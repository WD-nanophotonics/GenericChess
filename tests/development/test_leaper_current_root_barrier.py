"""A count3 current root is not an already-ended repeat4 arrival."""
from copy import deepcopy
from pathlib import Path
import pytest
from scripts.leaper_explorer_truth import load
from scripts.leaper_clock_rebinding import verify_history_draw_safety

P=Path('docs/research/data/leaper_frozen_pair_truth_20261024/current-root-barrier.json.gz')


def test_actual_count3_current_root_keeps_its_complete_outgoing_frontier():
    r=load(P);cert=dict(target_rule=r['rule'],positions=r['positions'])
    v=verify_history_draw_safety(cert,r['rule'],r['record'],r['safety'])
    assert v['verified']and v['counts']==dict(vertices=261,Core_edges=551,count3_draw_exits=1)


def test_same_position_without_the_two_actual_cycles_cannot_be_a_barrier():
    r=load(P);record=deepcopy(r['record']);record['actions']=record['actions'][:2]
    with pytest.raises(ValueError,match='lacks actual count3'):
        verify_history_draw_safety(dict(target_rule=r['rule'],positions=r['positions']),r['rule'],record,r['safety'])


def test_a_current_root_is_not_permission_to_omit_its_attacker_reply():
    r=load(P);safety=deepcopy(r['safety']);row=next(x for x in safety['vertices']if x['index']==safety['root']);row['selected_action_indices'].pop()
    with pytest.raises(ValueError,match='frontier incomplete'):
        verify_history_draw_safety(dict(target_rule=r['rule'],positions=r['positions']),r['rule'],r['record'],safety)
