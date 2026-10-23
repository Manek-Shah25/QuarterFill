"""Conservative fallback for untagged monetary rows with explicit dates and scale.

Complex merged/multilevel period headers are left unresolved rather than guessed.
Inline-tagged cells are handled by the structured parser first.
"""
from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import re
import time
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings
from .models import Fact
from .taxonomy import normalized


def number(text):
    text=text.strip().replace('\u2212','-').replace('\u00a0','').replace(',','').replace('$','').strip()
    if text in ('—','–','-',''):
        return None  # Typography is not explicit evidence of zero.
    if text.startswith('(') and text.endswith(')') and re.fullmatch(r'[\d.]+',text[1:-1].strip()):
        text='-'+text[1:-1].strip()
    if not re.fullmatch(r'-?\d+(?:\.\d+)?',text):
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def exact_date(text):
    text=re.sub(r'\s+',' ',text).strip()
    for fmt in ('%Y-%m-%d','%B %d, %Y','%b %d, %Y'):
        try:
            return datetime.strptime(text,fmt).date().isoformat()
        except ValueError:
            pass
    return None


def parse_tables(html,cik,filing,url,metrics,structured,timeout_seconds=10):
    deadline=time.monotonic()+timeout_seconds
    with warnings.catch_warnings():
        warnings.simplefilter('ignore',XMLParsedAsHTMLWarning)
        soup=BeautifulSoup(html,'lxml')
    output=[]
    for table in soup.find_all('table'):
        if time.monotonic()>deadline:
            from .sec import SECError
            raise SECError('Untagged table parsing time limit reached; structured filing facts are retained.')
        text=table.get_text(' ',strip=True)
        prefix=text[:500].lower()
        if 'in millions' in prefix or 'millions of dollars' in prefix:
            scale=6
        elif 'in thousands' in prefix or 'thousands of dollars' in prefix:
            scale=3
        elif 'in dollars' in prefix:
            scale=0
        else:
            continue  # Never infer monetary scale from magnitude.
        rows=table.find_all('tr',recursive=False) or table.find_all('tr')
        header=None
        for row in rows[:8]:
            cols=row.find_all(['td','th'],recursive=False)
            dates=[exact_date(c.get_text(' ',strip=True)) for c in cols]
            if sum(d is not None for d in dates)>=1 and all(c.get('colspan','1')=='1' for c in cols):
                header=dates
                break
        if not header:
            continue
        for row in rows:
            cols=row.find_all(['td','th'],recursive=False)
            if len(cols)!=len(header) or not cols or any(c.get('colspan','1')!='1' or c.get('rowspan','1')!='1' for c in cols):
                continue
            label=cols[0].get_text(' ',strip=True)
            candidates=[m for m in metrics if normalized(label) in {normalized(m.name),*(normalized(a) for a in m.aliases)} and m.unit=='USD']
            for m in candidates:
                category={'Balance sheet':('balance sheet','financial position'), 'Income':('statements of income','statements of operations'),
                          'Cash flow':('cash flows',)}.get(m.statement,())
                if not any(t in prefix for t in category):
                    continue
                for i,end in enumerate(header):
                    if not end or cols[i].find(lambda t:t.name.lower().split(':')[-1]=='nonfraction'):
                        continue
                    value=number(cols[i].get_text(' ',strip=True))
                    if value is None:
                        continue
                    if m.kind=='instant':
                        start=None
                    else:
                        # Duration headers must explicitly establish the start as well.
                        match=re.search(r'from (\d{4}-\d{2}-\d{2}) (?:through|to) '+re.escape(end),prefix)
                        if not match:
                            continue
                        start=match.group(1)
                    if any(f.start==start and f.end==end and f.concept in {'us-gaap:'+t for t in m.tags} for f in structured):
                        continue
                    output.append(Fact(str(cik),'html:'+normalized(m.name),label,value*(Decimal(10)**scale),'USD',start,end,
                        filing['accessionNumber'],filing['form'],filing['filingDate'],url,text[:1600],
                        'Explicit table date and scale',(),True,str(-scale),hashlib.sha256((filing['accessionNumber']+text).encode()).hexdigest(),
                        scale=scale,extraction_method='Original HTML table'))
    return output
