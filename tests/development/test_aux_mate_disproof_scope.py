"""Actual Core LOSS/DRAW certificates share no-forced-WIN, not WDL identity."""
from pathlib import Path
import gzip,json
from copy import deepcopy
import pytest
from scripts.leaper_truth_compatibility import bind_context,verify_bound_tree
P=Path(__file__).parents[1]/'fixtures'/'mate_disproof_not_draw.json.gz'
@pytest.fixture(scope='module')
def facts():return json.loads(gzip.decompress(P.read_bytes()))
def test_actual_loss_is_verified_for_named_attacker(facts):
 f=facts['loss'];c=bind_context(f['rule'],f['record']);p=verify_bound_tree(c,f['upper_nodes'],-1,direction='upper',value_seat=f['value_seat']);assert p['wdl_bounds']==[-1,-1] and p['counts']['edges']==2
 assert c.session.state.ply_count==15 and not c.session.state.terminal_status.is_terminal
def test_actual_draw_has_both_independent_directions(facts):
 f=facts['draw'];c=bind_context(f['rule'],f['record']);lo=verify_bound_tree(c,f['lower_nodes'],0,direction='lower',value_seat=f['value_seat']);hi=verify_bound_tree(c,f['upper_nodes'],0,direction='upper',value_seat=f['value_seat']);assert lo['wdl_bounds']==[0,1] and hi['wdl_bounds']==[-1,0]
 assert c.session.state.ply_count==127 and len(c.session.legal_actions())==18
@pytest.mark.parametrize('change',['wrong_attacker','different_history','unknown_leaf_with_disproof_flag'])
def test_different_context_or_reported_disproof_never_supplies_truth(facts,change):
 f=deepcopy(facts['loss']);seat=f['value_seat']
 if change=='wrong_attacker':seat=1-seat
 if change=='different_history':f['record']['actions'].pop()
 if change=='unknown_leaf_with_disproof_flag':
  root=next(n for n in f['upper_nodes'] if n['state']['ply_count']==15);f['upper_nodes']=[dict(state=root['state'],children=[],proof_number=1,disproof_number=0,reported_mate_disproof=True)]
 c=bind_context(f['rule'],f['record'])
 with pytest.raises(ValueError):verify_bound_tree(c,f['upper_nodes'],-1,direction='upper',value_seat=seat)
