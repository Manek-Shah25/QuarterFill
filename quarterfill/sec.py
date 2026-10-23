from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
import hashlib
import gzip
import json
import os
import re
import threading
import time
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings
from .models import Fact


class SECError(RuntimeError):
    pass


class SECClient:
    _lock = threading.Lock()
    _last = 0.0

    def __init__(self, user_agent=None, cache="data/cache", snapshot_url=None):
        self.user_agent = user_agent or os.getenv("SEC_USER_AGENT", "")
        self.cache = Path(cache)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.snapshot_url = snapshot_url or os.getenv("QUARTERFILL_SNAPSHOT_URL", "")
        self.events = []
        self.history_errors = []
        self.blocked_until = 0.0

    def get(self, url, ttl=86400):
        host = urlparse(url).hostname
        if host not in ("www.sec.gov", "data.sec.gov"):
            raise SECError("Only official SEC URLs are accepted by the SEC client.")
        key = hashlib.sha256(url.encode()).hexdigest()
        local = self.cache / (key + ".json")
        if local.exists():
            saved = json.loads(local.read_text(encoding="utf-8"))
            if saved["url"] == url and time.time() - saved["at"] < ttl:
                self.events.append({"url": url, "status": "cached", "retrieved": saved["at"]})
                return saved["body"]
        error = "A real operator name and email SEC_USER_AGENT must be configured."
        if (time.monotonic() >= self.blocked_until and
            re.search(r"[^\s@]+@[^\s@]+\.[^\s@]+", self.user_agent) and "example.com" not in self.user_agent):
            for attempt in range(3):
                response = None
                with self._lock:
                    time.sleep(max(0, 0.25 - (time.monotonic() - SECClient._last)))
                    SECClient._last = time.monotonic()
                try:
                    response = requests.get(url, headers={"User-Agent": self.user_agent,
                                            "Accept-Encoding": "gzip, deflate"}, timeout=30)
                    if response.status_code in (429, 503):
                        time.sleep(2 ** attempt)
                        continue
                    response.raise_for_status()
                    body = response.text
                    saved = {"url": url, "at": time.time(), "body": body,
                             "sha256": hashlib.sha256(body.encode()).hexdigest()}
                    local.write_text(json.dumps(saved), encoding="utf-8")
                    self.events.append({"url": url, "status": "live", "retrieved": saved["at"]})
                    return body
                except requests.RequestException as exc:
                    error = str(exc)
                    if response is not None and response.status_code == 403:
                        self.blocked_until = time.monotonic() + 60
                        break
        elif time.monotonic() < self.blocked_until:
            error = 'SEC access returned 403; using authentic cached evidence during a 60-second cooldown.'
        # Mirrors hold the exact cache envelopes generated from official SEC requests.
        if self.snapshot_url.startswith("https://raw.githubusercontent.com/"):
            try:
                mirror = requests.get(f"{self.snapshot_url.rstrip('/')}/{key}.json", timeout=20)
                mirror.raise_for_status()
                saved = mirror.json()
                if saved["url"] != url or hashlib.sha256(saved["body"].encode()).hexdigest() != saved["sha256"]:
                    raise SECError("Snapshot integrity check failed")
                self.events.append({"url": url, "status": "snapshot (not live)", "retrieved": saved["at"]})
                return saved["body"]
            except (requests.RequestException, ValueError, KeyError) as exc:
                error += f"; snapshot unavailable: {exc}"
        bundled = Path(__file__).resolve().parents[1] / 'data' / 'snapshots' / (key + '.json.gz')
        if bundled.exists():
            with gzip.open(bundled, 'rt', encoding='utf-8') as stream:
                saved = json.load(stream)
            if saved['url'] == url and hashlib.sha256(saved['body'].encode()).hexdigest() == saved['sha256']:
                self.events.append({'url': url, 'status': 'bundled SEC snapshot (not live)', 'retrieved': saved['at']})
                return saved['body']
        self.events.append({"url": url, "status": "unavailable", "error": error})
        raise SECError(error)

    def json(self, url):
        try:
            return json.loads(self.get(url))
        except ValueError as exc:
            raise SECError("SEC response was not valid JSON") from exc

    def companies(self):
        return list(self.json("https://www.sec.gov/files/company_tickers.json").values())

    def company(self, cik):
        cik = str(cik).zfill(10)
        return (self.json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"),
                self.json(f"https://data.sec.gov/submissions/CIK{cik}.json"))

    def concept(self, cik, namespace, tag):
        if not re.fullmatch(r'[A-Za-z0-9_-]+',namespace) or not re.fullmatch(r'[A-Za-z0-9_-]+',tag):
            raise SECError('Invalid XBRL concept name')
        return self.json(f'https://data.sec.gov/api/xbrl/companyconcept/CIK{str(cik).zfill(10)}/{namespace}/{tag}.json')

    def filings(self, submissions, include_history=False):
        recent = submissions["filings"]["recent"]
        records = [dict(zip(recent, values)) for values in zip(*recent.values())]
        if include_history:
            for item in submissions["filings"].get("files", []):
                try:
                    old = self.json(f"https://data.sec.gov/submissions/{item['name']}")
                    records.extend(dict(zip(old, values)) for values in zip(*old.values()))
                except SECError as exc:
                    self.history_errors.append({'status':'Filing verification unavailable',
                        'scope':'Historical submissions index', 'file':item['name'],'error':str(exc)})
        return records


