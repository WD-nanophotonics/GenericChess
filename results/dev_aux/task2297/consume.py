"""Closed fixed-foe 2x2 actual Session/certificate/resource audit."""
from pathlib import Path
from collections import defaultdict,Counter
from copy import copy
import json,time,hashlib,numpy as np
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import SessionChoice,SessionWinCertificate,SessionStrategyCursor,verify_session_certificate,execute
from results.dev_aux.task2205.consume import decode_graph
from results.dev_aux.task2048.portable_certificate import decode as decode_tree
from results.dev_aux.task2199.semantic_graph import verify_graph,GraphStrategyCursor
from results.dev_aux.task2175.receipt import choice_value
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2297')
def run():
 assert not (OUT/'result.json').exists(); start=time.perf_counter(); stop=EvidenceStopReader(Path.cwd()); folder=Path('results/dev_aux/task2289'); read=lambda p:json.loads(p.read_text(encoding='utf-8-sig')); p=read(folder/'plan.json'); done=read(folder/'completion.json'); roots={r['index']:r for r in read(Path(p['input']))}; slots=read(folder/'slots.json'); games=[json.loads(x) for x in (folder/'games.jsonl').read_text().splitlines()]; decisions=[json.loads(x) for x in (folder/'decisions.jsonl').read_text().splitlines()]; certificates=[json.loads(x) for x in (folder/'certificates.jsonl').read_text().splitlines()]; by=defaultdict(list)
 assert len(slots)==64 and len(games)<=64 and (done['status']!='COMPLETE' or len(games)==64) and len(decisions)==done['decisions'] and len(certificates)==done['certificates']; assert p['opponents']==[dict(ratio=2.,normal_nodes=8192,proof_nodes=8192,proof_seconds=.2,verification_nodes=16384,verification_seconds=.1,normal_seconds=1.)]
 for d in decisions:by[d['slot']].append(d)
 depths=Counter(); sources=Counter(); count=0; certificate_checks=[]
 def cancel():
  stop(); return time.perf_counter()-start>=240
 for g,slot in zip(games,slots):
  if cancel():raise TimeoutError('closed2x2consumer_cap')
  assert all(g[k]==v for k,v in slot.items()); root=roots[g['root']]; c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text())); s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record']))); prefix=s.to_record().actions; final=deserialize_game_record(json.dumps(g['record'])); assert final.actions[:len(prefix)]==prefix; actions=final.actions[len(prefix):]; mm=by[g['slot']]; assert len(actions)==g['plies']==len(mm);attempted=set();bound_cursor=False
  for i,(a,d) in enumerate(zip(actions,mm)):
   assert d['ply']==i and d['side']==s.state.position.side_to_move and d['is_candidate']==(d['side']==g['candidate_color']); assert d['root_record']==json.loads(serialize_game_record(s.to_record())) and d['root_state_sha']==hashlib.sha256(repr(s.state).encode()).hexdigest(); assert d['choice']==choice_value(SessionChoice('ACTION',action=a)); assert d['normal_visits']<=8192 and d['graph_positions']<=(65536 if d['is_candidate']else 8192)
   cfg=dict(d['phase_limits']);assert cfg['normal_seconds']==1. and cfg['total_seconds']<=d['caller_seconds']
   actors=sum(pc is not None for pc in s.state.position.board)+sum(n for h in s.state.position.hands for _,n in h.counts);regime='LOW'if actors<=4 else'HIGH';assert d['regime']==regime
   if d['is_candidate']:
    attempt=g['arm']=='TWO_REGIME_INCREMENTAL' and regime not in attempted and not bound_cursor;assert d['new_proof_attempt']==attempt
    if attempt:attempted.add(regime)
    assert d['caller_seconds']==(60. if attempt else 1.5)and cfg['proof_seconds_shared']==42. and cfg['verification_seconds_shared']==15.
    if not attempt:assert not d['raw_proofs'] and d['proof_seconds']==0
    if d['source']in('VERIFIED_GRAPH_STRATEGY','VERIFIED_FULL_HISTORY_STRATEGY'):bound_cursor=True
   else:assert not d['new_proof_attempt']and d['caller_seconds']==1.5 and cfg['proof_seconds_shared']==.2 and cfg['verification_seconds_shared']==.1
   if d['is_candidate'] and g['arm']=='MATERIAL_ONLY':assert not d['raw_proofs'] and d['proof_seconds']==d['verification_seconds']==0 and d['source'] not in ('VERIFIED_GRAPH_STRATEGY','VERIFIED_FULL_HISTORY_STRATEGY','VERIFIED_GRAPH_CONTINUATION','VERIFIED_FULL_HISTORY_CONTINUATION')
   if d['source'] in ('VERIFIED_GRAPH_STRATEGY','VERIFIED_FULL_HISTORY_STRATEGY'):assert any(v[1]=='INDEPENDENT' and v[2]['verified'] for v in d['verification_receipts']) and any(v[1]=='CURRENT_CURSOR' and v[2]['verified'] for v in d['verification_receipts'])
   if d['normal_receipt'] is not None:depths[(g['arm'],d['is_candidate'],d['normal_receipt']['completed_depth'])]+=1
   sources[d['source']]+=1; execute(s,SessionChoice('ACTION',action=a)); count+=1
  assert json.loads(serialize_game_record(s.to_record()))==g['record'] and s.result.status.value==g['actual_status'] and s.result.winner==g['winner']; reward=None if s.result.status is SessionStatus.ONGOING else 0 if s.result.winner is None else 1 if s.result.winner==g['candidate_color'] else -1; assert g['reward']==reward and g['outcome']==('U' if reward is None else 'D' if reward==0 else 'W' if reward==1 else 'L')
 for row in certificates:
  g=games[row['slot']]; root=roots[g['root']]; c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text())); s=GameSession.replay(c,deserialize_game_record(json.dumps(row['root_record']))); prefix=s.to_record().actions
  if row['kind']=='GRAPH':cert=decode_graph(s,row['certificate']); receipt=verify_graph(s,cert,max_nodes=65536,seconds=5.,cancel=cancel); assert receipt['verified']; cursor=GraphStrategyCursor(s,cert,max_nodes=65536,seconds=5.,cancel=cancel)
  else:
   cert=SessionWinCertificate(c.ruleset_fingerprint,s.to_record(),s.state,row['side'],decode_tree(row['certificate'],c.ruleset_fingerprint)); receipt=verify_session_certificate(s,cert,max_nodes=65536,seconds=5.,cancel=cancel); assert receipt['verified']; cursor=SessionStrategyCursor(s,cert,max_nodes=65536,seconds=5.,cancel=cancel)
  for a in deserialize_game_record(json.dumps(g['record'])).actions[len(prefix):]:
   before=copy(s); choice=SessionChoice('ACTION',action=a)
   if s.state.position.side_to_move==row['side']:assert cursor.choose(s)==choice
   execute(s,choice); cursor.observe(before,choice,s)
  assert s.result.status is not SessionStatus.ONGOING and s.result.winner==row['side']; certificate_checks.append(dict(slot=row['slot'],kind=row['kind'],receipt=receipt))
 matrix={}; paired={}; rng=np.random.default_rng(20261017782776); families=sorted(roots); idx={(g['root'],g['arm'],g['ratio'],g['candidate_color']):g for g in games}; arms=['MATERIAL_ONLY','TWO_REGIME_INCREMENTAL']
 for arm in arms:
  for price in [1.,2.]:
   rr=[g for g in games if g['arm']==arm and g['ratio']==price]; matrix[f'{arm}:{price}']=dict(games=len(rr),outcomes=dict(Counter(g['outcome'] for g in rr)),known_rewards=sum(g['reward'] for g in rr if g['reward']is not None),unknown=sum(g['reward']is None for g in rr),mean_W_minus_L=None if any(g['reward']is None for g in rr)or len(rr)!=16 else sum(g['reward']for g in rr)/16,measured_game_seconds=sum(g['seconds'] for g in rr))
 def contrast(name,fn):
  values=[];unknown=0
  for family in families:
   vv=[]
   for role in(0,1):
    try:v=fn(family,role)
    except TypeError:v=None
    vv.append(v)
   if any(v is None for v in vv):unknown+=1;values.append((-4.,4.)if 'interaction'in name else(-2.,2.))
   else:values.append((sum(vv)/2,)*2)
  lo=np.array([v[0]for v in values]);hi=np.array([v[1]for v in values]);inds=rng.integers(0,len(values),size=(10000,len(values)));paired[name]=dict(family_blocks=8,unknown_family_blocks=unknown,lower=float(lo.mean()),upper=float(hi.mean()),descriptive95_envelope=[float(np.quantile(lo[inds].mean(axis=1),.025)),float(np.quantile(hi[inds].mean(axis=1),.975))],per_family=values)
 def reward(f,a,p,r):
  g=idx.get((f,a,p,r));return None if g is None else g['reward']
 for arm in arms:contrast('price_'+arm,lambda f,r,a=arm:reward(f,a,2.,r)-reward(f,a,1.,r))
 for price in [1.,2.]:contrast('candidate_solver_'+str(price),lambda f,r,p=price:reward(f,arms[1],p,r)-reward(f,arms[0],p,r))
 contrast('price_by_candidate_solver_interaction',lambda f,r:(reward(f,arms[1],2.,r)-reward(f,arms[1],1.,r))-(reward(f,arms[0],2.,r)-reward(f,arms[0],1.,r)))
 result=dict(status='PASS_FIXED_FOE_ACTUAL_2x2_RECORDS_BUDGETS_CERTIFICATES',games=len(games),expected_games=64,missing=64-len(games),moves=count,certificates=len(certificates),certificate_checks=certificate_checks,matrix=matrix,contrasts=paired,sources=dict(sources),normal_depths=[dict(arm=a,is_candidate=c,depth=d,count=n) for (a,c,d),n in depths.items()],seconds=time.perf_counter()-start,scope='Correctfixedfoe/price/roleALLarms withactualsame-rootrecords. Candidateonly atmostonefreshproof perHIGH/LOWregime, boundcursor suppressesnewattempts; SAMEfoe .2/.1/1s. Actualpaidcandidate42/15/1s and60caller budget vsnormal1.5sexplicit, not equalcompute speedclaim. Completeactualrecords/certificateAND+currentcursors, missing/U notDRAW. 8exposedTRAINfamilies, no equivalencemargin/fit/holdout/defaultadoption. Unknowninteraction bounds require[-4,4]ifpresent; completecase normalpointestimates only.')
 with (OUT/'result.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items() if k not in ('certificate_checks','normal_depths')}))
if __name__=='__main__':run()
