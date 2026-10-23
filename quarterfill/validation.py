"""Accounting checks report discrepancies; they never change reported numbers."""
from dataclasses import dataclass, asdict
from decimal import Decimal
from .engine import tolerance


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    difference: Decimal | None
    tolerance: Decimal
    explanation: str

    def audit(self):
        return {k: str(v) if isinstance(v, Decimal) else v for k,v in asdict(self).items()}


IDENTITIES = (
    ('Assets equal liabilities plus equity', ('Total assets', 'Total liabilities', 'Equity including noncontrolling interests'), (1,-1,-1)),
    ('Revenue less costs equals gross profit', ('Revenue', 'Cost of revenue', 'Gross profit'), (1,-1,-1)),
    ('Current and noncurrent assets equal assets', ('Total assets', 'Current assets', 'Noncurrent assets'), (1,-1,-1)),
    ('Current and noncurrent liabilities equal liabilities', ('Total liabilities', 'Current liabilities', 'Noncurrent liabilities'), (1,-1,-1)),
    ('Cash movements include exchange rates', ('Change in cash including restricted cash', 'Cash from operations', 'Cash from investing', 'Cash from financing', 'Exchange-rate effect on cash'), (1,-1,-1,-1,-1)),
)


def validate(cells, absolute_tolerance=Decimal('1'), relative_tolerance=Decimal('0')):
    by_name = {c.metric:c for c in cells}
    checks=[]
    for label,names,signs in IDENTITIES:
        if names[0]=='Total assets' and 'Total liabilities' in names:
            # Mezzanine equity sits outside both liabilities and permanent equity.
            for extra in ('Temporary equity','Redeemable noncontrolling interests'):
                if extra in by_name and by_name[extra].value is not None:
                    names=(*names,extra); signs=(*signs,-1)
                    label='Assets equal liabilities, equity, and separately reported redeemable interests'
                    break  # Never count an aggregate and its component twice.
        parts=[by_name.get(n) for n in names]
        if any(c is None or c.value is None for c in parts):
            checks.append(Check(label,'Not checked',None,absolute_tolerance,'A required amount is missing; we do not assume it is zero.'))
            continue
        if len({(c.start if not all(f.start is None for f in c.inputs) else None,c.end,c.unit) for c in parts}) != 1:
            checks.append(Check(label,'Review',None,absolute_tolerance,'The amounts have different dates, periods, or units.'))
            continue
        # Worst-case accumulated rounding error, including each unique source once.
        sources={f.id:f for c in parts for f in c.inputs}
        allowed=max(absolute_tolerance,sum((tolerance(f) for f in sources.values()),Decimal(0)),
                    max(abs(c.value) for c in parts)*relative_tolerance)
        difference=sum((c.value*s for c,s in zip(parts,signs)),Decimal(0))
        calculated=any(c.accounting_status=='Derived' for c in parts)
        checks.append(Check(label,'Passed' if abs(difference)<=allowed else 'Review',difference,allowed,
                            ('The amounts agree within rounding.' + (' Some amounts were calculated, so this is not an independent check.' if calculated else '')) if abs(difference)<=allowed else
                            'The amounts do not add up. Reported values have been kept; check scope, signs, and other disclosed adjustments.'))
    return checks
