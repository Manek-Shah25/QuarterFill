"""Deliberately narrow equivalence groups; different definitions remain choices."""
from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass(frozen=True)
class Metric:
    name: str
    statement: str
    kind: str
    tags: tuple[str, ...]
    aliases: tuple[str, ...] = ()
    unit: str = "USD"
    definition: str = ""
    industries: tuple[str, ...] = ("all",)
    exclusions: tuple[str, ...] = ()

    @property
    def period_type(self):
        return 'instant' if self.kind == 'instant' else 'duration'

    @property
    def derivations(self):
        from .formulas import FORMULAS
        return FORMULAS.get(self.name, ())


METRICS = [
    Metric("Revenue", "Income", "flow", ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"), ("sales",)),
    Metric("Cost of revenue", "Income", "flow", ("CostOfRevenue", "CostOfGoodsAndServicesSold"), ("COGS",)),
    Metric("Gross profit", "Income", "flow", ("GrossProfit",)),
    Metric("SG&A", "Income", "flow", ("SellingGeneralAndAdministrativeExpense",)),
    Metric("R&D", "Income", "flow", ("ResearchAndDevelopmentExpense",)),
    Metric("Operating income", "Income", "flow", ("OperatingIncomeLoss",)),
    Metric("Interest expense", "Income", "flow", ("InterestExpense",)),
    Metric("Income taxes", "Income", "flow", ("IncomeTaxExpenseBenefit",)),
    Metric("Net income", "Income", "flow", ("NetIncomeLoss",)),
    Metric("Depreciation and amortization", "Cash flow", "flow", ("DepreciationDepletionAndAmortization",)),
    Metric("Diluted EPS", "Income", "nonadditive", ("EarningsPerShareDiluted",), ("EPS",), "USD/shares"),
    Metric("Basic EPS", "Income", "nonadditive", ("EarningsPerShareBasic",), (), "USD/shares"),
    Metric("Diluted weighted-average shares", "Income", "nonadditive", ("WeightedAverageNumberOfDilutedSharesOutstanding",), (), "shares"),
    Metric("Cash", "Balance sheet", "instant", ("CashAndCashEquivalentsAtCarryingValue",)),
    Metric("Receivables", "Balance sheet", "instant", ("AccountsReceivableNetCurrent",)),
    Metric("Inventory", "Balance sheet", "instant", ("InventoryNet",), ('inventories','merchandise inventories','inventory, net')),
    Metric("Deferred revenue (current)", "Balance sheet", "instant", ("ContractWithCustomerLiabilityCurrent", "DeferredRevenueCurrent"), ("deferred revenue",)),
    Metric("Debt (current)", "Balance sheet", "instant", ("LongTermDebtCurrent",)),
    Metric("Debt (noncurrent)", "Balance sheet", "instant", ("LongTermDebtNoncurrent",)),
    Metric("Goodwill", "Balance sheet", "instant", ("Goodwill",)),
    Metric("Intangible assets", "Balance sheet", "instant", ("IntangibleAssetsNetExcludingGoodwill",)),
    Metric("Total assets", "Balance sheet", "instant", ("Assets",)),
    Metric("Total liabilities", "Balance sheet", "instant", ("Liabilities",)),
    Metric("Equity", "Balance sheet", "instant", ("StockholdersEquity",)),
    Metric("Cash from operations", "Cash flow", "flow", ("NetCashProvidedByUsedInOperatingActivities",), ("CFO", "operating cash flow")),
    Metric("Capital expenditures", "Cash flow", "flow", ("PaymentsToAcquirePropertyPlantAndEquipment",), ("CapEx", "capital spending")),
    Metric("Stock-based compensation", "Cash flow", "flow", ("ShareBasedCompensation",), ("stock compensation", "SBC")),
    Metric("Acquisitions", "Cash flow", "flow", ("PaymentsToAcquireBusinessesNetOfCashAcquired",)),
    Metric("Debt issuance", "Cash flow", "flow", ("ProceedsFromIssuanceOfLongTermDebt",)),
    Metric("Debt repayment", "Cash flow", "flow", ("RepaymentsOfLongTermDebt",)),
    Metric("Dividends", "Cash flow", "flow", ("PaymentsOfDividends",)),
    Metric("Share repurchases", "Cash flow", "flow", ("PaymentsForRepurchaseOfCommonStock",)),
]
# Separate scopes stay separate, even when the filing uses similar labels.
# Registry entries are intentionally data, so adding coverage does not change the resolver.
_ADDITIONAL = {
    'Income': [
        ('Product revenue', 'SalesRevenueGoodsNet'), ('Service revenue', 'SalesRevenueServicesNet'),
        ('Revenue net of interest expense', 'RevenuesNetOfInterestExpense'),
        ('Income from continuing operations', 'IncomeLossFromContinuingOperations'),
        ('Cost of goods sold', 'CostOfGoodsSold'), ('Sales and marketing', 'SellingAndMarketingExpense'),
        ('General and administrative', 'GeneralAndAdministrativeExpense'),
        ('Operating depreciation and amortization', 'DepreciationAndAmortization'),
        ('Operating expenses', 'OperatingExpenses'), ('Interest income', 'InvestmentIncomeInterest'),
        ('Other income and expense', 'OtherNonoperatingIncomeExpense'),
        ('Pretax income', 'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest'),
        ('Net income to common shareholders', 'NetIncomeLossAvailableToCommonStockholdersBasic'),
        ('Basic weighted-average shares', 'WeightedAverageNumberOfSharesOutstandingBasic'),
    ],
    'Balance sheet': [
        ('Restricted cash', 'RestrictedCashAndCashEquivalents'), ('Short-term investments', 'ShortTermInvestments'),
        ('Restricted cash excluding equivalents', 'RestrictedCash'),
        ('Restricted cash, noncurrent', 'RestrictedCashNoncurrent'),
        ('Notes receivable', 'NotesReceivableNetCurrent'), ('Other receivables', 'OtherReceivablesNetCurrent'),
        ('Combined receivables', 'AccountsNotesAndOtherReceivablesNetCurrent|ReceivablesNetCurrent'),
        ('Gross inventory', 'InventoryGross'), ('Finished goods inventory', 'InventoryFinishedGoods'),
        ('Finite-lived intangible assets', 'FiniteLivedIntangibleAssetsNet'),
        ('Indefinite-lived intangible assets', 'IndefiniteLivedIntangibleAssetsExcludingGoodwill'),
        ('Prepaid expenses', 'PrepaidExpenseCurrent'), ('Other current assets', 'OtherAssetsCurrent'),
        ('Current assets', 'AssetsCurrent'), ('Noncurrent assets', 'AssetsNoncurrent'),
        ('Property and equipment, net', 'PropertyPlantAndEquipmentNet'),
        ('Property and equipment, gross', 'PropertyPlantAndEquipmentGross'),
        ('Accumulated depreciation', 'AccumulatedDepreciationDepletionAndAmortizationPropertyPlantAndEquipment'),
        ('Deferred tax assets', 'DeferredIncomeTaxAssetsNet'), ('Other noncurrent assets', 'OtherAssetsNoncurrent'),
        ('Accounts payable', 'AccountsPayableCurrent'), ('Accrued expenses', 'AccruedLiabilitiesCurrent'),
        ('Current contract liabilities', 'ContractWithCustomerLiabilityCurrent'),
        ('Short-term borrowings', 'ShortTermBorrowings'), ('Current operating lease liabilities', 'OperatingLeaseLiabilityCurrent'),
        ('Other current liabilities', 'OtherLiabilitiesCurrent'), ('Current liabilities', 'LiabilitiesCurrent'),
        ('Noncurrent liabilities', 'LiabilitiesNoncurrent'),
        ('Noncurrent operating lease liabilities', 'OperatingLeaseLiabilityNoncurrent'),
        ('Deferred tax liabilities', 'DeferredIncomeTaxLiabilitiesNet'),
        ('Deferred revenue (noncurrent)', 'ContractWithCustomerLiabilityNoncurrent|DeferredRevenueNoncurrent'),
        ('Other noncurrent liabilities', 'OtherLiabilitiesNoncurrent'), ('Common stock', 'CommonStockValue'),
        ('Additional paid-in capital', 'AdditionalPaidInCapital'), ('Retained earnings', 'RetainedEarningsAccumulatedDeficit'),
        ('Treasury stock', 'TreasuryStockValue'), ('Other comprehensive income', 'AccumulatedOtherComprehensiveIncomeLossNetOfTax'),
        ('Noncontrolling interests', 'MinorityInterest'), ('Equity including noncontrolling interests', 'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'),
        ('Redeemable noncontrolling interests', 'RedeemableNoncontrollingInterestEquityCarryingAmount'),
        ('Temporary equity', 'TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests'),
    ],
    'Cash flow': [
        ('Cash flow net income', 'NetIncomeLoss'), ('Deferred taxes', 'DeferredIncomeTaxExpenseBenefit'),
        ('Property depreciation and amortization', 'DepreciationDepletionAndAmortizationPropertyPlantAndEquipment'),
        ('Common stock dividends', 'PaymentsOfDividendsCommonStock'),
        ('Change in receivables', 'IncreaseDecreaseInAccountsReceivable'), ('Change in inventory', 'IncreaseDecreaseInInventories'),
        ('Change in accounts payable', 'IncreaseDecreaseInAccountsPayable'), ('Change in accrued liabilities', 'IncreaseDecreaseInAccruedLiabilities'),
        ('Change in deferred revenue', 'IncreaseDecreaseInContractWithCustomerLiability'),
        ('Change in operating assets and liabilities', 'IncreaseDecreaseInOperatingCapital'),
        ('Investment purchases', 'PaymentsToAcquireInvestments'),
        ('Investment sales and maturities', 'ProceedsFromSaleMaturityAndCollectionsOfInvestments'),
        ('Cash from investing', 'NetCashProvidedByUsedInInvestingActivities'),
        ('Equity issuance', 'ProceedsFromStockIssuance'),
        ('Cash from financing', 'NetCashProvidedByUsedInFinancingActivities'),
        ('Exchange-rate effect on cash', 'EffectOfExchangeRateOnCashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents'),
        ('Change in cash including restricted cash', 'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecreaseIncludingExchangeRateEffect'),
        ('Ending cash including restricted cash', 'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents'),
        ('Beginning cash including restricted cash', 'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents'),
        ('Free cash flow', ''),
    ],
}
for _statement, _entries in _ADDITIONAL.items():
    for _name, _tags in _entries:
        _kind = 'instant' if _statement == 'Balance sheet' or _name.startswith('Ending cash') else 'flow'
        _unit = 'USD'
        if _name == 'Basic weighted-average shares':
            _kind, _unit = 'nonadditive', 'shares'
        METRICS.append(Metric(_name, _statement, _kind, tuple(_tags.split('|')), unit=_unit,
                              definition=_name + '; exact consolidated accounting scope only.'))
from dataclasses import replace
_EXCLUSIONS = {
    'Inventory': ('InventoryGross', 'InventoryFinishedGoods'),
    'Receivables': ('AccountsNotesAndOtherReceivablesNetCurrent', 'ReceivablesNetCurrent'),
    'Capital expenditures': ('PaymentsToAcquireProductiveAssets',),
    'Intangible assets': ('Goodwill', 'GoodwillAndIntangibleAssetsNet'),
}
_DEFINITIONS = {
    'Inventory':'Net carrying amount of consolidated inventory after applicable allowances; not gross inventory or finished goods alone.',
    'Receivables':'Current trade accounts receivable after allowances; excludes notes and other receivables unless separately identified.',
    'Combined receivables':'Current accounts, notes, and other receivables net of allowances; broader than trade accounts alone.',
    'Cash':'Cash and cash equivalents available to the company; excludes restricted cash unless explicitly described as cash only.',
    'Capital expenditures':'Cash paid to acquire property, plant and equipment; positive outflow, excluding acquisitions and broader productive assets.',
    'Intangible assets':'Net identifiable finite- and indefinite-lived intangible assets, excluding goodwill.',
    'Finite-lived intangible assets':'Net identifiable intangible assets with finite useful lives; kept separate from indefinite-lived assets.',
    'Equity':'Equity attributable to parent stockholders; excludes noncontrolling and redeemable interests.',
    'Equity including noncontrolling interests':'Permanent consolidated equity, including noncontrolling interests; excludes mezzanine interests.',
    'Change in receivables':'Reported cash flow working-capital movement in accounts receivable; not a balance sheet receivable balance.',
    'Free cash flow':'Operating cash flow minus positive cash outflows to acquire property, plant and equipment.',
}
METRICS = [replace(m, definition=_DEFINITIONS.get(m.name,m.definition or m.name + '; exact consolidated accounting scope only.'),
                   industries=('nonfinancial',) if m.name in ('Gross profit','Cost of revenue','Cost of goods sold') else ('all',),
                   exclusions=_EXCLUSIONS.get(m.name, ())) for m in METRICS]
BY_NAME = {m.name: m for m in METRICS}
DERIVED = {
    "Free cash flow": ("Cash from operations", "Capital expenditures", "-"),
    "Net debt (long-term debt only)": ("Debt (current)", "Debt (noncurrent)", "+", "Cash", "-"),
    "EBITDA (operating income + D&A)": ("Operating income", "Depreciation and amortization", "+"),
}


def search(query):
    query = query.lower().strip()
    return sorted(METRICS, key=lambda m: max(
        1.0 if query in label.lower() else SequenceMatcher(None, query, label.lower()).ratio()
        for label in (m.name, *m.aliases, *m.tags)), reverse=True)
