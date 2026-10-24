"""Reject consumer-boundary claims with incomplete or inconsistent evidence."""
from copy import deepcopy
import json
import pytest
from scripts.verify_leaper_history_context_packet import DEFAULT,check_consumer_boundary
from scripts.verify_leaper_ab_learning_packet import read

@pytest.fixture
def actual_consumer(tmp_path):
    _,packet=read(DEFAULT,tmp_path)
    return json.loads(packet['documents_utf8']['consumer/actual.json'])

def test_actual_core_suffix_equality_does_not_imply_hypothetical_leaf_equality(actual_consumer):
    receipt=check_consumer_boundary(actual_consumer)
    assert receipt['game_suffix_equal'] and receipt['hypothetical_heuristic_differs']
    assert receipt['literal_nodes']==100 and not receipt['production_defect_claim']

@pytest.mark.parametrize('damage',('past_key','missing_history','claimed_score'))
def test_inconsistent_counterexample_cannot_be_reported_as_verified(actual_consumer,damage):
    bad=deepcopy(actual_consumer)
    if damage=='past_key':bad['past_repetition_key']='0'*64
    elif damage=='missing_history':bad['rows'][1]['record']['actions']=[]
    else:bad['rows'][1]['hypothetical_D1_score']=bad['rows'][0]['hypothetical_D1_score']
    with pytest.raises(ValueError):check_consumer_boundary(bad)
