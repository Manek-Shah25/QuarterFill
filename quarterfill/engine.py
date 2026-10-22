"""Deterministic period selection. No calendar-quarter assumptions or EPS differencing."""
from datetime import date, timedelta
from decimal import Decimal
from .models import Cell, Fact
from .concepts import Metric


def days(start, end):
    return (date.fromisoformat(end) - date.fromisoformat(start)).days + 1


def tolerance(fact):
    try:
        return Decimal(10) ** (-int(fact.decimals)) / 2
    except (ValueError, TypeError):
        return Decimal(0)


def choose(facts):
    """Do not silently pick latest when a disclosure has changed."""
    if not facts:
        return None, None
    if any(abs(a.value - b.value) > max(tolerance(a), tolerance(b))
           for a in facts for b in facts):
        return None, "Conflicting filing versions or accounting concepts; analyst review required."
    return sorted(facts, key=lambda f: (f.verified, f.filed), reverse=True)[0], None


def fiscal_periods(facts, year):
    # fy on CompanyFacts is the filing's fiscal year, NOT the observation year.
    annual = [f for f in facts if f.start and 350 <= days(f.start, f.end) <= 380
              and f.form in ("10-K", "10-K/A") and int(f.end[:4]) == year]
    anchors = {(f.start, f.end) for f in annual}
    if len(anchors) != 1:
        return None
    start, end = next(iter(anchors))
    boundaries = {}
    for q, low, high in ((1, 70, 110), (2, 160, 205), (3, 245, 300)):
        ends = {f.end for f in facts if f.start == start and low <= days(start, f.end) <= high}
        if len(ends) == 1:
            boundaries[q] = next(iter(ends))
    boundaries[4] = end
    return start, boundaries


def reconstruct(company, ticker, metric: Metric, facts: list[Fact], year, q,
                periods, selected_concept=None, dimensions=()):
    label = f"Q{q}" if q != 0 else "FY"
    cell = Cell(company, ticker, metric.name, year, label, None, None, "Insufficient information")
    if not periods:
        cell.reasoning.append("No unique annual fiscal calendar anchor; transition years require review.")
        return cell
    annual_start, ends = periods
    end = ends.get(q or 4)
    previous = ends.get(q - 1) if q > 1 else None
    start = annual_start if q in (0, 1) else (
        (date.fromisoformat(previous) + timedelta(days=1)).isoformat() if previous else None)
    cell.start, cell.end = start, end
    cell.reasoning.append("Fiscal year is named by the calendar year of its annual period end; boundaries use actual disclosed durations.")
    if not end or (metric.kind != "instant" and not start):
        cell.reasoning.append("Quarter boundaries are not sufficiently supported by filing periods.")
        return cell
    candidates = [f for f in facts if f.unit == metric.unit and f.dimensions == dimensions and
                  (f.concept == selected_concept if selected_concept else
                   f.concept in {f"us-gaap:{t}" for t in metric.tags})]
    direct = [f for f in candidates if f.end == end and
              (f.start is None if metric.kind == "instant" else f.start == start)]
    selected, conflict = choose(direct)
    if conflict:
        cell.status = "Ambiguous or conflicting"
        cell.inputs = direct
        cell.warnings.append(conflict)
        return cell
    if selected:
        if metric.kind == 'flow' and q > 1:
            hi, hc = choose([f for f in candidates if f.start == annual_start and f.end == end])
            lo, lc = choose([f for f in candidates if f.start == annual_start and f.end == previous])
            if hc or lc or (hi and lo and hi.concept == lo.concept == selected.concept and
                           abs(hi.value-lo.value-selected.value) >
                           tolerance(hi)+tolerance(lo)+tolerance(selected)):
                cell.status = 'Ambiguous or conflicting'
                cell.inputs = list(dict.fromkeys([selected, *([hi] if hi else []), *([lo] if lo else [])]))
                cell.warnings.append('Standalone quarter conflicts with cumulative evidence or filing versions.')
                return cell
        cell.value, cell.unit, cell.inputs = selected.value, selected.unit, [selected]
        cell.status = "Explicitly zero" if selected.value == 0 else "Directly reported"
        cell.reasoning.append("Exact context, period, unit and consolidated scope matched; direct disclosure preferred.")
        return cell
    if metric.kind != "flow" or q in (0, 1):
        cell.reasoning.append("Balance sheets use exact dates; EPS, shares, ratios and other nonadditive measures are never differenced.")
        return cell
    upper = [f for f in candidates if f.start == annual_start and f.end == end]
    lower = [f for f in candidates if f.start == annual_start and f.end == previous]
    a, ca = choose(upper)
    b, cb = choose(lower)
    if ca or cb:
        cell.status, cell.inputs = "Ambiguous or conflicting", upper + lower
        cell.warnings.append(ca or cb)
    elif a and b:
        if a.concept != b.concept or a.unit != b.unit or a.dimensions != b.dimensions:
            cell.status = "Ambiguous or conflicting"
            cell.warnings.append("Cumulative inputs do not share one accounting concept, unit and scope.")
            cell.inputs = [a, b]
        else:
            cell.value, cell.unit, cell.inputs, cell.operation = a.value - b.value, a.unit, [a, b], "-"
            cell.status = "Mathematically calculated"
            cell.reasoning.append("Compatible cumulative periods share the fiscal start; subtract previous YTD from current YTD.")
            cell.warnings.append("Cross-filing basis comparability requires analyst review, including acquisitions, discontinued operations and restatements.")
    return cell


def derive(company, ticker, name, components, operators):
    first = components[0]
    cell = Cell(company, ticker, name, first.year, first.quarter, first.start, first.end,
                "Insufficient information")
    if any(c.value is None for c in components):
        cell.reasoning.append("A required reported component is unavailable or ambiguous.")
        return cell
    if any((c.end, c.unit) != (first.end, first.unit) or
           (c.start != first.start and c.start is not None) for c in components):
        cell.status = "Ambiguous or conflicting"
        return cell
    # Preserve the graph: component calculations may themselves contain subtraction.
    cell.value = first.value
    for op, c in zip(operators, components[1:]):
        cell.value = cell.value + c.value if op == "+" else cell.value - c.value
    cell.unit = first.unit
    cell.components = components
    cell.component_operators = operators
    cell.inputs = [f for c in components for f in c.inputs]
    cell.status = "Derived from reported components"
    cell.reasoning = [name, *[f"{c.id}: {c.formula}" for c in components]]
    cell.operation = "component graph"
    cell.warnings = list(dict.fromkeys(w for c in components for w in c.warnings))
    return cell
