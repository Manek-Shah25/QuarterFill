"""Resolve exact-date cash balances without merging different definitions."""
from .concepts import Metric
from .engine import reconstruct, derive

CASH_TAGS = ('CashAndCashEquivalentsAtCarryingValue','Cash','CashEquivalentsAtCarryingValue',
             'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents','RestrictedCashAndCashEquivalents')


def cash_balance(company, ticker, facts, year, q, periods):
    def reported(tag, label):
        return reconstruct(company,ticker,Metric(label,'Balance sheet','instant',(),(),'USD'),
                           facts,year,q,periods,'us-gaap:'+tag)

    total = reported('CashAndCashEquivalentsAtCarryingValue','Cash')
    if total.value is not None or total.status == 'Ambiguous or conflicting':
        return total
    cash = reported('Cash','Cash')
    equivalents = reported('CashEquivalentsAtCarryingValue','Cash equivalents')
    if cash.value is not None and equivalents.value is not None:
        return derive(company,ticker,'Cash',[cash,equivalents],['+'])
    if cash.value is not None or cash.status == 'Ambiguous or conflicting':
        cash.warnings.append('Cash-only balance: the company reports this line as cash, rather than a combined cash-and-cash-equivalents total.')
        return cash
    combined = reported('CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents',
                        'Cash, cash equivalents and restricted cash')
    # Broad restricted-cash totals are alternatives, not additive components.
    for tag in ('RestrictedCashAndCashEquivalents',):
        restricted = reported(tag,'Restricted cash')
        if combined.value is not None and restricted.value is not None:
            return derive(company,ticker,'Cash',[combined,restricted],['-'])
    return total
