"""Actual rule/cursor/commit safety and shared-budget regressions."""
from pathlib import Path
from dataclasses import replace,asdict
from copy import copy
import json,sys,pytest
sys.path.insert(0,str(Path('tests').resolve()));sys.path.insert(0,str(Path('tests/development').resolve()))
from test_generic_session_win_proof import session,claim
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from scripts.generic_session_proof_player import commit_session_decision
from scripts.generic_session_phase_player import PhaseLimits
from scripts.generic_session_win_proof import SessionChoice
from scripts.generic_win_proof import _same_state
from results.dev_aux.task2200.controls import mate_rules
from results.dev_aux.task2199.semantic_graph import prove_graph
from results.dev_aux.task2210.player import PaidGraphPhasePlayer

def make(s,**kwargs):
 return PaidGraphPhasePlayer(s.compiled,lambda p,t:0.,limits=PhaseLimits(
     proof_nodes=512,proof_seconds=.25,verification_nodes=8192,
     verification_seconds=.25,normal_seconds=.1),max_depth=1,**kwargs)
def mate():return GameSession(compile_ruleset_for_execution(mate_rules()),initial_setup_key='quiet_mate')
def commit(s,d,p):
 before=s.to_record();child=copy(s);commit_session_decision(child,d,[p])
 assert s.to_record()==before and _same_state(GameSession.replay(s.compiled,child.to_record()).state,child.state)
 return child

def test_real_S4_graph_proof_both_current_checks_and_actual_mate():
 s=mate();p=make(s);d=p.choose(s,max_nodes=64,seconds=1.)
 assert d.source=='VERIFIED_GRAPH_STRATEGY'and d.cursor_kind=='GRAPH'
 assert d.raw_proofs[0][1]=='CANDIDATE_WIN_GRAPH'
 assert [c[1]for c in d.verification_receipts]==['INDEPENDENT','CURRENT_CURSOR']
 assert all(c[2]['verified']for c in d.verification_receipts)
 assert d.graph_positions>0 and d.graph_verifier_visits>0 and d.proof_nodes==0
 with pytest.raises(AttributeError,match='mixed-unit'): _=d.nodes
 child=commit(s,d,p);assert child.result.winner==0 and p.cursor.certificate.nodes[p.cursor.index].rank==0

def test_unsupported_graph_declaration_routes_to_actual_fullhistory_proof():
 s=session(claim(0,'WIN'));p=make(s);d=p.choose(s,max_nodes=64,seconds=1.)
 assert d.raw_proofs[0]==('GRAPH','NOT_ADMITTED','unsupported_declarations')
 assert d.source=='VERIFIED_FULL_HISTORY_STRATEGY'and d.graph_positions==0
 assert d.proof_nodes>0 and d.tree_verifier_visits>0 and d.choice.kind=='DECLARATION'
 child=commit(s,d,p);assert child.result.status is SessionStatus.DECLARATION and child.result.winner==0 and not child.to_record().actions

def test_zero_proof_unknown_keeps_actual_normal_WIN_claim():
 s=session(claim(0,'WIN'));p=make(s);p.limits=replace(p.limits,proof_nodes=0);d=p.choose(s,max_nodes=64,seconds=1.)
 assert d.raw_proofs[-1][1]=='UNKNOWN'and d.source=='FULL_SESSION_MATERIAL_SEARCH'
 assert commit(s,d,p).result.winner==0

def test_restart_claim_is_typed_actual_restart_not_draw_proxy():
 s=session(claim(0,'RESTART'),k=0,b=15,r=2);p=make(s,proof_enabled=False)
 d=p.choose(s,max_nodes=64,seconds=1.);child=commit(s,d,p)
 assert d.choice==SessionChoice('DECLARATION',declaration_id='claim')
 assert child.result.declaration_outcome=='RESTART'and child.result.winner is None
 assert child.result.status is not SessionStatus.REPETITION

def test_forged_candidate_fails_validation_before_choice_or_cursor():
 s=mate();r=prove_graph(s,seconds=1.,max_nodes=512);assert r.certificate is not None
 p=make(s);p.graph_search=lambda *a,**k:replace(r,certificate=replace(r.certificate,target=1))
 d=p.choose(s,max_nodes=64,seconds=1.)
 assert not d.verification_receipts[0][2]['verified']
 assert d.source!='VERIFIED_GRAPH_STRATEGY'
 assert d.raw_proofs[0][1]=='CANDIDATE_WIN_GRAPH'
 # Full-history fallback may prove the same real win; forged graph was not used.
 child=commit(s,d,p);assert child.result.winner==0

