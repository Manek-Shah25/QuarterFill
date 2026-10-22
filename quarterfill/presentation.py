"""Plain-language views of financial evidence. Accounting stays in the engine."""
from datetime import date
from decimal import Decimal


STATUS_LABELS = {
    'Directly reported': 'Found in a report',
    'Reported under alternate label': 'Found in a report',
    'Mathematically calculated': 'Calculated',
    'Derived from reported components': 'Calculated',
    'Explicitly zero': 'Reported as zero',
    'Ambiguous or conflicting': 'Reports disagree',
    'Filing verification unavailable': 'Could not check the reports',
    'Not applicable': 'Does not apply',
    'Not separately disclosed': 'Not shown separately',
    'Insufficient information': 'Not enough information',
}


def amount(value, unit='USD', compact=False):
    if value is None:
        return '—'
    value = Decimal(str(value))
    if compact and unit == 'USD':
        return f'{value / Decimal(1000000):,.3f}'
    if unit == 'USD':
        digits = 0 if value == value.to_integral_value() else 2
        return ('−' if value < 0 else '') + f'${abs(value):,.{digits}f}'
    if unit == 'USD/shares':
        return ('−' if value < 0 else '') + f'${abs(value):,.2f} per share'
    if unit == 'shares':
        return f'{value:,.0f} shares'
    if unit == '%':
        return f'{value:,.2f}%'
    return f'{value:,.2f} {unit}'


def readable_date(value):
    return date.fromisoformat(value).strftime('%b %d, %Y').replace(' 0', ' ') if value else ''


def period(start, end):
    if not end:
        return 'The reporting dates are not clear yet.'
    return f'{readable_date(start)} to {readable_date(end)}' if start else f'As of {readable_date(end)}'


def quarter_name(quarter):
    return 'Full year' if quarter == 'FY' else f'Quarter {quarter[1:]}'


def input_name(cell, index):
    if cell.operation == '-' and len(cell.inputs) == 2:
        q = int(cell.quarter[1:]) if cell.quarter.startswith('Q') else 4
        count = q if index == 0 else q - 1
        return 'Full year' if count == 4 else ('Quarter 1' if count == 1 else f'First {count} quarters')
    return 'Reported amount'


def explanation(cell):
    result = {'label': STATUS_LABELS.get(cell.status, 'Needs checking'), 'steps': [], 'formula': '', 'note': ''}
    if cell.value is None:
        if cell.status == 'Ambiguous or conflicting':
            result['steps'] = ['The reports show different amounts for the same period.',
                               'We left this number blank because choosing one could be misleading.']
        elif cell.status == 'Filing verification unavailable':
            result['steps'] = ['We could not open all the reports needed to check this number.',
                               'A blank here does not mean zero.']
        elif cell.status == 'Not applicable':
            result['steps'] = ['The supporting report says this item does not apply.']
        elif cell.status == 'Not separately disclosed':
            result['steps'] = ['The company did not show this item on its own. It may be included in another amount.']
        else:
            result['steps'] = ['We could not find enough matching information to give a reliable number.',
                               'We leave it blank instead of guessing.']
        if cell.reasoning and cell.reasoning[0].startswith('Checked reported quarters,'):
            result['steps'].append('We checked quarterly amounts, running totals, the full year, and whether other groups could fill the gap.')
            result['steps'].append('Two filled quarters alone cannot tell us the other two. A blank also does not prove the company does not use this item.')
        if 'EPS' in cell.metric or 'shares' in cell.metric.lower():
            result['note'] = 'Per-share amounts and average share counts cannot be found by simple subtraction.'
        return result
    if cell.operation == 'percentage':
        numerator, denominator = cell.components
        result['steps'] = [f'Divide {numerator.metric.lower()} by company revenue for the same period.',
                           'Multiply by 100 to show the share as a percentage.']
        result['formula'] = f'{amount(numerator.value, numerator.unit)} ÷ {amount(denominator.value, denominator.unit)} × 100 = {amount(cell.value, cell.unit)}'
    elif cell.components:
        result['steps'] = [f'Start with {cell.components[0].metric.lower()}.']
        for op, component in zip(cell.component_operators, cell.components[1:]):
            result['steps'].append(f'{"Add" if op == "+" else "Subtract"} {component.metric.lower()}.')
        expression = amount(cell.components[0].value, cell.unit)
        for op, component in zip(cell.component_operators, cell.components[1:]):
            expression += f' {"+" if op == "+" else "−"} {amount(component.value, cell.unit)}'
        result['formula'] = expression + ' = ' + amount(cell.value, cell.unit)
        result['note'] = 'Each part comes from the company’s reports. Different definitions can give different results.'
    elif cell.operation == '-' and len(cell.inputs) == 2:
        a, b = cell.inputs
        result['steps'] = [f'The company reported {amount(a.value, a.unit)} for the {input_name(cell, 0).lower()}.',
                           f'That total includes {amount(b.value, b.unit)} from the {input_name(cell, 1).lower()}.',
                           f'Subtract the earlier amount. What is left belongs to {quarter_name(cell.quarter).lower()}.']
        result['formula'] = f'{amount(a.value, a.unit)} − {amount(b.value, b.unit)} = {amount(cell.value, cell.unit)}'
    elif cell.start is None or (cell.inputs and all(f.start is None for f in cell.inputs)):
        result['steps'] = ['This is the amount the company reported on that date.',
                           'It is a balance at one point in time, so we do not subtract another quarter.']
    else:
        result['steps'] = ['The company already reported this number for this period.',
                           'No calculation was needed.']
    if not cell.verified:
        result['note'] = 'We found the amount in SEC data, but have not checked it against the original report yet.'
    elif any('comparability' in warning or 'basis' in warning for warning in cell.warnings):
        result['note'] = 'These amounts come from separate reports. Changes in the business or reporting may affect the comparison.'
    return result
