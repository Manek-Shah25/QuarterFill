"""Small, non-validating extension reader. Never resolves XML external entities.

Only same-filing schema/linkbase documents are fetched, with a bounded budget.
This reads relationships for evidence; it does not claim full XBRL validation.
"""
from collections import defaultdict
from urllib.parse import urljoin, urlparse
import re
from dataclasses import replace
from lxml import etree
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings

XLINK='{http://www.w3.org/1999/xlink}'
XBRLI='{http://www.xbrl.org/2003/instance}'


def xml(text):
    return etree.fromstring(text.encode(),etree.XMLParser(resolve_entities=False,no_network=True,huge_tree=False))


class Taxonomy:
    def __init__(self):
        self.concepts={}
        self.labels=defaultdict(dict)
        self.roles=defaultdict(set)
        self.calculations=[]
        self.presentations=[]
        self.documents=[]
        self.errors=[]

    def read(self,text,url):
        root=xml(text)
        self.documents.append(url)
        target=root.get('targetNamespace','')
        prefix=next((p for p,v in root.nsmap.items() if p and v==target),'')
        for e in root.xpath('//*[local-name()="element"]'):
            if not e.get('name'):
                continue
            name=(prefix+':' if prefix else '')+e.get('name')
            self.concepts[name]={'period':e.get(XBRLI+'periodType'),'balance':e.get(XBRLI+'balance'),
                                 'type':e.get('type',''),'id':e.get('id',''),
                                 'definition':' '.join(e.xpath('.//*[local-name()="documentation"]/text()'))}
        for link in root.xpath('//*[local-name()="labelLink" or local-name()="presentationLink" or local-name()="calculationLink"]'):
            loc={e.get(XLINK+'label'):self.qname(e.get(XLINK+'href','').split('#')[-1])
                 for e in link if etree.QName(e).localname=='loc'}
            labels={e.get(XLINK+'label'):(e.get(XLINK+'role','').split('/')[-1],''.join(e.itertext()).strip())
                    for e in link if etree.QName(e).localname=='label'}
            role=link.get(XLINK+'role','')
            for arc in link:
                kind=etree.QName(arc).localname
                source=loc.get(arc.get(XLINK+'from'))
                dest=loc.get(arc.get(XLINK+'to'))
                if kind=='labelArc' and source and arc.get(XLINK+'to') in labels:
                    label_kind,label=labels[arc.get(XLINK+'to')]
                    self.labels[source][label_kind]=label
                elif kind in ('presentationArc','calculationArc') and source and dest:
                    self.roles[source].add(role); self.roles[dest].add(role)
                    relation=(source,dest,arc.get('weight','1'),role)
                    (self.calculations if kind=='calculationArc' else self.presentations).append(relation)

    def qname(self,identifier):
        for name,info in self.concepts.items():
            if info['id']==identifier:
                return name
        return identifier.replace('_',':',1)


def load_taxonomy(client,html,filing_url,budget=6):
    result=Taxonomy()
    with warnings.catch_warnings():
        warnings.simplefilter('ignore',XMLParsedAsHTMLWarning)
        soup=BeautifulSoup(html,'lxml')
    refs=[t.get('xlink:href') or t.get('href') for t in soup.find_all(
        lambda t:t.name.lower().split(':')[-1]=='schemaref')]
    base=filing_url.rsplit('/',1)[0]+'/'
    queue=[urljoin(filing_url,r) for r in refs if r]
    seen=set()
    while queue and len(seen)<budget:
        url=queue.pop(0)
        if url in seen or not url.startswith(base) or urlparse(url).fragment:
            continue
        seen.add(url)
        try:
            text=client.get(url,ttl=30*86400)
            root=xml(text)
            result.read(text,url)
            for e in root.xpath('//*[local-name()="linkbaseRef"]'):
                ref=e.get(XLINK+'href')
                if ref:
                    queue.append(urljoin(url,ref))
        except Exception as exc:
            # A taxonomy failure must not discard already parsed financial facts.
            result.errors.append({'url':url,'error':str(exc)})
    return result


def normalized(text):
    return re.sub(r'[^a-z0-9]','',text.lower())


def definition_supports(metric,text):
    """Narrow natural-language definitions, in addition to explicit standard references."""
    compact=normalized(text)
    if any(normalized(t) in compact for t in metric.exclusions):
        return False
    if any(normalized(t) in compact for t in metric.tags):
        return True
    lower=text.lower()
    if metric.name=='Inventory':
        return ('inventor' in lower and 'net of' in lower and
                any(t in lower for t in ('valuation reserves','valuation allowances','inventory reserves')) and
                any(t in lower for t in ('carrying amount','current asset')) and
                not any(t in lower for t in ('finished goods only','gross inventory','gross inventories')))
    if metric.name=='Receivables':
        return ('trade' in lower and 'receivable' in lower and 'net of' in lower and
                'allowance' in lower and 'current' in lower and not any(t in lower for t in ('notes receivable','other receivables','noncurrent')))
    if metric.name in ('Deferred revenue (current)','Current contract liabilities'):
        return ('current' in lower and 'noncurrent' not in lower and 'non-current' not in lower and
                any(t in lower for t in ('contract liability','contract liabilities','unearned revenue','deferred revenue')) and
                'customer' in lower and any(t in lower for t in ('performance obligation','goods or services','goods and services')))
    return False


def custom_candidates(metric,taxonomy,facts):
    """Require exact terminology PLUS schema period/unit AND statement relationship.

    Documentation must support the definition or a standard calculation relationship
    must anchor the custom concept to a known standard total. A keyword is not proof.
    """
    names={normalized(x) for x in (metric.name,*metric.aliases,*metric.tags)}
    statement_tokens={'Income':('income','operations','earnings'),
                      'Balance sheet':('balance','financialposition'), 'Cash flow':('cashflow',)}
    found=[]
    for concept in {f.concept for f in facts if not f.concept.startswith('us-gaap:')}:
        schema=taxonomy.concepts.get(concept,{})
        labels=taxonomy.labels.get(concept,{})
        label=labels.get('label','')
        if normalized(label) not in names or schema.get('period')!=metric.period_type:
            continue
        roles=' '.join(taxonomy.roles.get(concept,())).lower().replace('_','')
        if not any(t in roles for t in statement_tokens.get(metric.statement,())):
            continue
        documentation=labels.get('documentation','')+' '+schema.get('definition','')
        definition_match=definition_supports(metric,documentation)
        # A calculation child is not equivalent to its parent. Relationships supply
        # statement context, while documentation must establish accounting meaning.
        if not definition_match:
            continue
        found.extend(replace(f,definition=documentation,presentation_roles=tuple(sorted(taxonomy.roles[concept])),
                             calculation_relationships=tuple(r for r in taxonomy.calculations if concept in r[:2]),
                             extraction_method='Inline XBRL with extension definition and statement relationships')
                     for f in facts if f.concept==concept and f.unit==metric.unit and not f.dimensions)
    return found