def test_pulse_cancel_inside_provider_stays_latched_and_never_dispatches():
 s=mate();real=prove_graph(s,seconds=1.,max_nodes=512);p=make(s);calls=[0]
 def pulse():calls[0]+=1;return calls[0]==5
 def provider(*a,**kw):
  for _ in range(8):kw['cancel']()
  return real
 p.graph_search=provider;before=s.to_record();d=p.choose(s,max_nodes=64,seconds=1.,cancel=pulse)
 assert d.choice is None and d.exit_cause=='cancelled'and s.to_record()==before
 with pytest.raises(ValueError,match='no actionable'):commit_session_decision(s,d,[p])

def test_cancel_after_normal_returns_beats_precomputed_fallback():
 s=session();p=make(s,proof_enabled=False);flag=[False];real=p.normal.choose
 def stop(*a,**kw):out=real(*a,**kw);flag[0]=True;return out
 p.normal.choose=stop;d=p.choose(s,max_nodes=64,seconds=1.,cancel=lambda:flag[0])
 assert d.choice is None and d.exit_cause=='cancelled'

def test_zero_normal_clock_emits_only_paid_typed_fallback():
 s=mate();p=make(s,proof_enabled=False);p.limits=replace(p.limits,normal_seconds=0.)
 d=p.choose(s,max_nodes=64,seconds=1.)
 assert d.source=='PRECOMPUTED_TYPED_LEGAL_FALLBACK'and d.fallback_admission_seconds>0
 assert d.normal_receipt.choice is None and d.choice.action in s.legal_actions()
 commit(s,d,p)

def test_total_deadline_beats_graph_that_returns_late_and_normal_not_started():
 s=mate();real=prove_graph(s,seconds=1.,max_nodes=512);p=make(s);clock=[0.]
 def provider(*a,**kw):clock[0]=2.;return real
 p.graph_search=provider;d=p.choose(s,max_nodes=64,seconds=1.,_clock=lambda:clock[0])
 assert d.exit_cause=='time_budget'and d.normal_receipt is None
 assert d.source=='PRECOMPUTED_TYPED_LEGAL_FALLBACK'
 assert d.verification_receipts==()and p.cursor is None
 assert d.seconds==2. # Atomic provider overrun recorded, not hidden or called harddeadline.

def test_foreign_or_stale_root_never_commits():
 s=mate();foreign=session();p=make(foreign);d=p.choose(s,max_nodes=64,seconds=1.)
 assert d.choice is None and d.exit_cause=='unsupported_or_unreplayable_session'
 p=make(s);d=p.choose(s,max_nodes=64,seconds=1.);s.submit(s.legal_actions()[-1])
 with pytest.raises(ValueError,match='stale session'):commit_session_decision(s,d,[p])

def test_actual_graph_strategy_continuation_does_not_research(monkeypatch):
 from results.dev_aux.task2191.test_semantic_graph import semantic_mate
 s=semantic_mate();p=make(s);d=p.choose(s,max_nodes=64,seconds=1.)
 assert d.source=='VERIFIED_GRAPH_STRATEGY'
 # This fixture may have a one-ply certificate: terminal choose must not recurse.
 child=commit(s,d,p)
 if child.result.status is SessionStatus.ONGOING:
  assert child.state.position.side_to_move!=p.cursor.certificate.target
  node=p.cursor.certificate.nodes[p.cursor.index];choice=node.edges[0][0]
  before=copy(child);child.submit(choice.action);p.observe(before,choice,child)
  if child.result.status is SessionStatus.ONGOING:
   p.graph_search=lambda *a,**k:pytest.fail('continuation searched again')
   next_d=p.choose(child,max_nodes=64,seconds=1.,allow_new_proof=False)
   assert next_d.source=='VERIFIED_GRAPH_CONTINUATION'
 else:
  terminal=p.choose(child,max_nodes=64,seconds=1.);assert terminal.choice is None and terminal.source=='TERMINAL'

def test_normal_phase_cap_not_increased_by_unused_graph_time():
 s=mate();p=make(s,proof_enabled=False);d=p.choose(s,max_nodes=7,seconds=1.)
 limits=dict(d.phase_limits);assert limits['normal_nodes']==7 and limits['normal_seconds']==.1
 assert d.normal_receipt.nodes<=7 and d.normal_receipt.completed_depth in(0,1)
