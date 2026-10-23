"""Conservative, centralized accounting identities with explicit scope guards."""
from .engine import derive

# No equation guesses missing components or mixes stockholder and total equity.
FORMULAS = {
    'Cost of revenue': [(('Revenue','Gross profit'), ('-',), 'industrial')],
    'Gross profit': [(('Revenue','Cost of revenue'), ('-',), 'industrial')],
    'Noncurrent assets': [(('Total assets','Current assets'), ('-',), 'all')],
    'Noncurrent liabilities': [(('Total liabilities','Current liabilities'), ('-',), 'all')],
    'Total liabilities': [(('Total assets','Equity including noncontrolling interests'), ('-',), 'all')],
    'Total assets': [(('Total liabilities','Equity including noncontrolling interests'), ('+',), 'all')],
    'Equity including noncontrolling interests': [(('Total assets','Total liabilities'), ('-',), 'all')],
    'Intangible assets': [(('Finite-lived intangible assets','Indefinite-lived intangible assets'), ('+',), 'all')],
    'Pretax income': [(('Income from continuing operations','Income taxes'), ('+',), 'presentation')],
    'Operating income': [(('Gross profit','Operating expenses'), ('-',), 'presentation')],
    'Change in cash including restricted cash': [(('Cash from operations','Cash from investing','Cash from financing','Exchange-rate effect on cash'), ('+','+','+'), 'presentation')],
    'Property and equipment, net': [(('Property and equipment, gross','Accumulated depreciation'), ('-',), 'all')],
}


def financial_industry(submissions):
    try:
        sic=int(submissions.get('sic',0))
    except (TypeError,ValueError):
        return False
    return 6000 <= sic <= 6499


def recover(research, name, year, q, seen):
    for names,ops,industry in FORMULAS.get(name, ()):
        if industry in ('industrial','presentation') and financial_industry(research.submissions):
            continue
        if any(n in seen for n in names):
            continue
        parts=[research.cell(n,year,q,_seen=seen) for n in names]
        # Arithmetic from unverified API facts is not a verified accounting identity.
        if not all(c.verified for c in parts):
            continue
        if name in ('Total assets','Total liabilities','Equity including noncontrolling interests'):
            # A - L also includes redeemable interests when they sit in mezzanine.
            target=parts[0].end
            mezz=[f for f in research.selected_facts() if f.end==target and f.start is None and not f.dimensions
                  and ('TemporaryEquity' in f.concept or 'RedeemableNoncontrollingInterestEquityCarryingAmount' in f.concept)]
            if any(f.value!=0 for f in mezz):
                extra=None
                for label in ('Temporary equity','Redeemable noncontrolling interests'):
                    candidate=research.cell(label,year,q,_seen=seen)
                    if candidate.verified:
                        extra=candidate; break
                if extra is None:
                    continue
                parts.append(extra)
                ops=(*ops,'+' if name=='Total assets' else '-')
        # PP&E gross and depreciation must be in the same reported table and filing.
        if name=='Property and equipment, net':
            groups=[{(f.accession,f.table) for f in c.inputs if f.table} for c in parts]
            if not set.intersection(*groups):
                continue
        if industry in ('industrial','presentation'):
            # Same filing and statement table establishes matching revenue/gross scope.
            groups=[{(f.accession,f.table) for f in c.inputs if f.table} for c in parts]
            if not set.intersection(*groups):
                continue
            if industry=='presentation':
                # Filed calculation arcs must prove this is the complete equation.
                if any(c.components or c.operation for c in parts):
                    continue  # Relationship proof is for the exact reported concepts.
                expected={(parts[0].inputs[0].concept,1),*((c.inputs[0].concept,1 if op=='+' else -1) for c,op in zip(parts[1:],ops))}
                valid=False
                from .concepts import BY_NAME
                for taxonomy in research.taxonomies.values():
                    for tag in BY_NAME[name].tags:
                        parent='us-gaap:'+tag
                        roles={r for a,b,w,r in taxonomy.calculations if a==parent}
                        for role in roles:
                            relationships=[(b,w) for a,b,w,r in taxonomy.calculations if a==parent and r==role]
                            if any(w not in ('1','-1') for b,w in relationships):
                                continue
                            arcs={(b,int(w)) for b,w in relationships}
                            if arcs==expected:
                                valid=True
                if not valid:
                    continue
        result=derive(research.company['entityName'],research.submissions.get('tickers',[''])[0],name,parts,list(ops))
        if result.value is not None:
            result.reasoning.insert(0,'Calculated using matching reported accounting components.')
            return result
    return None
