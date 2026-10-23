import copy,json
from pathlib import Path
import pytest
from scripts.replay_leaper_mate_strategy import proposed_strategy,verify,key

SOURCE=Path('docs/research/data/leaper_rule_coordinates_20261024/mate7-review-handoff.json')

def handoff():return json.loads(SOURCE.read_text(encoding='utf-8'))

def test_supplied_policy_covers_all_actual_defenses():
    h=handoff();v=verify(h,proposed_strategy(h))
    assert v['root_WDL_for0']==1 and v['maximum_absolute_plies']==7
    assert v['leaf_count']==5
    # Every defender node expands its complete literal frontier, not only PV.
    defense=[n for n in v['nodes'] if n['side']==1 and n['terminal']['status']=='ongoing']
    assert any(len(n['legal_actions'])>1 for n in defense)
    assert all(n['legal_actions']==n['checked_child_actions'] for n in defense)
    assert sorted(v['terminal_absolute_plies'])==[5,7,7,7,7]

def test_omitting_offpv_attacker_policy_fails():
    h=handoff();policy=proposed_strategy(h)
    del policy[key(h['remaining_branch']['full_record'])]
    with pytest.raises(ValueError,match='missing or nonunique'):
        verify(h,policy)

def test_original_pv_alone_is_not_all_defense_proof():
    h=handoff();policy=proposed_strategy(h)
    prefix=h['cooperative_mate7_complete_record']['actions']
    policy={k:v for k,v in policy.items() if json.loads(k)['actions']==prefix[:len(json.loads(k)['actions'])]}
    with pytest.raises(ValueError,match='missing or nonunique'):
        verify(h,policy)

def test_false_shorter_bound_is_rejected():
    h=handoff()
    with pytest.raises(ValueError,match='exceeds claimed mate bound'):
        verify(h,proposed_strategy(h),max_plies=5)

def test_serialized_history_identity_cannot_be_renamed():
    h=handoff();h['full_initial_record']['ruleset_fingerprint']='0'*64
    with pytest.raises(ValueError):proposed_strategy(h)