def test_real_three_ply_graph_cursor_continues_after_actual_defense():
 from results.dev_aux.task2187.trace import root_session
 from results.dev_aux.task2205.consume import decode_graph
 from results.dev_aux.task2179.graph import GraphResult
 roots={r['family']:r for r in json.loads(Path('results/dev_aux/task2177/inputs.json').read_text())['roots']}
 rows=(json.loads(l)for l in Path('results/dev_aux/task2204/certificates.jsonl').read_text().splitlines())
 item=next(r for r in rows if r['certificate']['nodes'][0]['rank']>=3 and r['certificate']['target']==0)
 s=root_session(roots[item['family']]);cert=decode_graph(s,item['certificate']);p=make(s)
 # Fixed existing serialized witness is prepaid fixture evidence, not new discovery.
 p.graph_search=lambda *a,**k:GraphResult('CANDIDATE_WIN_GRAPH',cert,'fixture_prepaid',len(cert.nodes),0,0,0.,cert.nodes[0].rank)
 d=p.choose(s,max_nodes=64,seconds=1.);assert d.source=='VERIFIED_GRAPH_STRATEGY'
 actual=commit(s,d,p);assert actual.result.status is SessionStatus.ONGOING
 node=p.cursor.certificate.nodes[p.cursor.index];choice=max(node.edges,key=lambda e:p.cursor.certificate.nodes[e[1]].rank)[0]
 before=copy(actual);actual.submit(choice.action);p.observe(before,choice,actual)
 assert actual.result.status is SessionStatus.ONGOING
 p.graph_search=lambda *a,**k:pytest.fail('existingcursor started new graph search')
 d=p.choose(actual,max_nodes=64,seconds=1.,allow_new_proof=False)
 assert d.source=='VERIFIED_GRAPH_CONTINUATION'and not d.raw_proofs and not d.verification_receipts
 assert d.admission_seconds>0 # Current full record admission remains paid.
 while actual.result.status is SessionStatus.ONGOING:
  if actual.state.position.side_to_move==cert.target:
   d=p.choose(actual,max_nodes=64,seconds=1.,allow_new_proof=False)
   assert d.source=='VERIFIED_GRAPH_CONTINUATION';actual=commit(actual,d,p)
  else:
   node=p.cursor.certificate.nodes[p.cursor.index];choice=max(node.edges,key=lambda e:p.cursor.certificate.nodes[e[1]].rank)[0]
   before=copy(actual);actual.submit(choice.action);p.observe(before,choice,actual)
 assert actual.result.winner==cert.target

def test_current_graph_rejection_retains_its_paid_work_receipt():
 from results.dev_aux.task2210.player import PaidCurrentGraphCursor
 from scripts.generic_win_proof import CertificateVerificationError
 s=mate();r=prove_graph(s,seconds=1.,max_nodes=512);bad=replace(r.certificate,target=1)
 with pytest.raises(CertificateVerificationError)as caught:PaidCurrentGraphCursor(s,bad,seconds=1.)
 assert caught.value.receipt['verified']is False and caught.value.receipt['nodes']>0
def test_actual_prehistory_candidate_rejected_before_graph_cursor_or_commit():
 from generic_chess.rules.serialization import deserialize_ruleset
 from generic_chess.session.serialization import deserialize_game_record
 from results.dev_aux.task2198.boundary import propose
 from results.dev_aux.task2068.teacher import CanonicalTeacher
 from results.dev_aux.task2179.graph import GraphResult
 data=json.loads(Path('results/dev_aux/task2198/result.json').read_text())['rows'][0]
 c=compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task2198/baseline-rules.json').read_text()))
 s=GameSession.replay(c,deserialize_game_record(json.dumps(data['root_record'])))
 teacher=CanonicalTeacher('results/dev_aux/task2171','results/dev_aux/task2172','results/dev_aux/task2176')
 target=json.loads(Path('results/dev_aux/task2101/result.json').read_text())['target']
 assert s.state.position.side_to_move==target and s.result.status is SessionStatus.ONGOING
 cert=propose(s,teacher,target,lambda:False);p=make(s)
 p.graph_search=lambda *a,**k:GraphResult('CANDIDATE_WIN_GRAPH',cert,'fixture_prepaid_actualhistory',len(cert.nodes),0,0,0.,cert.nodes[0].rank)
 # Restrict fallback tree tozero so graph rejection cannot be mistaken for a
 # successful graph choice or synthetic DRAW. Real normal action still allowed.
 p.limits=replace(p.limits,proof_nodes=0,verification_seconds=2.)
 d=p.choose(s,max_nodes=64,seconds=3.)
 assert d.verification_receipts[0][2]['reason']=='prehistory_repetition_guard'
 assert not d.verification_receipts[0][2]['verified']
 assert d.source not in('VERIFIED_GRAPH_STRATEGY','VERIFIED_GRAPH_CONTINUATION')and p.cursor is None
 assert s.result.status is SessionStatus.ONGOING and d.raw_proofs[-1][1]=='UNKNOWN'
