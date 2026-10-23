"""Incoming proof-layer corruption must fail at actual Core bindings."""
from copy import deepcopy
from pathlib import Path
import pytest

from scripts.leaper_explorer_truth import load,materialize
from scripts.leaper_explorer_supplement import apply_supplement,verify_supplement
from scripts.leaper_local_truth import verify_layer,derive


@pytest.fixture(scope='module')
def inputs():
    old=Path('docs/research/data/leaper_explorer_truth_20261023')
    p=Path('docs/research/data/leaper_explorer_followup_20261023')
    raw=load(old/'truth.json.gz');supp=load(p/'supplement.json.gz')
    truth=materialize(raw,load(old/'cooperative.json'),load(old/'observed-suffixes.json.gz'))
    return raw,supp,load(p/'colour-certificate.json'),apply_supplement(truth,supp),load(p/'local-layer.json.gz')


def test_omitting_a_colour_root_legal_action_is_not_complete_action_truth(inputs):
    raw,supp,cert,_,_=inputs;supp=deepcopy(supp)
    row=next(r for r in supp['rows']if 'action_bounds'in r);row['action_bounds'].pop()
    with pytest.raises(ValueError,match='action bindings'):verify_supplement(raw,supp,cert)


def test_existential_path_cannot_smuggle_an_exact_wdl_label(inputs):
    raw,supp,cert,_,_=inputs;supp=deepcopy(supp)
    row=next(r for r in supp['rows']if 'witness'in r);row['wdl_bounds']=[1,1]
    with pytest.raises(ValueError,match='outside scope'):verify_supplement(raw,supp,cert)


def test_self_consistent_fake_terminal_row_still_fails_core(inputs):
    _,_,_,truth,layer=inputs;layer=deepcopy(layer)
    row=next(r for r in layer['rows']if any(c['terminal']=='ongoing'for c in r['children']))
    c=next(c for c in row['children']if c['terminal']=='ongoing')
    c.update(terminal='max_ply',terminal_winner=None,wdl_bounds=[0,0])
    row['derived']=derive(row['children'])
    with pytest.raises(ValueError,match='Core certificate'):verify_layer(truth,layer)


def test_wrong_full_history_child_binding_is_not_fuzzy_joined(inputs):
    _,_,_,truth,layer=inputs;layer=deepcopy(layer)
    layer['rows'][0]['children'][0]['child_id']='0'*64
    with pytest.raises(ValueError,match='Core certificate'):verify_layer(truth,layer)
