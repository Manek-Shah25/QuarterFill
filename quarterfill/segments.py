"""Keep business-segment revenue separate from overlapping product/geography views."""
import re
from .revenue_math import RevenueMath
from .engine import derive, tolerance
from .models import Cell, stable_id
from decimal import Decimal


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


def revenue_model(research, year):
    periods = research.periods(year)
    if not periods:
        return None
    start, ends = periods
    # Use the selected year's own filings as one reproducible reporting basis.
    # Later comparative reclassifications must not replace only part of a build.
    basis_year = getattr(research, 'revenue_basis_year', year)
    basis_periods = research.periods(basis_year)
    basis_start, basis_ends = basis_periods if basis_periods else (start, ends)
    accessions = {f['accessionNumber'] for f in getattr(research, 'filings', [])
                  if basis_start <= f.get('reportDate', '') <= basis_ends[4]}
    facts = [f for f in research.facts if f.verified and f.unit == 'USD' and revenue_fact(f)
             and (not hasattr(research, 'filings') or f.accession in accessions)
             and f.start and start <= f.start <= f.end <= ends[4]
             and not any(re.search(r'Intersegment|Elimination|ConsolidationAdjustment|Restatement', d, re.I) for d in f.dimensions)]
    signature = (year, tuple(f.id for f in facts))
    cache = getattr(research, '_revenue_models', {})
    if signature not in cache:
        cache[signature] = RevenueMath(research, year, facts)
        research._revenue_models = cache
    return cache[signature]


def supplemental_rows(model, concept, scope, label):
    if not scope:
        return {}
    parents = model.cells(concept, scope, label + ' revenue')
    company = model.cells(concept, (), 'Company revenue')
    shares = []
    for numerator, denominator in zip(parents, company):
        cell = Cell(numerator.company, numerator.ticker, label + ' — % of company revenue', numerator.year,
                    numerator.quarter, numerator.start, numerator.end, 'Insufficient information', unit='%')
        if numerator.value is not None and denominator.value not in (None, 0):
            cell.value = numerator.value / denominator.value * Decimal(100)
            cell.status, cell.operation = 'Derived from reported components', 'percentage'
            cell.components, cell.component_operators = [numerator, denominator], ['/']
            cell.inputs = list(dict.fromkeys(numerator.inputs + denominator.inputs))
        shares.append(cell)
    output = {'% of company revenue': shares}
    genomics = [dims for c, dims in model.values if c == concept and set(scope) < set(dims)
                and len(dims) == len(scope)+1 and 'genom' in next(iter(set(dims)-set(scope))).split('=', 1)[1].lower()]
    if len(genomics) == 1:
        excluded = model.cells(concept, genomics[0], 'Genomics revenue')
        output['Core revenue (minus Genomics)'] = [derive(parents[0].company, parents[0].ticker,
            label + ' — core revenue (minus Genomics)', [a, b], ['-']) for a, b in zip(parents, excluded)]
    return output


def revenue_details(research, year):
    """Discover each disclosed dimensional slice; parentage requires exact scope.

    A child adds one axis to an explicitly reported dimensional scope. Standalone product
    views remain separate: equal totals or similar names do not establish parentage.
    """
    periods = research.periods(year)
    if not periods:
        return []
    start, ends = periods
    model = revenue_model(research, year)
    facts = model.facts
    groups = {}
    for fact in facts:
        for dim in fact.dimensions:
            axis, member = dim.split('=', 1)
            # Acquisitions, timing obligations and accounting adjustments are not
            # smaller revenue businesses. Keep those contexts out of this view.
            if any(x in axis.lower() for x in ('acquisition', 'consolidation', 'scenario', 'restatement', 'timing', 'contract')):
                continue
            parent = tuple(d for d in fact.dimensions if d != dim)
            # A product belongs inside a business segment, not the reverse.
            # Keep reverse cross-tab cuts out of the smaller-business menu.
            if 'segment' in axis.lower() and parent and not any('segment' in d.split('=', 1)[0].lower() for d in parent):
                continue
            groups.setdefault((fact.concept, parent, axis), {}).setdefault(member, []).append(fact)
    output = []
    views = []
    for key, members in sorted(groups.items()):
        alternatives = model.coexisting_sets.get(key)
        if alternatives:
            for dimensions in sorted(alternatives):
                views.append((key, {member: facts for member, facts in members.items()
                             if tuple(sorted((*key[1], key[2]+'='+member))) in dimensions}))
        else:
            views.append((key, members))
    for (concept, scope, axis), members in views:
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
            cells = model.cells(concept, dimensions, label)
            rows.append({'name': label, 'dimensions': dimensions, 'cells': cells})
        parent_name = ' / '.join(member_label(d.split('=', 1)[1]) for d in scope
                                 if 'consolidation' not in d.split('=', 1)[0].lower()) or 'Whole company'
        parent_cells = model.cells(concept, scope, parent_name + ' revenue')
        changed_names = []
        for family, common in model.remainders:
            if family != (concept, scope, axis):
                continue
            common_rows = [r for r in rows if r['dimensions'] in common]
            changed_names = [r['name'] for r in rows if r['dimensions'] not in common]
            label = 'Remaining revenue (' + ' / '.join(changed_names) + ')'
            remaining = [derive(parent_cells[0].company, parent_cells[0].ticker, label,
                         [parent_cells[i], *[row['cells'][i] for row in common_rows]], ['-'] * len(common_rows)) for i in range(5)]
            rows = common_rows + [{'name': label, 'dimensions': (), 'cells': remaining}]
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
                       'concept': concept, 'rows': rows, 'parent_cells': parent_cells, 'totals': totals, 'checks': checks,
                       'supplemental': supplemental_rows(model, concept, scope, parent_name), 'changed_names': changed_names,
                       'identity': stable_id([concept, scope, axis, [r['dimensions'] for r in rows]])})
    return output


def segment_build(research, year):
    """One exact axis/concept per build; never combine product subtotals or axes."""
    periods = research.periods(year)
    if not periods:
        return []
    model = revenue_model(research, year)
    start, ends = periods
    groups = {}
    for fact in model.facts:
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
            rows[label] = model.cells(concept, (axis + '=' + member,), label)
        totals, checks = [], []
        for i, q in enumerate((1, 2, 3, 4, 0)):
            components = [cells[i] for cells in rows.values()]
            total = derive(research.company['entityName'], '', 'Sum of segments', components, ['+'] * (len(components)-1))
            consolidated = model.cells(concept, (), 'Company revenue')[i]
            totals.append((total, consolidated))
            if total.value is None or consolidated.value is None or not consolidated.verified:
                checks.append('Not enough information to check the total.')
            else:
                allowed = sum(tolerance(f) for f in total.inputs + consolidated.inputs)
                checks.append('The segments add up to company revenue.' if abs(total.value-consolidated.value) <= allowed
                              else 'These segments do not add up to company revenue. They may overlap or leave something out.')
        builds.append({'rows': rows, 'totals': totals, 'checks': checks, 'concept': concept, 'axis': axis,
                       'supplemental': {member_label(m): supplemental_rows(model, concept, (axis+'='+m,), member_label(m)) for m in members}})
    # Prefer the company's ordinary revenue definition, with the most reported segments.
    builds.sort(key=lambda b: (REVENUE_TAGS.index(b['concept'].split(':')[-1]), -len(b['rows'])))
    return builds
