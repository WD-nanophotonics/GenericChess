"""Independent full-record, proof-cursor, phase and frozen-factor audit."""
from pathlib import Path
from collections import defaultdict,Counter
from copy import copy
import json,time,hashlib,sys
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import SessionChoice,execute
from results.dev_aux.task2205.consume import decode_graph
from results.dev_aux.task2199.semantic_graph import verify_graph,GraphStrategyCursor
from results.dev_aux.task2175.receipt import choice_value
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2317')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(task=2313):
 t=time.perf_counter();stop=EvidenceStopReader(Path.cwd());folder=Path(f'results/dev_aux/task{task}');read=lambda p:json.loads(Path(p).read_text());p=read(folder/'plan.json');done=read(folder/'completion.json');slots=read(folder/'slots.json');roots={r['index']:r for r in read(p['input'])};games=list(map(json.loads,(folder/'games.jsonl').read_text().splitlines()));ds=list(map(json.loads,(folder/'decisions.jsonl').read_text().splitlines()));certs=list(map(json.loads,(folder/'certificates.jsonl').read_text().splitlines()));arm='LOW_ONLY_INCREMENTAL'if task==2313 else'TWO_REGIME_INCREMENTAL';budget=60. if task==2313 else 8.;proof=42. if task==2313 else 5.6;verification=15. if task==2313 else 2.
 assert task in(2313,2316);assert len(slots)==32 and p['expected_games']==32 and len(games)==done['games']and len(ds)==done['decisions']and len(certs)==done['certificates'];assert done['missing']==32-len(games);assert done['status']!='COMPLETE'or len(games)==32
 assert sha(p['input'])==p['input_sha']and sha(folder/'slots.json')==p['slots_sha']
 for name,h in p['pins'].items():assert sha(name)==h
 baseline=read('results/dev_aux/task2307/plan.json');base_slots=read('results/dev_aux/task2307/slots.json');assert p['opponents']==baseline['opponents']and p['H']==baseline['H']==96 and p['step_seconds']==baseline['step_seconds']==1.5;assert Path(p['input']).read_bytes()==Path(baseline['input']).read_bytes()
 assert all(p['candidate'][k]==baseline['candidate'][k]for k in baseline['candidate']if k not in('proof_seconds','verification_seconds'));assert p['candidate']['proof_seconds']==proof and p['candidate']['verification_seconds']==verification and p['candidate_proof_caller_seconds']==budget
 assert all({k:v for k,v in a.items()if k!='arm'}=={k:v for k,v in b.items()if k!='arm'}and a['arm']==arm for a,b in zip(slots,base_slots))
 by=defaultdict(list)
 for d in ds:by[d['slot']].append(d)
 moves=0;depths=Counter();sources=Counter();attempts=Counter();material_before_proof=[];pending=[];proofs=[]
 def cancel():stop();return time.perf_counter()-t>300
 for g,slot in zip(games,slots):
  assert all(g[k]==v for k,v in slot.items());r=roots[g['root']];c=compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(r['record'])));prefix=s.to_record().actions;final=deserialize_game_record(json.dumps(g['record']));assert final.actions[:len(prefix)]==prefix;actions=final.actions[len(prefix):];mm=by[g['slot']];assert len(actions)==g['plies']and len(mm)in(len(actions),len(actions)+1);attempted=set();cursor_bound=False;own_material=0
  for i,(a,d)in enumerate(zip(actions,mm)):
   if cancel():raise TimeoutError('consumer_cap')
   assert d['ply']==i and d['side']==s.state.position.side_to_move and d['is_candidate']==(d['side']==g['candidate_color']);assert d['root_record']==json.loads(serialize_game_record(s.to_record()))and d['root_state_sha']==hashlib.sha256(repr(s.state).encode()).hexdigest();assert d['choice']==choice_value(SessionChoice('ACTION',action=a));assert d['normal_visits']<=8192 and d['graph_positions']<=(65536 if d['is_candidate']else 8192)
   actors=sum(x is not None for x in s.state.position.board)+sum(n for h in s.state.position.hands for _,n in h.counts);regime='LOW'if actors<=4 else'HIGH';assert d['regime']==regime;limits=dict(d['phase_limits']);assert limits['normal_seconds']==1. and limits['total_seconds']<=d['caller_seconds']
   if d['is_candidate']:
    fresh=(regime=='LOW'or task==2316)and regime not in attempted and not cursor_bound;assert d['new_proof_attempt']==fresh
    if fresh:attempted.add(regime);attempts[regime]+=1
    assert d['caller_seconds']==(budget if fresh else 1.5)and limits['proof_seconds_shared']==proof and limits['verification_seconds_shared']==verification
    if not fresh:assert d['proof_seconds']==0 and not d['raw_proofs']
    if d['source']=='FULL_SESSION_MATERIAL_SEARCH':own_material+=1
    if d['source']=='VERIFIED_GRAPH_STRATEGY':material_before_proof.append(dict(slot=g['slot'],ply=i,material_decisions_before=own_material));cursor_bound=True
   else:assert d['caller_seconds']==1.5 and limits['proof_seconds_shared']==.2 and limits['verification_seconds_shared']==.1 and not d['new_proof_attempt']
   if d['source']=='VERIFIED_GRAPH_STRATEGY':assert any(v[1]=='INDEPENDENT'and v[2]['verified']for v in d['verification_receipts'])and any(v[1]=='CURRENT_CURSOR'and v[2]['verified']for v in d['verification_receipts'])
   if d['normal_receipt']is not None:depths[(d['is_candidate'],d['normal_receipt']['completed_depth'])]+=1
   sources[d['source']]+=1;execute(s,SessionChoice('ACTION',action=a));moves+=1
  if len(mm)>len(actions):
   d=mm[-1];assert d['ply']==len(actions)and d['root_record']==json.loads(serialize_game_record(s.to_record()));pending.append(dict(slot=g['slot'],uncommitted_decision=d['ply']))
  assert json.loads(serialize_game_record(s.to_record()))==g['record']and s.result.status.value==g['actual_status']and s.result.winner==g['winner'];reward=None if s.result.status is SessionStatus.ONGOING else 0 if s.result.winner is None else 1 if s.result.winner==g['candidate_color']else-1;assert reward==g['reward']and g['outcome']==('U'if reward is None else'D'if reward==0 else'W'if reward==1 else'L')
 for row in certs:
  g=next(g for g in games if g['slot']==row['slot']);r=roots[g['root']];c=compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(row['root_record'])));assert row['kind']=='GRAPH';cert=decode_graph(s,row['certificate']);v=verify_graph(s,cert,max_nodes=65536,seconds=5.,cancel=cancel);assert v['verified'];cur=GraphStrategyCursor(s,cert,max_nodes=65536,seconds=5.,cancel=cancel);n=0
  for a in deserialize_game_record(json.dumps(g['record'])).actions[len(s.to_record().actions):]:
   before=copy(s);ch=SessionChoice('ACTION',action=a)
   if s.state.position.side_to_move==row['side']:assert cur.choose(s)==ch
   execute(s,ch);cur.observe(before,ch,s);n+=1
  if g['outcome']!='U':assert s.result.status is not SessionStatus.ONGOING and s.result.winner==row['side']
  proofs.append(dict(slot=row['slot'],ply=row['ply'],verification=v,actual_cursor_plies=n,actual_terminal=g['outcome']!='U'))
 result=dict(status='PASS_FULL_ACTUAL_RECORDS_PHASES_CERTIFICATES_SINGLEAXIS_CONTRACT',task=task,games=len(games),expected=32,missing=32-len(games),actual_moves=moves,uncommitted=pending,outcomes=dict(Counter(g['outcome']for g in games)),attempts=dict(attempts),sources=dict(sources),normal_depths=[dict(is_candidate=k[0],depth=k[1],count=v)for k,v in depths.items()],material_before_proofs=material_before_proof,proofs=proofs,candidate_measured_seconds=sum(d['measured_seconds']for d in ds if d['is_candidate']),foe_measured_seconds=sum(d['measured_seconds']for d in ds if not d['is_candidate']),seconds=time.perf_counter()-t,scope='ALLclosed/partialactualrecords/sourcepins/slotorder/phasecost/LOWtriggerorinclusiveHIGHtrigger/fullgameoutcomes, independentlyreconstructed. Allsavedgraphcandidates andcurrentcursors replayed, U/missing notDRAW. Sameengine/verifier notexternalexecution; nofit/DEV/defaultadoption.')
 with(OUT/f'task{task}-audit.json').open('x')as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items()if k not in('proofs','material_before_proofs','normal_depths')}))
if __name__=='__main__':run(int(sys.argv[1])if len(sys.argv)>1 else 2313)
