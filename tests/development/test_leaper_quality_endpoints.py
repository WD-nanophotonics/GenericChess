"""Identity and finite-geometry controls for the source-only endpoint reader."""
from copy import deepcopy
from scripts.qualify_leaper_quality_endpoints import action,geometry

def rule():
 return dict(board_size=4,piece_types=[dict(type_id='K',is_anchor=True,movement_atoms=[dict(kind='leap',offset=[1,0]),dict(kind='leap',offset=[0,1])]),dict(type_id='A',is_anchor=False,movement_atoms=[dict(kind='leap',offset=[2,1])])],initial_position=[[dict(current_type_id='K',owner=0),dict(current_type_id='A',owner=0),None,None],[None]*4,[None]*4,[dict(current_type_id='A',owner=1),dict(current_type_id='K',owner=1),None,None]])

def test_geometry_canonicalization_keeps_joint_orientation_and_roster():
 r=rule();rot=deepcopy(r)
 for t in rot['piece_types']:
  for a in t['movement_atoms']:x,y=a['offset'];a['offset']=[-y,x]
 assert geometry(r)==geometry(rot)
 # Reflecting only one movement type is not a joint board symmetry.
 rot=deepcopy(r);rot['piece_types'][1]['movement_atoms'][0]['offset']=[-2,1]
 assert geometry(r)!=geometry(rot)
 changed=deepcopy(r);changed['initial_position'][0][1]=None
 assert geometry(r)!=geometry(changed)

def test_only_finite_incidence_and_type_names_are_normalized():
 r=rule();q=deepcopy(r)
 q['piece_types'][1]['type_id']='OTHER'
 for row in q['initial_position']:
  for p in row:
   if p and p['current_type_id']=='A':p['current_type_id']='OTHER'
 q['piece_types'][1]['movement_atoms'].append(dict(kind='leap',offset=[9,8]))
 assert geometry(r)==geometry(q)
 q['max_ply']=128;r['max_ply']=6
 assert geometry(r)==geometry(q) # Descriptor deliberately does not equate clocks.

def test_full_action_identity_survives_wire_normalization():
 a=dict(actor_type_id='A',pattern_id='p1',geometry_id='g2',promotion_target_id=None,from_square=dict(file=1,rank=2),to_square=dict(file=3,rank=0))
 b=action(a);assert b['from']==[1,2] and b['to']==[3,0]
 assert action(b)==b
 changed=dict(a,pattern_id='p2');assert action(changed)!=b
 changed=dict(a,geometry_id='g3');assert action(changed)!=b


def test_unfinished_with_no_winner_is_not_a_draw_and_known_win_keeps_perspective():
 from scripts.qualify_leaper_quality_endpoints import dense_bounds
 rows=[dict(game_id=0,status='TERMINAL',long_seat=1,Core_terminal=dict(status='checkmate',winner=1)),dict(game_id=1,status='UNFINISHED',long_seat=0,Core_terminal=dict(status='ongoing',winner=None))]
 b=dense_bounds(rows)
 assert b==dict(signed_mean_bounds=[0.0,1.0],positive_family_bounds=[0,1],completions=3,unknown=[1])
