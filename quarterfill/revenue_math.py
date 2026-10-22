"""Evidence-backed interval and segment equations, with no guessed zeros."""
from collections import defaultdict, deque
from datetime import date, timedelta
from decimal import Decimal
from .engine import choose, tolerance, derive
from .models import Cell


def uncertainty(cell):
    return sum(tolerance(f) for f in cell.inputs)


def combine(name, components, signs, start, end, quarter, year):
    first = components[0]
    cell = Cell(first.company, first.ticker, name, year, quarter, start, end, 'Derived from reported components')
    cell.value = sum((c.value if sign == '+' else -c.value for c, sign in zip(components, signs)), Decimal(0))
    cell.unit = first.unit
    cell.inputs = list(dict.fromkeys(f for c in components for f in c.inputs))
    cell.components, cell.component_operators = components, signs[1:]
    cell.operation = 'component graph'
    cell.reasoning = ['Matching reported periods or a reconciled, stable group breakdown support this equation.']
    if len({f.accession for f in cell.inputs}) > 1:
        cell.warnings.append('Cross-filing basis comparability requires review; the selected reporting version is kept consistent.')
    return cell


class RevenueMath:
    def __init__(self, research, year, facts):
        self.research, self.year, self.facts = research, year, facts
        self.periods = research.periods(year)
        self.values = defaultdict(dict)
        self.names = {}
        if not self.periods:
            return
        start, ends = self.periods
        self.boundaries = {0: start, **{q: (date.fromisoformat(end)+timedelta(days=1)).isoformat() for q, end in ends.items()}}
        buckets = defaultdict(list)
        for f in facts:
            left = next((i for i, value in self.boundaries.items() if value == f.start), None)
            right = next((i for i, value in ends.items() if value == f.end), None)
            if left is not None and right is not None and left < right:
                buckets[(f.concept, f.dimensions, left, right)].append(f)
        for (concept, dims, left, right), observations in buckets.items():
            selected, conflict = choose(observations)
            cell = self.empty((concept, dims), (left, right))
            cell.inputs = observations if conflict else [selected]
            if conflict:
                cell.status = 'Ambiguous or conflicting'
            else:
                cell.value, cell.unit, cell.status = selected.value, selected.unit, 'Directly reported'
            self.values[(concept, dims)][(left, right)] = cell
        self.partitions = self.find_partitions()
        self.solve()

    def empty(self, key, span):
        left, right = span
        return Cell(self.research.company['entityName'], self.research.submissions.get('tickers', [''])[0],
                    self.names.get(key, 'Revenue'), self.year, 'FY' if span == (0, 4) else f'Q{right}',
                    self.boundaries.get(left), self.periods[1].get(right), 'Insufficient information')

    def find_partitions(self):
        tables = defaultdict(dict)
        for f in self.facts:
            if f.table:
                tables[(f.table, f.concept, f.start, f.end)][f.dimensions] = f
        families = defaultdict(set)
        proof = {}
        proof_reports = defaultdict(set)
        rejected = set()
        for (_, concept, _, _), rows in tables.items():
            for scope, parent in rows.items():
                by_axis = defaultdict(list)
                for dims, child in rows.items():
                    extra = set(dims)-set(scope)
                    if set(scope) < set(dims) and len(extra) == 1:
                        axis = next(iter(extra)).split('=', 1)[0]
                        if not any(x in axis.lower() for x in ('consolidation', 'acquisition', 'scenario', 'timing')):
                            by_axis[axis].append(child)
                for axis, children in by_axis.items():
                    if len(children) < 2:
                        continue
                    family = (concept, scope, axis)
                    members = tuple(sorted(f.dimensions for f in children))
                    families[family].add(members)
                    if abs(parent.value-sum(f.value for f in children)) <= sum(tolerance(f) for f in [parent, *children]):
                        proof[(family, members)] = [parent, *children]
                        proof_reports[(family, members)].add((parent.accession, parent.start, parent.end))
                    else:
                        rejected.add(family)
        # Changing or overlapping member sets are never treated as one complete family.
        self.remainders = []
        self.coexisting_sets = {}
        for family, sets in families.items():
            if len(sets) < 2 or family in rejected or any((family, members) not in proof for members in sets):
                continue
            shared_reports = set.intersection(*(proof_reports[(family, members)] for members in sets))
            if shared_reports:
                self.coexisting_sets[family] = sets
                continue
            common = set.intersection(*(set(members) for members in sets))
            if len(common) >= 2 and all(len(set(members)-common) == 1 for members in sets):
                self.remainders.append((family, common))
        return [((concept, scope), [(concept, d) for d in members], proof[((concept, scope, axis), members)])
                for (concept, scope, axis), sets in families.items()
                if (len(sets) == 1 or (concept, scope, axis) in self.coexisting_sets)
                and (concept, scope, axis) not in rejected
                for members in sets if ((concept, scope, axis), members) in proof
                and (concept, scope, axis) not in rejected]

    def temporal(self, key, span):
        graph = defaultdict(list)
        for (left, right), cell in self.values[key].items():
            if cell.value is not None:
                graph[left].append((right, cell, '+'))
                graph[right].append((left, cell, '-'))
        seen = {span[0]: (Decimal(0), [], [], Decimal(0))}
        queue = deque([span[0]])
        conflict = False
        while queue:
            point = queue.popleft()
            value, parts, signs, error = seen[point]
            for dest, cell, sign in graph[point]:
                candidate = value + (cell.value if sign == '+' else -cell.value)
                margin = error + uncertainty(cell)
                if dest in seen:
                    if abs(seen[dest][0]-candidate) > margin+seen[dest][3]:
                        conflict = True
                else:
                    seen[dest] = (candidate, parts+[cell], signs+[sign], margin)
                    queue.append(dest)
        if span[1] not in seen:
            return None
        _, parts, signs, _ = seen[span[1]]
        if conflict:
            result = self.empty(key, span)
            result.status = 'Ambiguous or conflicting'
            result.inputs = list(dict.fromkeys(f for _, c, _ in sum(graph.values(), []) for f in c.inputs))
            return result
        # Put positive terms first so every displayed equation starts with a real amount.
        ordered = sorted(zip(parts, signs), key=lambda x: x[1] != '+')
        template = self.empty(key, span)
        return combine(template.metric, [p for p, _ in ordered], [s for _, s in ordered],
                       template.start, template.end, template.quarter, self.year)

    def solve(self):
        spans = [(a, b) for a in range(4) for b in range(a+1, 5) if a in self.boundaries and b in self.boundaries]
        for key in list(self.values):
            conflicts = {span: candidate for span in list(self.values[key])
                         if (candidate := self.temporal(key, span)) and candidate.status == 'Ambiguous or conflicting'}
            self.values[key].update(conflicts)
        for _ in range(12):
            changes = 0
            for key in list(self.values):
                for span in spans:
                    old = self.values[key].get(span)
                    if old is None:
                        candidate = self.temporal(key, span)
                        if candidate:
                            self.values[key][span] = candidate
                            changes += 1
            for parent, children, proof in self.partitions:
                for span in spans:
                    keys = [parent, *children]
                    cells = [self.values[key].get(span) for key in keys]
                    missing = [i for i, c in enumerate(cells) if c is None or c.value is None]
                    if len(missing) != 1:
                        continue
                    index = missing[0]
                    if cells[index] is not None and cells[index].status == 'Ambiguous or conflicting':
                        continue
                    parts = cells[1:] if index == 0 else [cells[0], *[c for i, c in enumerate(cells[1:], 1) if i != index]]
                    signs = ['+']*len(parts) if index == 0 else ['+']+['-']*(len(parts)-1)
                    template = self.empty(keys[index], span)
                    candidate = combine(template.metric, parts, signs, template.start, template.end, template.quarter, self.year)
                    candidate.disclosure_evidence = [{'url': proof[0].url,
                        'quote': proof[0].section, 'rationale': 'The complete member set reconciles in the same original-year disclosure table.',
                        'source_matched': True}]
                    self.values[keys[index]][span] = candidate
                    changes += 1
            # An independent equation must agree; the first successful route does
            # not get to override a different supported route.
            bad = set()
            for parent, children, _ in self.partitions:
                for span in spans:
                    cells = [self.values[key].get(span) for key in [parent, *children]]
                    if any(c is None or c.value is None for c in cells):
                        continue
                    if abs(cells[0].value-sum(c.value for c in cells[1:])) > sum(uncertainty(c) for c in cells):
                        bad.update(id(c) for c in cells if c.components)
            if bad:
                while True:
                    added = 0
                    for values in self.values.values():
                        for cell in values.values():
                            if cell.value is not None and (id(cell) in bad or any(id(c) in bad for c in cell.components)):
                                bad.add(id(cell))
                                cell.value, cell.status = None, 'Ambiguous or conflicting'
                                cell.warnings.append('Independent revenue equations disagree; calculated descendants were withdrawn.')
                                added += 1
                    changes += added
                    if not added:
                        break
            if not changes:
                break

    def cells(self, concept, dimensions, label):
        key = (concept, dimensions)
        self.names[key] = label
        output = []
        for span in ((0, 1), (1, 2), (2, 3), (3, 4), (0, 4)):
            cell = self.values[key].get(span) or self.empty(key, span)
            cell.metric = label
            if cell.value is None:
                cell.reasoning = ['Checked reported quarters, cumulative amounts, yearly totals, sums of smaller groups, and parent revenue minus the other groups.',
                                  'The available numbers do not give one consistent answer. Missing amounts were not treated as zero.']
            output.append(cell)
        return output
