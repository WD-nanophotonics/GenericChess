"""Actual closed-cycle safety, counterexample and fail-closed controls."""
from pathlib import Path
from dataclasses import replace
from copy import copy
import sys,pytest
sys.path.insert(0,str(Path('tests').resolve()))
from conftest import king_type,make_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import SessionChoice,execute
from results.dev_aux.task2320.refutation import *
from results.dev_aux.task2320.build import discover,encode,decode

@pytest.fixture
def sample():
 rs=replace(make_ruleset(3,[king_type()],lines=['K..','...','..k']),max_ply=24,repetition_limit=3)
 s=GameSession(compile_ruleset_for_execution(rs));d=discover(s,max_nodes=1000,seconds=5.);assert d['certificate']is not None;return s,d['certificate']

def test_actual_closed_cycle_refutation_and_four_rollouts(sample):
 s,cert=sample;v,pos=verify_no_forced_win(s,cert,seconds=5.,return_positions=True);assert v['verified']and v['claim']=='NO_FORCED_WIN'and len(pos)>1
 assert verify_no_forced_win(s,decode(s,encode(cert)),seconds=5.)['verified']
 for seed in range(4):
  actual=copy(s);cur=RefutationCursor(actual,cert,seconds=5.);steps=0
  while actual.result.status is SessionStatus.ONGOING:
   before=copy(actual)
   if actual.state.position.side_to_move==cert.target:
    legal=actual.legal_actions();ch=SessionChoice('ACTION',action=legal[(steps+seed)%len(legal)])
   else:ch=cur.choose(actual)
   execute(actual,ch);cur.observe(before,ch,actual);steps+=1
  assert actual.result.winner!=cert.target and steps<=24 and not cur.active

def test_missing_target_move_is_not_refutation(sample):
 s,c=sample;nodes=list(c.nodes);assert s.state.position.side_to_move==c.target and len(nodes[0].edges)>1;nodes[0]=replace(nodes[0],edges=nodes[0].edges[1:]);v=verify_no_forced_win(s,replace(c,nodes=tuple(nodes)));assert not v['verified']and v['reason']=='missing_target_action'

def test_inconsistent_self_merge_rejected(sample):
 s,c=sample;nodes=list(c.nodes);nodes[0]=replace(nodes[0],edges=tuple((ch,0)for ch,j in nodes[0].edges));v=verify_no_forced_win(s,replace(c,nodes=tuple(nodes)));assert not v['verified']and v['reason']=='inconsistent_full_position_merge'

def test_stale_history_binding_rejected(sample):
 s,c=sample;after=copy(s);after.submit(after.legal_actions()[0]);v=verify_no_forced_win(after,c);assert not v['verified']and v['reason']=='root_binding'

def test_wrong_rule_target_and_empty_graph_rejected(sample):
 s,c=sample
 for bad in(replace(c,ruleset_fingerprint='bad'),replace(c,target=True),replace(c,nodes=())):assert not verify_no_forced_win(s,bad)['verified']

def test_incomplete_budget_is_unknown_not_draw(sample):
 s,c=sample
 for kw in(dict(max_nodes=0),dict(seconds=0.),dict(cancel=lambda:True)):
  r=verify_no_forced_win(s,c,**kw);assert not r['verified']and r['claim']=='UNKNOWN'
 with pytest.raises(ValueError):RefutationCursor(s,c,max_nodes=0)

def test_discovery_does_not_turn_incomplete_graph_into_negative(sample):
 s,c=sample;d=discover(s,max_nodes=1,seconds=1.);assert d['certificate']is None and not d['closed']

def test_unsupported_perpetual_history_rejected(sample):
 s,c=sample;wrong=GameSession(replace(s.compiled,repetition_policy='perpetual_check_loses'));bad=replace(c,root_state=wrong.state,root_record=wrong.to_record())
 assert not verify_no_forced_win(wrong,bad)['verified']


