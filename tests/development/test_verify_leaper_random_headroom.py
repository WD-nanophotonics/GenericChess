"""Anti-inflation controls on the actual full-history chance certificate."""
import copy
from pathlib import Path
import pytest
from scripts.leaper_explorer_truth import load
from scripts.verify_leaper_random_headroom import verify

PACKET=Path('docs/research/data/leaper_scope_and_headroom_20261024/twoa-graph.json.gz')
CERT=Path('docs/research/data/leaper_trajectory_chance_20261024/headroom.json')

def test_actual_controller_lower_binds_complete_core_and_history():
    r=verify(load(PACKET),load(CERT))
    assert r['verified'] and r['counts']['Core_vertices']==78
    assert [row['lower']for row in r['rows']]==['223/2835','61/144']

def test_omitting_an_actual_prior_count3_barrier_is_rejected():
    cert=load(Path('docs/research/data/leaper_trajectory_chance_20261024/history-barrier-chance.json'))
    assert verify(load(PACKET),cert)['verified']
    assert cert['policies'][0]['blocked']
    cert['policies'][0]['blocked']=[]
    with pytest.raises(ValueError,match='actual count3'):verify(load(PACKET),cert)

@pytest.mark.parametrize('fault',['probability','defender_denominator','history','clock','rank'])
def test_false_chance_lower_is_rejected(fault):
    cert=copy.deepcopy(load(CERT));policy=cert['policies'][0]
    if fault=='probability':policy['vertices'][0]['numerator']=str(int(policy['vertices'][0]['numerator'])+1)
    elif fault=='defender_denominator':
        row=next(r for r in policy['vertices']if len(r['selected_action_indices'])>1)
        row['selected_action_indices']=row['selected_action_indices'][:-1]
        row['positive_action_indices']=[k for k in row['positive_action_indices']if k in row['selected_action_indices']]
    elif fault=='history':policy['root_state_sha']='0'*64
    elif fault=='clock':policy['remaining']-=1
    else:policy['vertices'][0]['distance']+=1
    with pytest.raises(ValueError):verify(load(PACKET),cert)
