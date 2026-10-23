"""Translate a table selection to the existing explanation controls."""


def sync_cell_selection(state, table_key, row_targets, period_targets, open_key=None):
    cells = state.get(table_key, {}).get('selection', {}).get('cells', [])
    if len(cells) != 1 or len(cells[0]) != 2:
        return
    row, column = cells[0]
    if not isinstance(row, int) or isinstance(row, bool) or not 0 <= row < len(row_targets):
        return
    if column not in period_targets:
        return
    state.update(row_targets[row])
    state.update(period_targets[column])
    if open_key:
        state[open_key] = True
