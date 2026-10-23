"""Training start, UNKNOWN, model-epoch and literal TD leaf boundaries."""
from copy import deepcopy
from pathlib import Path
import gzip,json
import pytest
from scripts.verify_leaper_one_epoch import verify
from scripts.leaper_h6_later_records import ContextBinder
from scripts.verify_leaper_epoch_control import verify as verify_control

BASE=Path('docs/research/data/leaper_h6_initial_truth_20261023')
P=Path('docs/research/data/leaper_frozen_pair_truth_20261024/learning-evidence.json.gz')


@pytest.fixture(scope='module')
def data():
    packet=json.loads(gzip.decompress(P.read_bytes()))['documents_utf8']
    return {k:[json.loads(s)for s in v.splitlines()]if k.endswith('jsonl')else json.loads(v)for k,v in packet.items()}


def test_actual_epoch_and_frozen_library_update_reproduce(data):
    r=verify(data['epoch-plan.json'],data['epoch-result.json'],data['epoch-episodes.jsonl'],BASE)
    assert r['verified']and r['counts']['episodes']==256 and r['counts']['queries']==637


def test_removing_a_training_start_cannot_claim_same_mu(data):
    rows=deepcopy(data['epoch-episodes.jsonl']);rows.pop(0)
    with pytest.raises(ValueError,match='128start'):verify(data['epoch-plan.json'],data['epoch-result.json'],rows,BASE)


def test_query_model_epoch_cannot_change_before_td_finish(data):
    rows=deepcopy(data['epoch-episodes.jsonl']);rows[0]['before'][1]=2
    with pytest.raises(ValueError,match='model epoch'):verify(data['epoch-plan.json'],data['epoch-result.json'],rows,BASE)


def test_actual_terminal_cannot_be_replaced_with_unknown_or_draw(data):
    rows=deepcopy(data['epoch-episodes.jsonl']);rows[0]['result']['outcome']=None
    with pytest.raises(ValueError,match='terminal outcome'):verify(data['epoch-plan.json'],data['epoch-result.json'],rows,BASE)


def test_td_gradient_requires_actual_literal_search_leaf(data):
    rows=deepcopy(data['epoch-episodes.jsonl']);rows[0]['queries'][0]['receipt']['pv_phi']=[7,7,7,7]
    with pytest.raises(ValueError,match='leaf/gradient'):verify(data['epoch-plan.json'],data['epoch-result.json'],rows,BASE)


def test_repeated_prefix_is_not_a_repeat2_ongoing_training_context(data):
    candidate=deepcopy(data['panel.json']['bound_contexts'][0]);candidate['prior_vertices'].append(candidate['prior_vertices'][0])
    with pytest.raises(ValueError,match='injective'):ContextBinder(BASE).bind(candidate)


def test_matched_unit_control_has_no_observed_trajectory_gain(data):
    r=verify_control(data['control-result.json'],data['control-episodes.jsonl'],data['epoch-episodes.jsonl'],BASE)
    assert r['verified']and r['counts']['reused_trajectories']==2
    assert all(s['different_complete_records']==0 and s['terminal_U0_gain']==0 for s in r['summary'])


def test_nonunit_epoch_cannot_be_relabelled_as_a_reused_unit_control(data):
    rows=deepcopy(data['epoch-episodes.jsonl']);rows[0]['before'][1]=2
    with pytest.raises(ValueError,match='nonunit'):
        verify_control(data['control-result.json'],data['control-episodes.jsonl'],rows,BASE)