def filing_url(cik, filing):
    accession = filing["accessionNumber"]
    document = filing["primaryDocument"]
    if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession) or not re.fullmatch(r"[\w.\-]+", document):
        raise SECError("Invalid filing metadata; refusing to invent a source URL")
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/{document}"


def company_facts(payload, filings):
    documents = {r["accessionNumber"]: r for r in filings}
    output = []
    for namespace, concepts in payload["facts"].items():
        for tag, info in concepts.items():
            for unit, observations in info["units"].items():
                for row in observations:
                    if row["form"] not in ("10-Q", "10-K", "10-Q/A", "10-K/A", "10-KT", "10-KT/A", "10-QT", "10-QT/A"):
                        continue
                    filing = documents.get(row["accn"])
                    output.append(Fact(str(payload["cik"]), f"{namespace}:{tag}", info["label"],
                        Decimal(str(row["val"])), unit, row.get("start"), row["end"],
                        row["accn"], row["form"], row["filed"],
                        filing_url(payload["cik"], filing) if filing else ""))
    return output


def parse_inline(html, cik, filing, url, timeout_seconds=30):
    if len(html)>40_000_000:
        raise SECError('Filing exceeds the 40 MB parsing limit; open the original report for review.')
    deadline=time.monotonic()+timeout_seconds
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', XMLParsedAsHTMLWarning)
        soup = BeautifulSoup(html, "lxml")
    contexts, units = {}, {}
    for tag in soup.find_all(lambda t: t.name.lower().split(":")[-1] == "context"):
        if time.monotonic()>deadline:
            raise SECError('Filing parsing time limit reached; no partial statement was accepted.')
        def content(name):
            found = tag.find(lambda t: t.name.lower().split(":")[-1] == name)
            return found.get_text(strip=True) if found else None
        dims = tuple(sorted(x.get('dimension','') + '=' + x.get_text(strip=True) for x in tag.find_all(
            lambda t: t.name.lower().split(":")[-1] in ("explicitmember", "typedmember"))))
        contexts[tag.get("id")] = (content("startdate"), content("enddate") or content("instant"), dims)
    for tag in soup.find_all(lambda t: t.name.lower().split(":")[-1] == "unit"):
        measures = [x.get_text(strip=True).split(":")[-1] for x in tag.find_all(
            lambda t: t.name.lower().split(":")[-1] == "measure")]
        units[tag.get("id")] = "/".join(measures)
    facts = []
    table_keys = {}
    for tag in soup.find_all(lambda t: t.name.lower().split(":")[-1] == "nonfraction"):
        if time.monotonic()>deadline:
            raise SECError('Filing parsing time limit reached; no partial statement was accepted.')
        context = contexts.get(tag.get("contextref"))
        if not context or not context[1] or tag.get("xsi:nil") == "true":
            continue
        text = tag.get_text("", strip=True).replace(",", "").replace("\u00a0", "")
        # Unsupported transformations are excluded, never guessed.
        fmt = tag.get("format", "").split(":")[-1].lower()
        if fmt and fmt not in ("num-dot-decimal", "numdotdecimal", "num-zero", "zerodash"):
            continue
        if fmt in ("num-zero", "zerodash"):
            text = "0"
        # Parentheses are an alternative negative representation. Do not negate
        # twice when an Inline XBRL sign attribute is also present.
        parenthesized = text.startswith('(') and text.endswith(')')
        if parenthesized:
            text = text[1:-1]
        try:
            value = Decimal(text) * (Decimal(10) ** int(tag.get("scale", "0")))
            if tag.get("sign") == "-" or parenthesized:
                value = -value
            if not value.is_finite():
                continue
        except (InvalidOperation, ValueError):
            continue
        table = tag.find_parent("table")
        table_key = ''
        if table is not None:
            identity = id(table)
            if identity not in table_keys:
                table_keys[identity] = hashlib.sha256((filing['accessionNumber'] + table.get_text(' ', strip=True)).encode()).hexdigest()
            table_key = table_keys[identity]
        row = tag.find_parent('tr')
        row_text = row.get_text(' ',strip=True) if row else tag.parent.get_text(' ',strip=True)
        section = ((table.get_text(' ',strip=True)[:450] + '\nMatched disclosure row: ') if table else '') + row_text[:1200]
        label_tag = row.find(['td','th']) if row else None
        original_label = label_tag.get_text(' ',strip=True) if label_tag else tag.get('name','')
        facts.append(Fact(str(cik), tag.get("name", ""), original_label, value,
            units.get(tag.get("unitref"), "unknown"), context[0], context[1],
            filing["accessionNumber"], filing["form"], filing["filingDate"], url,
            section, tag.get("contextref", ""), context[2], True, tag.get("decimals", "INF"), table_key,
            scale=int(tag.get('scale','0')), extraction_method='Inline XBRL'))
    return facts, soup.get_text(" ", strip=True)


def verify(fact, document_facts):
    matches = [f for f in document_facts if (f.concept, f.start, f.end, f.unit, f.value, f.dimensions) ==
               (fact.concept, fact.start, fact.end, fact.unit, fact.value, fact.dimensions)]
    return replace(fact, verified=True, section=matches[0].section, label=matches[0].label,
                   context=matches[0].context, decimals=matches[0].decimals, table=matches[0].table,
                   scale=matches[0].scale,extraction_method='Company Facts matched to Inline XBRL') if matches else fact
