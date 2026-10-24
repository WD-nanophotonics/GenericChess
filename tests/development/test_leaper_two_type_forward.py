"""Observed prospective-input and complete relative-price boundary contracts."""
from dataclasses import replace
import copy,json
from pathlib import Path
import pytest
from scripts import leaper_design as L
from scripts.leaper_two_type_forward import prepare,profiles,RATIOS

@pytest.fixture
def world(tmp_path):return prepare(tmp_path/'input.json')

def test_four_complete_named_roots_share_rule_but_preserve_history_identity(world):
 c=L.compile_rule(L.ruleset_from_dict(world['rule']))
 assert len(world['roots'])==4 and len(RATIOS)==7
 assert len({r['state_sha256']for r in world['roots']})==4
 for r in world['roots']:
  s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(r['record'])))
  assert L.record_value(s.state)==r['state'] and s.state.ply_count==0
  assert CounterPieces(s.state)=={(0,'K'):1,(0,'A'):1,(0,'B'):1,(1,'K'):1,(1,'A'):1,(1,'B'):1}
  assert not s.state.terminal_status.is_terminal

def CounterPieces(state):
 from collections import Counter
 return dict(Counter((p.owner,p.current_type_id)for p in state.position.board if p))

def test_leaf_relative_price_changes_but_ordering_stays_unit(world):
 c=L.compile_rule(L.ruleset_from_dict(world['rule']));s=L.GameSession(c)
 # Remove one B from a copied state to create an explicit leaf feature delta;
 # this evaluator-only control makes no reachable-history claim.
 board=list(s.state.position.board);i=next(i for i,p in enumerate(board)if p and p.owner==1 and p.current_type_id=='B');board[i]=None
 state=replace(s.state,position=replace(s.state.position,board=tuple(board)))
 for b in RATIOS.values():
  e,p,cfg=profiles(c,b)
  assert e.type_value('B')==1000 and e.type_value('A')==1000
  assert e.evaluate(state)==b
  assert p['board_value_by_type']=={'K':0,'A':1000,'B':b}
  assert cfg['dynamic_mobility_weight']==cfg['anchor_escape_weight']==0

def test_named_setup_cannot_be_replaced_by_fresh_default(world):
 c=L.compile_rule(L.ruleset_from_dict(world['rule']));r=world['roots'][1]['record'];named=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(r)))
 assert named.state!=L.GameSession(c).state
 bad=copy.deepcopy(r);bad['initial_setup_key']='not-declared'
 with pytest.raises(Exception):L.GameSession.replay(c,L.deserialize_game_record(json.dumps(bad)))


def test_censored_transcript_remains_unknown_and_corruption_is_rejected(world):
 from scripts.leaper_two_type_forward import player
 from scripts.leaper_two_type_qualify import qualify_game
 c=L.compile_rule(L.ruleset_from_dict(world['rule']));ss=L.GameSession(c);p=player(c,1000)
 d=p.choose_action(ss,L.SearchLimits(max_depth=1,max_nodes=64,max_time_seconds=1,quiescence_max_depth=0,quiescence_hard_max_depth=8))
 q=dict(actor=0,root_ply=0,state_sha256=L.state_sha(ss.state),legal_count=len(ss.legal_actions()),decision=L.record_value(d),action=L.record_value(d.action),seconds=0)
 ss.submit(d.action)
 row=dict(status='CLOSED',slot=dict(root=0,policy='B1000',seed=0),nodes_limit=64,initial_record=world['roots'][0]['record'],queries=[q],final_record=L.record_value(ss.to_record()),final_state=L.record_value(ss.state),terminal=L.record_value(ss.result),censor='whole_cap',value=None,seconds=1)
 result=qualify_game(world,row,dict(nodes=64));assert result['value']is None and result['plies']==1
 wrong=copy.deepcopy(row);wrong['value']=0
 with pytest.raises(AssertionError):qualify_game(world,wrong,dict(nodes=64))
 wrong=copy.deepcopy(row);wrong['queries'][0]['state_sha256']='0'*64
 with pytest.raises(AssertionError):qualify_game(world,wrong,dict(nodes=64))


def test_declared_profile_must_match_actual_constructor(world):
 from scripts.leaper_two_type_qualify import analyze
 wrong=copy.deepcopy(world);wrong['profiles']['B500'][0]['board_value_by_type']['B']=501
 with pytest.raises(AssertionError,match='declared complete profiles'):
  analyze(wrong,dict(slots=[]),dict(slots=[],missing=[]),lambda i:None)