def test_borrowed_boundary_DRAW_cannot_omit_actual_mating_action():
 from results.dev_aux.task2200.controls import mate_rules
 rs=replace(mate_rules(),max_ply=1);s=GameSession(compile_ruleset_for_execution(rs),initial_setup_key='quiet_mate')
 # No certificate terminal label or synthetic deadline history is accepted.
 # An empty-node alleged DRAW must face actual Position legal closure.
 fake=RefutationCertificate(s.compiled.ruleset_fingerprint,s.to_record(),s.state,0,(RefutationNode(()),));bad=verify_no_forced_win(s,fake,seconds=3.);assert not bad['verified']and bad['reason']=='missing_target_action'
 legal=list(s.legal_actions());mate=[]
 for a in legal:
  child=copy(s);child.submit(a)
  if child.result.status is not SessionStatus.ONGOING and child.result.winner==0:mate.append(a)
 assert mate
 actual=copy(s);actual.submit(mate[0]);assert actual.state.ply_count==1 and actual.result.winner==0
 # Preserve ALLrootmoves, put the target-WIN child first; it cannot be accepted
 # as DRAW merely because the actual winning action also reaches max_ply.
 ordered=[mate[0]]+[a for a in legal if a!=mate[0]];nodes=(RefutationNode(tuple((SessionChoice('ACTION',action=a),i+1)for i,a in enumerate(ordered))),)+tuple(RefutationNode(())for a in ordered)
 bad=verify_no_forced_win(s,replace(fake,nodes=nodes),seconds=3.);assert not bad['verified']and bad['reason']=='target_WIN_leaf'


def test_real_same_Position_new_history_rebind_and_third_repeat(sample):
 root,cert=sample;actual=copy(root)
 loop=[((0,2),(0,1)),((2,0),(2,1)),((0,1),(0,2)),((2,1),(2,0))]
 def four():
  for src,dst in loop:
   a,=[a for a in actual.legal_actions()if(a.from_square.file,a.from_square.rank)==src and(a.to_square.file,a.to_square.rank)==dst];actual.submit(a)
 four();assert actual.state.position==root.state.position and actual.result.status is SessionStatus.ONGOING
 assert not verify_no_forced_win(actual,cert)['verified']
 rebound=replace(cert,root_record=actual.to_record(),root_state=actual.state);v=verify_no_forced_win(actual,rebound,seconds=5.);assert v['verified']and v['claim']=='NO_FORCED_WIN'
 # Current actual history eventually draws, but is not used to close graph nodes.
 four();assert actual.state.position==root.state.position and actual.result.status is not SessionStatus.ONGOING and actual.result.winner is None
 bad=verify_no_forced_win(actual,replace(cert,root_record=actual.to_record(),root_state=actual.state));assert not bad['verified']and bad['reason']=='actual_root_terminal'


def test_actual_automatic_rule_is_outside_finite_ply_contract(sample):
 from generic_chess.rules.schema import RuleAutomaticAdjudication
 root,cert=sample
 rs=replace(make_ruleset(3,[king_type()],lines=['K..','...','..k']),max_ply=24,repetition_limit=3,automatic_adjudications=(RuleAutomaticAdjudication('opaque_cutoff',4),))
 actual=GameSession(compile_ruleset_for_execution(rs));bound=replace(cert,ruleset_fingerprint=actual.compiled.ruleset_fingerprint,root_record=actual.to_record(),root_state=actual.state)
 bad=verify_no_forced_win(actual,bound,seconds=3.);assert not bad['verified']and bad['reason']=='unsupported_history_adjudication'


def test_actual_foe_deviation_is_not_a_global_negative_skip(sample):
 actual,cert=sample;actual=copy(actual);cur=RefutationCursor(actual,cert,seconds=5.)
 for src,dst in(((0,2),(0,1)),((2,0),(2,1)),((0,1),(0,0))):
  before=copy(actual);a,=[a for a in actual.legal_actions()if(a.from_square.file,a.from_square.rank)==src and(a.to_square.file,a.to_square.rank)==dst];choice=SessionChoice('ACTION',action=a)
  if actual.state.position.side_to_move!=cert.target:assert cur.choose(actual)==choice
  execute(actual,choice);cur.observe(before,choice,actual)
 prescribed=cur.choose(actual);alternative=next(a for a in actual.legal_actions()if a!=prescribed.action);before=copy(actual);choice=SessionChoice('ACTION',action=alternative);execute(actual,choice)
 with pytest.raises(ValueError,match='outside_refutation'):cur.observe(before,choice,actual)
