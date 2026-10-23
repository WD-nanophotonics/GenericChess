"""Actual frozen tactical cases must not become invented outcome/price evidence."""
from copy import deepcopy
from pathlib import Path
import pytest
from scripts.leaper_saved_child_bounds import current_truth,propagate
from scripts.leaper_explorer_truth import load
from scripts.verify_leaper_saved_paths import verify_critical_cases


@pytest.fixture(scope='module')
def data():
    p=Path('docs/research/data/leaper_explorer_saved_paths_20261023')
    t=current_truth('docs/research/data/leaper_explorer_truth_20261023','docs/research/data/leaper_explorer_followup_20261023')
    u,_=propagate(t,load(p/'edges.json.gz'))
    return t,u,load(p/'new-critical-cases.json'),load('docs/research/data/leaper_explorer_truth_20261023/source-context.json.gz')


@pytest.mark.parametrize('damage',['source','chosen_bound','outcome','reference_count','query','tactical_scope'])
def test_actual_source_cases_reject_changed_claims(data,damage):
    t,u,original,context=data;p=deepcopy(original);q=p['new_record_actions'][0]
    if damage=='source':p['input_digest']='wrong'
    if damage=='chosen_bound':q['chosen_bounds']=[-1,-1]
    if damage=='outcome':q['actual_terminal']='checkmate'
    if damage=='reference_count':q['reference_count']=4
    if damage=='query':q['source_queries'][0][3]='Static'
    if damage=='tactical_scope':q['immediate_winning_action_exists']=False
    with pytest.raises(ValueError):verify_critical_cases(t,u,p,context)
