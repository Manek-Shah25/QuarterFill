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


def revenue_fact(fact):
    tag = fact.concept.split(':')[-1]
    return (tag in REVENUE_TAGS or (not fact.concept.startswith('us-gaap:') and
            bool(re.fullmatch(r'(?:Net|Total|External|Customer|Segment|Operating)?(?:Revenue|Revenues|Sales|NetSales)(?:FromExternalCustomers)?', tag))))


def axis_label(axis):
    name = axis.split(':')[-1].lower()
    if 'product' in name or 'service' in name:
        return 'Products and services'
    if 'geograph' in name or 'countr' in name:
        return 'Countries and regions'
    if 'segment' in name:
        return 'Business groups'
    return member_label(axis).removesuffix(' Axis')


def revenue_details(research, year):
    """Discover each disclosed dimensional slice; parentage requires exact scope.

    A child adds one axis to an actual reported parent context. Standalone product
    views remain separate: equal totals or similar names do not establish parentage.
    """
    periods = research.periods(year)
    if not periods:
        return []
    start, ends = periods
    facts = [f for f in research.facts if f.verified and f.unit == 'USD' and f.start
             and start <= f.start <= f.end <= ends[4] and revenue_fact(f)]
    scopes = {(f.concept, f.dimensions) for f in facts}
    groups = {}
    for fact in facts:
        for dim in fact.dimensions:
            axis, member = dim.split('=', 1)
            # Acquisitions, timing obligations and accounting adjustments are not
            # smaller revenue businesses. Keep those contexts out of this view.
            if any(x in axis.lower() for x in ('acquisition', 'consolidation', 'scenario', 'restatement', 'timing', 'contract')):
                continue
            parent = tuple(d for d in fact.dimensions if d != dim)
            if parent and (fact.concept, parent) not in scopes:
                continue
            groups.setdefault((fact.concept, parent, axis), {}).setdefault(member, []).append(fact)
    output = []
    for (concept, scope, axis), members in sorted(groups.items()):
        rows = []
        for member, observations in sorted(members.items()):
            fallback = member_label(member)
            # Prefer a literal disclosure label when it describes this member,
            # rather than the generic row label 'Revenue' or a parent heading.
            words = set(re.findall(r'[a-z]+', fallback.lower())) - {'and', 'other', 'of'}
            labels = [re.sub(r'\s*\(\d+\)\s*$', '', f.label).strip().rstrip('®™') for f in observations]
            normalized = re.sub(r'[^a-z0-9]', '', fallback.lower())
            usable = [label for label in labels if ':' not in label and (words.intersection(re.findall(r'[a-z]+', label.lower()))
                      or re.sub(r'[^a-z0-9]', '', label.lower()) == normalized)]
            label = min(usable, key=len) if usable else fallback
            dimensions = tuple(sorted((*scope, axis + '=' + member)))
            cells = [reconstruct(research.company['entityName'], research.submissions.get('tickers', [''])[0],
                     Metric(label, 'Segments', 'flow', (), (), 'USD'), research.facts, year, q,
                     periods, concept, dimensions) for q in (1, 2, 3, 4, 0)]
            rows.append({'name': label, 'dimensions': dimensions, 'cells': cells})
        parent_name = ' / '.join(member_label(d.split('=', 1)[1]) for d in scope) or 'Whole company'
        parent_cells = [reconstruct(research.company['entityName'], '', Metric(parent_name, 'Segments', 'flow', (), (), 'USD'),
                        research.facts, year, q, periods, concept, scope) for q in (1, 2, 3, 4, 0)]
        totals = [derive(research.company['entityName'], '', 'Sum of these groups',
                  [row['cells'][i] for row in rows], ['+'] * (len(rows)-1)) for i in range(5)]
        checks = []
        for total, parent_cell in zip(totals, parent_cells):
            if total.value is None or parent_cell.value is None:
                checks.append('We do not have enough information to check this total.')
            elif abs(total.value-parent_cell.value) <= sum(tolerance(f) for f in total.inputs + parent_cell.inputs):
                checks.append('These groups add up to the reported total for this view. Matching totals alone do not prove the groups never overlap.')
            else:
                checks.append('These groups do not add up to the reported total. Some may overlap or be missing. We have not filled the difference with a guess.')
        output.append({'name': axis_label(axis), 'parent': parent_name, 'scope': scope, 'axis': axis,
                       'concept': concept, 'rows': rows, 'parent_cells': parent_cells, 'totals': totals, 'checks': checks})
    return output


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
