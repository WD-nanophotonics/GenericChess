"""Real cross-rule all-defense failure and transport corruption controls."""
from copy import deepcopy
from pathlib import Path
import pytest
from scripts.leaper_explorer_truth import load
from scripts.leaper_h6_pair_certificates import dual_replay

PACKET=Path('docs/research/data/leaper_h6_initial_truth_20261023')


@pytest.fixture(scope='module')
def inputs():
    return load(PACKET/'pair-certificates.json.gz'),load(PACKET/'adjacent-pairs.json.gz')


def test_actual_paths_transfer_but_all_defense_roots_do_not(inputs):
    certs,pairs=inputs
    out=dual_replay(PACKET,certs,pairs)
    assert out['counts']==dict(prefix_nodes=80,paired_transitions=64,
        public_action_rebindings=64,added_legal_actions=16,removed_legal_actions=0,
        rebound_subtree_verified=64,same_terminal_result=80,same_check_history=80)
    for row in out['rows']:
        assert row['direct_transfer_reason']=='root_binding_mismatch'
        assert row['root_rebound_verified'] is False
        for node in row['nodes']:
            assert node['left_actor_history']==node['right_actor_history']
            assert node['repetition_partition']==node['right_repetition_partition']
            assert node['rebound_verified']==(node['ply']>0)
            assert len(node['added_actions'])==(node['ply']==0)


@pytest.mark.parametrize('corruption',['omit_root','duplicate_root','wrong_right','wrong_geometry','omit_defense'])
def test_corrupted_cross_rule_evidence_rejected(inputs,corruption):
    certs,pairs=deepcopy(inputs)
    if corruption=='omit_root':certs['rows'].pop()
    elif corruption=='duplicate_root':certs['rows'].append(certs['rows'][0])
    elif corruption=='wrong_right':certs['rows'][0]['right_id']=certs['rows'][1]['right_id']
    elif corruption=='wrong_geometry':certs['rows'][0]['left_forced_loss_certificate']['tree']['edges'][0]['choice']['action']['geometry_id']='absent'
    elif corruption=='omit_defense':certs['rows'][0]['left_forced_loss_certificate']['tree']['edges'].pop()
    with pytest.raises(ValueError):dual_replay(PACKET,certs,pairs)


def test_replay_cap_does_not_create_transfer_claim(inputs):
    certs,pairs=inputs
    with pytest.raises(RuntimeError,match='CAP_UNKNOWN'):
        dual_replay(PACKET,certs,pairs,max_nodes=6)
