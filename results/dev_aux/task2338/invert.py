"""Invert a saved semantic WIN strategy into scoped opponent NO_FORCED_WIN."""
from pathlib import Path
from dataclasses import replace
from copy import copy
import json,time
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import execute
from results.dev_aux.task2205.consume import decode_graph
from results.dev_aux.task2199.semantic_graph import verify_graph
from results.dev_aux.task2320.refutation import RefutationCertificate,RefutationNode,verify_no_forced_win,RefutationCursor
from results.dev_aux.task2320.build import encode
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2338')
def sha(p):return __import__('hashlib').sha256(Path(p).read_bytes()).hexdigest()
def run():
 p=json.loads((OUT/'plan.json').read_text());assert not(OUT/'result.json').exists()
 for n,h in p['pins'].items():assert sha(n)==h
 stop=EvidenceStopReader(Path.cwd());start=time.perf_counter()
 def cancel():stop();return time.perf_counter()-start>=p['cap_seconds']
 f=Path('results/dev_aux/task2315');data=json.loads((f/'result.json').read_text());saved=json.loads((f/'certificates.json').read_text());c=compile_ruleset_for_execution(deserialize_ruleset((f/'rules.json').read_text()));row=next(r for r in data['rows']if r['setup']is None);other=next(r for r in data['rows']if r['setup']=='swapped_bases');s=GameSession.replay(c,deserialize_game_record(json.dumps(row['root_record'])));first=GameSession.replay(c,deserialize_game_record(json.dumps(row['prefixes'][0]['record'])));assert dict(first.state.position.aux_state)[(0,-1)]==1 and dict(s.state.position.aux_state)[(0,-1)]==0;pc=s.state.position.board[8];assert(pc.base_type_id,pc.current_type_id,pc.promoted)==('P','R',True)and s.state.position.hands[0].count('R')==1
 positive=decode_graph(s,saved[0]['certificate']);pv=verify_graph(s,positive,seconds=5.,cancel=cancel);assert pv['verified'];negative=RefutationCertificate(c.ruleset_fingerprint,s.to_record(),s.state,1-positive.target,tuple(RefutationNode(n.edges)for n in positive.nodes));v=verify_no_forced_win(s,negative,seconds=5.,cancel=cancel);assert v['verified'],v;root=s.to_record();cur=RefutationCursor(s,negative,seconds=5.,cancel=cancel);ch=cur.choose(s);assert ch.action.base_type_id=='R'and ch.action.pattern_id.startswith('sem_');before=copy(s);execute(s,ch);cur.observe(before,ch,s);assert s.result.status is not SessionStatus.ONGOING and s.result.winner==positive.target and json.loads(serialize_game_record(s.to_record()))==row['actual_record']
 wrong=GameSession.replay(c,deserialize_game_record(json.dumps(other['root_record'])));assert wrong.state.position.hands[0].count('P')==1;root_session=GameSession.replay(c,root);stale=verify_no_forced_win(wrong,negative,seconds=5.,cancel=cancel);rebound=replace(negative,root_record=wrong.to_record(),root_state=wrong.state);wrongbase=verify_no_forced_win(wrong,rebound,seconds=5.,cancel=cancel);badtarget=verify_no_forced_win(root_session,replace(negative,target=positive.target),seconds=5.,cancel=cancel);terminal=verify_no_forced_win(s,replace(negative,root_record=s.to_record(),root_state=s.state),seconds=5.,cancel=cancel);assert all(not r['verified']for r in(stale,wrongbase,badtarget,terminal))
 result=dict(status='PASS_SAVED_COMPOSITE_SEMANTIC_POSITIVE_TO_NEGATIVE_INVERSION',positive=pv,negative=v,actual_semantic_drop_plies=1,actual_winner=s.result.winner,negative_target=negative.target,real_aux_history=[1,0],base_current=['P','R'],other_context='UNKNOWN; savedRdropnegativewitnessrejected, notLOSS/DRAW',controls=dict(stale_root=stale,wrong_base_hand_rebound=wrongbase,wrong_quantifier_target=badtarget,actual_terminal_root=terminal),root_record=json.loads(serialize_game_record(root)),actual_record=json.loads(serialize_game_record(s.to_record())),negative_certificate=encode(negative),seconds=time.perf_counter()-start,scope=p['scope'])
 with(OUT/'result.json').open('x')as f:json.dump(result,f,indent=2)
 print(json.dumps({k:result[k]for k in('status','actual_semantic_drop_plies','actual_winner','negative_target','seconds')}))
if __name__=='__main__':run()
