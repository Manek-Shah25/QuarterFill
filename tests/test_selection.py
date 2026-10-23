from quarterfill.selection import sync_cell_selection


def test_cell_click_updates_item_year_and_period_together():
    state = {'table': {'selection': {'cells': [[1, 'Q3']]}}, 'metric':'Cash', 'year':2025, 'quarter':1}
    rows = [{'metric':'Cash','year':2024},{'metric':'Debt (current)','year':2025}]
    sync_cell_selection(state,'table',rows,{'Q3':{'quarter':3}})
    assert (state['metric'],state['year'],state['quarter']) == ('Debt (current)',2025,3)
    # A manual choice after the callback is retained until another selection event.
    state['quarter'] = 4
    assert state['quarter'] == 4


def test_year_total_and_blank_cells_have_the_same_selection_path():
    state = {'table': {'selection': {'cells': [[0, 'Year total']]}}}
    sync_cell_selection(state,'table',[{'metric':'Revenue','year':2024}],{'Year total':{'quarter':0}},'open')
    assert state['quarter']==0 and state['year']==2024 and state['open']


def test_label_columns_and_out_of_range_rows_do_not_change_explanation():
    for cells in ([], [[0,'Line item']], [[0,'Year']], [[9,'Q1']], [[-1,'Q1']], [[True,'Q1']], [[0,'Q1'],[1,'Q2']]):
        state = {'table': {'selection': {'cells':cells}}, 'metric':'Cash','quarter':4}
        sync_cell_selection(state,'table',[{'metric':'Inventory'}],{'Q1':{'quarter':1}})
        assert state['metric']=='Cash' and state['quarter']==4
