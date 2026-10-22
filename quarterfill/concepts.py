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
    Metric("Depreciation and amortization", "Cash flow", "flow", ("DepreciationDepletionAndAmortization", "DepreciationDepletionAndAmortizationPropertyPlantAndEquipment")),
    Metric("Diluted EPS", "Income", "nonadditive", ("EarningsPerShareDiluted",), ("EPS",), "USD/shares"),
    Metric("Basic EPS", "Income", "nonadditive", ("EarningsPerShareBasic",), (), "USD/shares"),
    Metric("Diluted weighted-average shares", "Income", "nonadditive", ("WeightedAverageNumberOfDilutedSharesOutstanding",), (), "shares"),
    Metric("Cash", "Balance sheet", "instant", ("CashAndCashEquivalentsAtCarryingValue",)),
    Metric("Receivables", "Balance sheet", "instant", ("AccountsReceivableNetCurrent",)),
    Metric("Inventory", "Balance sheet", "instant", ("InventoryNet",)),
    Metric("Deferred revenue (current)", "Balance sheet", "instant", ("ContractWithCustomerLiabilityCurrent", "DeferredRevenueCurrent"), ("deferred revenue",)),
    Metric("Debt (current)", "Balance sheet", "instant", ("LongTermDebtCurrent",)),
    Metric("Debt (noncurrent)", "Balance sheet", "instant", ("LongTermDebtNoncurrent",)),
    Metric("Goodwill", "Balance sheet", "instant", ("Goodwill",)),
    Metric("Intangible assets", "Balance sheet", "instant", ("FiniteLivedIntangibleAssetsNet",)),
    Metric("Total assets", "Balance sheet", "instant", ("Assets",)),
    Metric("Total liabilities", "Balance sheet", "instant", ("Liabilities",)),
    Metric("Equity", "Balance sheet", "instant", ("StockholdersEquity",)),
    Metric("Cash from operations", "Cash flow", "flow", ("NetCashProvidedByUsedInOperatingActivities",), ("CFO", "operating cash flow")),
    Metric("Capital expenditures", "Cash flow", "flow", ("PaymentsToAcquirePropertyPlantAndEquipment",), ("CapEx", "capital spending")),
    Metric("Stock-based compensation", "Cash flow", "flow", ("ShareBasedCompensation",), ("stock compensation", "SBC")),
    Metric("Acquisitions", "Cash flow", "flow", ("PaymentsToAcquireBusinessesNetOfCashAcquired",)),
    Metric("Debt issuance", "Cash flow", "flow", ("ProceedsFromIssuanceOfLongTermDebt",)),
    Metric("Debt repayment", "Cash flow", "flow", ("RepaymentsOfLongTermDebt",)),
    Metric("Dividends", "Cash flow", "flow", ("PaymentsOfDividends", "PaymentsOfDividendsCommonStock")),
    Metric("Share repurchases", "Cash flow", "flow", ("PaymentsForRepurchaseOfCommonStock",)),
]
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
