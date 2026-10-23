"""Corruption controls for actual-prefix safety and retained query evidence."""
from copy import deepcopy
from pathlib import Path
import pytest
from scripts.leaper_explorer_truth import load
from scripts.leaper_clock_rebinding import verify_history_draw_safety
from scripts.verify_leaper_h6_pair_transfer import verify_material_escape_receipts,verify_onset_reuse,verify_positive_price_cells

DATA=Path(__file__).resolve().parents[2]/'docs/research/data'


@pytest.fixture
def safety():
    domain=load(DATA/'leaper_pair_transfer_20261024/mask5-domain.json.gz')
    packet=load(DATA/'leaper_history_barriers_20261024/repeat4-counterexample.json')
    row=packet['rows'][0]
    return domain,packet['rule'],row['record'],deepcopy(row['draw_safety'])


def test_actual_count3_safety_has_complete_attacker_frontier(safety):
    receipt=verify_history_draw_safety(*safety)
    assert receipt['verified']and receipt['value_for0']==0
    assert receipt['counts']=={'vertices':258,'Core_edges':547,'count3_draw_exits':1}


def test_a_prior_count_two_vertex_is_not_a_draw_barrier(safety):
    safety[3]['barriers']=[100]
    with pytest.raises(ValueError,match='actual count3'):
        verify_history_draw_safety(*safety)


def test_omitting_an_attacker_choice_cannot_certify_draw(safety):
    row=next(r for r in safety[3]['vertices']if r.get('actor')==0 and len(r['selected_action_indices'])>1)
    row['selected_action_indices'].pop();row['children'].pop()
    with pytest.raises(ValueError,match='attacker frontier incomplete'):
        verify_history_draw_safety(*safety)


def test_defender_must_supply_an_actual_safe_action(safety):
    row=next(r for r in safety[3]['vertices']if r.get('actor')==1)
    row['selected_action_indices']=[];row['children']=[]
    with pytest.raises(ValueError,match='one legal defender'):
        verify_history_draw_safety(*safety)


def test_missing_safety_successor_fails_closed(safety):
    safety[3]['vertices'].pop()
    with pytest.raises(ValueError,match='missing child'):
        verify_history_draw_safety(*safety)


def test_saved_material_query_checks_literal_leaf_and_fixed_weight():
    data=load(DATA/'leaper_history_barriers_20261024/material-control.json')
    row=data['rows'][0];row['receipt']['value']+=.25
    with pytest.raises(ValueError,match='feature/value'):
        verify_material_escape_receipts(data,DATA/'leaper_h6_initial_truth_20261023')


def test_saved_material_query_checks_selection_and_missing_slots():
    data=load(DATA/'leaper_history_barriers_20261024/material-control.json');data['rows'].pop()
    with pytest.raises(ValueError,match='missing or duplicate'):
        verify_material_escape_receipts(data,DATA/'leaper_h6_initial_truth_20261023')


def onset_arguments():
    p=DATA/'leaper_history_barriers_20261024'
    return [load(p/'onset-depth-inputs.json.gz'),load(p/'onset-depth-results.json.gz'),
        load(p/'onset-depth-truth.json.gz'),load(p/'shallow-first-fork.json'),
        load(p/'first-fork-nominal.json'),load(DATA/'leaper_pair_transfer_20261024/depth-results.json.gz'),
        load(p/'sparse-depth-results.json.gz')]


def test_already_executed_query_cannot_be_relabelled_new():
    args=onset_arguments();row=next(r for r in args[1]['rows']if r['receipt_origin']['kind']=='REUSED')
    row['receipt_origin']={'kind':'NEW','runtime_source_sha':args[0]['source_runtime_sha']}
    with pytest.raises(ValueError,match='reused receipt changed or relaunched'):
        verify_onset_reuse(*args)


def test_incremental_work_is_not_total_retained_query_work():
    args=onset_arguments();assert args[1]['new_nodes']<args[1]['nodes']
    args[1]['new_nodes']=args[1]['nodes']
    with pytest.raises(ValueError,match='incremental cost'):
        verify_onset_reuse(*args)


def test_free_root_parameter_is_not_a_free_search_leaf_gradient():
    data=load(DATA/'leaper_history_barriers_20261024/material-control.json')
    receipt=verify_material_escape_receipts(data,DATA/'leaper_h6_initial_truth_20261023')
    assert receipt['counts']['nonzero_root_free_gradients']==96
    assert receipt['counts']['nonzero_PV_free_gradients']==0


def test_positive_price_gradient_is_not_root_decision_improvement():
    data=load(DATA/'leaper_history_barriers_20261024/price-regions.json')
    receipt=verify_positive_price_cells(data,DATA/'leaper_h6_initial_truth_20261023')
    assert receipt['all_positive_interior_affine_crossings']==['1']
    assert receipt['positive_cell_sensitive_roots']=={'1':{'action':0,'quality':0},'2':{'action':0,'quality':0}}
    assert receipt['D1_nonzero_free_gradient_by_root_WDL']=={'-1':64}


def test_price_quality_report_must_match_literal_maximizers():
    data=load(DATA/'leaper_history_barriers_20261024/price-regions.json')
    data['rows'][0]['profiles'][0]['depths'][0]['uniform_tie_error']='1'
    with pytest.raises(ValueError,match='quality/gradient'):
        verify_positive_price_cells(data,DATA/'leaper_h6_initial_truth_20261023')
