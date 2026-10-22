"""Keep business-segment revenue separate from overlapping product/geography views."""
import re
from .concepts import Metric
from .engine import reconstruct, derive, tolerance


REVENUE_TAGS = ('RevenueFromContractWithCustomerExcludingAssessedTax',
                'RevenueFromContractWithCustomerIncludingAssessedTax', 'Revenues', 'SalesRevenueNet',
                'SegmentReportingInformationRevenueFromExternalCustomers')


def member_label(member):
    name = member.split(':')[-1]
    name = re.sub(r'(Segment)?Member$', '', name)
    name = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', name)
    name = re.sub(r'([A-Z])([A-Z][a-z])', r'\1 \2', name)
    return name.replace('_', ' ')


def segment_build(research, year):
    """One exact axis/concept per build; never combine product subtotals or axes."""
    periods = research.periods(year)
    if not periods:
        return []
    # Resolve rounded comparative versions in consolidated revenue before checking sums.
    if hasattr(research, 'cell'):
        for q in (1, 2, 3, 4, 0):
            research.cell('Revenue', year, q)
    start, ends = periods
    groups = {}
    for fact in research.facts:
        if (not fact.verified or fact.unit != 'USD' or len(fact.dimensions) != 1
                or not fact.start or not start <= fact.start <= fact.end <= ends[4]
                or fact.concept.split(':')[-1] not in REVENUE_TAGS):
            continue
        axis, member = fact.dimensions[0].split('=', 1)
        if not any(word in axis.lower() for word in ('businesssegment', 'operatingsegment', 'reportablesegment')):
            continue
        groups.setdefault((axis, fact.concept), set()).add(member)
    builds = []
    for (axis, concept), members in sorted(groups.items()):
        rows = {}
        for member in sorted(members):
            label = member_label(member)
            metric = Metric(label, 'Segments', 'flow', (), (), 'USD')
            rows[label] = [reconstruct(research.company['entityName'], research.submissions.get('tickers', [''])[0],
                          metric, research.facts, year, q, periods, concept, (axis + '=' + member,))
                           for q in (1, 2, 3, 4, 0)]
        totals, checks = [], []
        for i, q in enumerate((1, 2, 3, 4, 0)):
            components = [cells[i] for cells in rows.values()]
            total = derive(research.company['entityName'], '', 'Sum of segments', components, ['+'] * (len(components)-1))
            consolidated = reconstruct(research.company['entityName'], '',
                Metric('Company revenue', 'Segments', 'flow', (), (), 'USD'), research.facts,
                year, q, periods, concept)
            totals.append((total, consolidated))
            if total.value is None or consolidated.value is None or not consolidated.verified:
                checks.append('Not enough information to check the total.')
            else:
                allowed = sum(tolerance(f) for f in total.inputs + consolidated.inputs)
                checks.append('The segments add up to company revenue.' if abs(total.value-consolidated.value) <= allowed
                              else 'These segments do not add up to company revenue. They may overlap or leave something out.')
        builds.append({'rows': rows, 'totals': totals, 'checks': checks, 'concept': concept, 'axis': axis})
    # Prefer the company's ordinary revenue definition, with the most reported segments.
    builds.sort(key=lambda b: (REVENUE_TAGS.index(b['concept'].split(':')[-1]), -len(b['rows'])))
    return builds
