"""Independently audit fixed-opponent candidate-depth actual games and every receipt."""
from pathlib import Path
from collections import Counter,defaultdict
import json,time,hashlib,random
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.actions import action_to_dict
from scripts.generic_proof_rnb_bridge import actor_state,uci
from scripts.generic_royal_actor import RoyalActor
from scripts.generic_win_proof import _same_state,_ordered
from scripts.generic_session_win_proof import SessionWinCertificate,verify_session_certificate
from results.dev_aux.task2048.portable_certificate import decode
from results.dev_aux.task2100.campaign import sha_state
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2173')
def audit(cancel=None):
 root=Path('results/dev_aux/task2167');start=time.perf_counter();deadline=start+180;stop=EvidenceStopReader(Path.cwd())if cancel is None else None
 def check():
  if stop:stop()
  if time.perf_counter()>=deadline or(cancel is not None and cancel()):raise TimeoutError('one180auditcap')
 p=json.loads((root/'plan.json').read_text(encoding='utf-8'));done=json.loads((root/'completion.json').read_text(encoding='utf-8'));started=json.loads((root/'started.json').read_text(encoding='utf-8'));assert hashlib.sha256((root/'learn.py').read_bytes()).hexdigest()==started['source_sha']==p['source_sha'];assert hashlib.sha256((root/'inputs.json').read_bytes()).hexdigest()==p['input_sha'];inputs=json.loads((root/'inputs.json').read_text(encoding='utf-8'))['roots'];games=list(map(json.loads,(root/'games.jsonl').read_text(encoding='utf-8').splitlines()));moves=defaultdict(list);decisions=defaultdict(list)
 for r in map(json.loads,(root/'moves.jsonl').read_text(encoding='utf-8').splitlines()):moves[r['physical_id']].append(r)
 for r in map(json.loads,(root/'decisions.jsonl').read_text(encoding='utf-8').splitlines()):decisions[r['physical_id']].append(r)
 expected=[]
 for family in range(32):
  for foe in(p['TRAIN_foes']if family%2==0 else list(reversed(p['TRAIN_foes']))):
   for role in(0,1):
    cond=[(price,depth)for price in p['ratios']for depth in p['candidate_depths']];off=(family+role)%4;cond=cond[off:]+cond[:off]
    if(family+role)%2:cond=list(reversed(cond))
    expected.extend((family,foe,role,price,depth)for price,depth in cond)
 assert len(games)<=len(expected)==512;actor=RoyalActor(3);counts=Counter();bycondition=defaultdict(Counter);compiled={};roots_for_cert={};actualrecords={}
 for index,g in enumerate(games):
  check();assert g['physical_id']==g['logical_slot']==index and g['reused_from']is None and g['phase']=='TRAIN_DIAGNOSTIC';assert(g['family'],g['opponent_ratio'],g['candidate_side'],g['ratio'],g['candidate_depth'])==expected[index];assert g['opponent_depth']==2
  family=g['family']
  if family not in compiled:compiled[family]=compile_ruleset_for_execution(deserialize_ruleset(Path(inputs[family]['rules']).read_text(encoding='utf-8')))
  c=compiled[family];s=GameSession(c);rec=deserialize_game_record(json.dumps(g['record']));ms=moves[index];ds=decisions[index];assert len(ms)==len(rec.actions)==g['moves'];assert len(ds)>=len(ms)
  for ply,(m,a)in enumerate(zip(ms,rec.actions)):
   d=ds[ply];side=s.state.position.side_to_move;candidate=side==g['candidate_side'];nodes=512 if candidate else 64;depth=g['candidate_depth']if candidate else 2
   assert s.result.status is SessionStatus.ONGOING and m['side']==d['side']==side and m['is_candidate']==d['is_candidate']==candidate;assert sha_state(s.state)==m['before_state_sha']==d['root_state_sha'];assert _same_state(deserialize_game_record(json.dumps(d['root_record'])),s.to_record());assert d['ruleset_fingerprint']==c.ruleset_fingerprint
   assert d['requested_limits']['normal_nodes']==nodes and d['requested_limits']['normal_depth']==depth;assert d['actual_phase_limits']==m['phase_limits']and m['phase_limits']['normal_nodes']==nodes and m['phase_limits']['normal_seconds']==.05
   assert m['search_nodes']<=nodes and m['proof_nodes']<=1024 and m['verification_nodes']<=16384 and m['fill_verification_nodes']<=16384
   assert d['choice']['kind']=='ACTION'and d['choice']['action']==m['choice']==action_to_dict(a)
   legal={uci(x):x for x in s.legal_actions()};literal=dict(actor.moves(actor_state(s.state)));assert set(legal)==set(literal)and uci(a)in legal
   normal=d['normal_receipt']
   if normal is not None:assert normal['nodes']==d['search_nodes']and normal['completed_depth']<=depth
   if d['source']=='PRECOMPUTED_LEGAL_FALLBACK':assert a==_ordered(s.legal_actions())[0];counts['actual_paid_fallback']+=1
   if d['source']=='PROOF':roots_for_cert[index,ply]=s.to_record();counts['proof_certificates']+=1
   cond=str(g['ratio'])+'/depth'+str(g['candidate_depth'])+('/candidate'if candidate else'/foe');cost=bycondition[cond];cost['moves']+=1;cost['normal_completed_requested']+=normal is not None and normal['completed_depth']==depth;cost['normal_returned']+=normal is not None
   for k in('seconds','normal_seconds','proof_seconds','verification_seconds','fill_verification_seconds','search_nodes','proof_nodes'):cost[k]+=d[k]
   s.submit(a);assert actor_state(s.state)==literal[uci(a)]and sha_state(s.state)==m['after_state_sha']and dict(status=s.result.status.value,winner=s.result.winner)==m['result'];counts['moves']+=1
  replay=GameSession.replay(c,rec);assert _same_state(replay.state,s.state)and replay.result==s.result and sha_state(s.state)==g['final_state_sha'];outcome='UNKNOWN'if s.result.status is SessionStatus.ONGOING else'DRAW'if s.result.winner is None else'WIN'if s.result.winner==g['candidate_side']else'LOSS';assert g['outcome']==outcome and g['score']==(None if outcome=='UNKNOWN'else 1 if outcome=='WIN'else-1 if outcome=='LOSS'else 0);counts[outcome]+=1;actualrecords[index]=rec
 assert len(games)==done['physical_games']==done['logical_games']and counts['moves']==done['moves'];certs=list(map(json.loads,(root/'certificates.jsonl').read_text(encoding='utf-8').splitlines()));assert {(r['physical_id'],r['ply'])for r in certs}==set(roots_for_cert);verified=[]
 for r in certs:
  check();g=games[r['physical_id']];c=compiled[g['family']];rec=deserialize_game_record(json.dumps(r['root_record']));assert _same_state(rec,roots_for_cert[r['physical_id'],r['ply']]);s=GameSession.replay(c,rec);cert=SessionWinCertificate(c.ruleset_fingerprint,rec,s.state,r['target'],decode(r['tree'],c.ruleset_fingerprint));v=verify_session_certificate(s,cert,max_nodes=65536,seconds=2.);assert v['verified'];verified.append(v)
 # Paired family effects; no policy or price selection. UNKNOWN prevents completed summary.
 familyrows=[];effects={}
 if len(games)==512 and counts['UNKNOWN']==0:
  for family in range(32):
   means={(price,depth):sum(g['score']for g in games if g['family']==family and g['ratio']==price and g['candidate_depth']==depth)/4 for price in(.25,1.)for depth in(2,3)}
   familyrows.append(dict(family=family,means={str(k):v for k,v in means.items()},depth_gain_point25=means[.25,3]-means[.25,2],depth_gain_1=means[1.,3]-means[1.,2],price_gain_depth2=means[.25,2]-means[1.,2],price_gain_depth3=means[.25,3]-means[1.,3],interaction=(means[.25,3]-means[1.,3])-(means[.25,2]-means[1.,2])))
  rng=random.Random(20261016742173)
  for key in('depth_gain_point25','depth_gain_1','price_gain_depth2','price_gain_depth3','interaction'):
   vals=[r[key]for r in familyrows];boots=sorted(sum(rng.choice(vals)for _ in vals)/len(vals)for _ in range(10000));effects[key]=dict(mean=sum(vals)/32,bootstrap_percentile95=[boots[249],boots[9749]],positive=sum(x>0 for x in vals),negative=sum(x<0 for x in vals),zero=sum(x==0 for x in vals))
 pairs=[]
 for family in range(32):
  for foe in(.5,2.):
   for role in(0,1):
    for price in(.25,1.):
     gg=[g for g in games if(g['family'],g['opponent_ratio'],g['candidate_side'],g['ratio'])==(family,foe,role,price)];dd={g['candidate_depth']:g for g in gg}
     if set(dd)!={2,3}:continue
     a,b=dd[2],dd[3];ma,mb=moves[a['physical_id']],moves[b['physical_id']];first=None
     for x,y in zip(ma,mb):
      if x['choice']!=y['choice']:
       assert x['before_state_sha']==y['before_state_sha'];first=dict(ply=x['ply'],is_candidate=x['is_candidate'],sources=[x['source'],y['source']],completed_depths=[x['completed_depth'],y['completed_depth']]);break
     pairs.append(dict(family=family,foe=foe,role=role,price=price,first_divergence=first,outcomes=[a['outcome'],b['outcome']]))
 out=dict(status='PASS_ACTUAL_RECORDS_FULL_DECISIONS_FIXED_OPPONENT_AND_CERTIFICATES',physical=len(games),moves=counts['moves'],missing=512-len(games),counts=dict(counts),certificate_verifier_nodes=sum(v['nodes']for v in verified),effects=effects,family_effects=familyrows,costs={k:dict(v)for k,v in bycondition.items()},pairs=pairs,seconds=time.perf_counter()-start,scope='Freshroot conditionaldistribution; fixedopponent setup, requestedcandidate normaldepth onlychanges betweenpaireddeptharms. Actualwallcensor/changedpaths/certcost included. Position WDL never reward; CIs descriptive/no equivalence/priceoptimum/generalization claim.');(OUT/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items()if k not in('costs','pairs','family_effects')}),flush=True)
if __name__=='__main__':audit()
