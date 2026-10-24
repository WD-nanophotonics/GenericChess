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

def test_first_action_intervention_requires_registration_and_keeps_query_pv(world):
 from scripts.leaper_two_type_forward import player
 from scripts.leaper_two_type_qualify import qualify_game
 c=L.compile_rule(L.ruleset_from_dict(world['rule']));s=L.GameSession(c)
 d=player(c,1000).choose_action(s,L.SearchLimits(max_depth=1,max_nodes=64,max_time_seconds=1,quiescence_max_depth=0,quiescence_hard_max_depth=8))
 alternative=next(a for a in s.legal_actions() if a!=d.action)
 q=dict(actor=0,root_ply=0,state_sha256=L.state_sha(s.state),legal_count=len(s.legal_actions()),decision=L.record_value(d),action=L.record_value(d.action),executed_action=L.record_value(alternative),seconds=0)
 s.submit(alternative)
 row=dict(status='CLOSED',slot=dict(root=0,policy='UNIT'),nodes_limit=64,initial_record=world['roots'][0]['record'],queries=[q],final_record=L.record_value(s.to_record()),final_state=L.record_value(s.state),terminal=L.record_value(s.result),censor='whole_cap',value=None,seconds=1)
 with pytest.raises(AssertionError,match='unregistered executed-action'):
  qualify_game(world,row,dict(nodes=64))
 result=qualify_game(world,row,dict(nodes=64,first_action_override=L.record_value(alternative)))
 assert result['value'] is None and q['decision']['action']==q['action']!=q['executed_action']

def test_prospective_sampler_preserves_complete_named_safe_inputs(world,tmp_path):
 from scripts.leaper_fresh_mu import prepare as prepare_mu
 from generic_chess.core.attacks import anchor_square,pseudo_attacks
 source=tmp_path/'source.json';L.write_record(source,world)
 target=tmp_path/'fresh.json';regpath=tmp_path/'registration.json'
 prepare_mu(source,target,regpath,count=2,seed=202610240951)
 fresh=L.load(target);c=L.compile_rule(L.ruleset_from_dict(fresh['rule']))
 assert len(fresh['roots'])==2
 for root in fresh['roots']:
  s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(root['record'])))
  assert L.record_value(s.state)==root['state'] and not s.state.terminal_status.is_terminal
  assert CounterPieces(s.state)=={(0,'K'):1,(0,'A'):1,(0,'B'):1,(1,'K'):1,(1,'A'):1,(1,'B'):1}
  assert not any(anchor_square(s.state.position,side,c) in pseudo_attacks(s.state.position,1-side,c)for side in (0,1))
 assert fresh['roots'][1]['record']['initial_setup_key']=='fresh1'
 assert fresh['fingerprint']!=world['fingerprint']


def test_sampler_never_swallows_unrelated_rule_validation(world,tmp_path,monkeypatch):
 from scripts.leaper_fresh_mu import prepare as prepare_mu
 from generic_chess.rules.validation import RuleValidationError,ValidationIssue
 source=tmp_path/'source.json';L.write_record(source,world)
 def bad_compile(rule):raise RuleValidationError([ValidationIssue('UNSUPPORTED_CONTRACT','piece_types','must not become a rejection-sampling exclusion')])
 monkeypatch.setattr(L,'compile_rule',bad_compile)
 with pytest.raises(RuleValidationError,match='UNSUPPORTED_CONTRACT'):
  prepare_mu(source,tmp_path/'fresh.json',tmp_path/'registration.json',count=2)
 assert not (tmp_path/'fresh.json').exists()

@pytest.mark.parametrize('controller',['UNIT','DEFAULT'])
def test_future_writer_labels_actual_controller_and_separates_generated_profile(world,tmp_path,monkeypatch,controller):
 from scripts import leaper_default_contact as writer
 c=L.compile_rule(L.ruleset_from_dict(world['rule']))
 profile=L.record_value(L.AlphaBetaPlayer(c,use_disk_cache=False).evaluation_profile)
 source=tmp_path/'input.json';L.write_record(source,world)
 reg=dict(input_sha256=L.sha(source),source_sha256=L.sha(Path(writer.__file__)),expected_total_seconds=1,controller=controller,root=0,profile=profile,nodes=64,cap_seconds=0)
 regpath=tmp_path/'reg.json';L.write_record(regpath,reg)
 def no_queries(*args,**kwargs):raise AssertionError('metadata fixture must not issue Player queries')
 monkeypatch.setattr(L.AlphaBetaPlayer,'choose_action',no_queries)
 row=writer.run(source,regpath,tmp_path/'closed.json')
 assert row['slot']['policy']==row['controller']==controller
 assert 'profile'not in row and row['generated_default_profile']==profile
 assert row['actual_leaf_profile']['board_value_by_type']==({'K':0,'A':1000,'B':1000}if controller=='UNIT'else profile['board_value_by_type'])
 assert row['actual_leaf_config']['dynamic_mobility_weight']==(0 if controller=='UNIT'else 2)
 assert row['ordering_profile']['board_value_by_type']==row['actual_leaf_profile']['board_value_by_type']
 assert row['queries']==[] and row['censor']=='whole_cap' and row['value']is None


def test_pinned_legacy_label_erratum_cannot_accept_new_or_corrupted_mismatch():
 from scripts.leaper_default_contact_packet import validate_controller_labels
 reg=dict(controller='UNIT',root=0,source_sha256='df7b67719cd01267d3e39a6c1f53d571b8dc1c012fc6ae2b2f891f5fe7201822')
 row=dict(controller='UNIT',slot=dict(root=0,policy='DEFAULT'),queries=[dict(actor=0,controller='UNIT'),dict(actor=1,controller='UNIT')])
 assert validate_controller_labels(row,reg)['actual_controller']=='UNIT'
 wrong=copy.deepcopy(reg);wrong['source_sha256']='0'*64
 with pytest.raises(AssertionError,match='unrecognized controller-label'):
  validate_controller_labels(row,wrong)
 wrong=copy.deepcopy(row);wrong['slot']['policy']='STATIC_FIXED'
 with pytest.raises(AssertionError,match='unrecognized controller-label'):
  validate_controller_labels(wrong,reg)
 wrong=copy.deepcopy(row);wrong['queries'][0]['controller']='DEFAULT'
 with pytest.raises(AssertionError):validate_controller_labels(wrong,reg)
