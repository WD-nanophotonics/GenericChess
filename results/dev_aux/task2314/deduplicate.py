"""Actual lookup opportunities: distinguish source-target pairs from fresh calls."""
from pathlib import Path
from collections import Counter,defaultdict
import json,time,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from results.dev_aux.task2205.consume import decode_graph
from results.dev_aux.task2199.semantic_graph import verify_graph
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2314')
def token(c,s):return(c.ruleset_fingerprint,json.dumps(json.loads(serialize_game_record(s.to_record())),sort_keys=True))
def run():
 start=time.perf_counter();stop=EvidenceStopReader(Path.cwd());folder=Path('results/dev_aux/task2289');p=json.loads((folder/'plan.json').read_text());roots={r['index']:r for r in json.loads(Path(p['input']).read_text())};games=list(map(json.loads,(folder/'games.jsonl').read_text().splitlines()));decisions={(d['slot'],d['ply']):d for d in map(json.loads,(folder/'decisions.jsonl').read_text().splitlines())};raw=list(map(json.loads,(folder/'certificates.jsonl').read_text().splitlines()));sources=defaultdict(list)
 def cancel():stop();return time.perf_counter()-start>120
 for i,row in enumerate(raw):
  if row['kind']!='GRAPH':continue
  r=roots[games[row['slot']]['root']];c=compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(row['root_record'])));cert=decode_graph(s,row['certificate']);check=verify_graph(s,cert,max_nodes=65536,seconds=5.,cancel=cancel);assert check['verified'];sources[token(c,s)].append(dict(source=i,slot=row['slot'],ply=row['ply'],target=cert.target,source_verification_seconds=check['seconds']))
 pairs=0;prefixes=0;hits=[]
 for g in games:
  r=roots[g['root']];c=compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(r['record'])));actions=deserialize_game_record(json.dumps(g['record'])).actions[len(s.to_record().actions):]
  for ply in range(len(actions)+1):
   if cancel():raise TimeoutError('dedup_cap')
   if s.result.status is SessionStatus.ONGOING:
    prefixes+=1;eligible=[x for x in sources.get(token(c,s),[])if(x['slot'],x['ply'])<(g['slot'],ply)]
    if eligible:
     d=decisions[(g['slot'],ply)];pairs+=len(eligible);fresh=d['proof_seconds']>0;earliest=min(eligible,key=lambda x:(x['slot'],x['ply']));hits.append(dict(slot=g['slot'],ply=ply,root=g['root'],arm=g['arm'],ratio=g['ratio'],is_candidate=d['is_candidate'],target_side=d['side'],regime=d['regime'],prior_sources=eligible,source_pairs=len(eligible),chosen_earliest=earliest['source'],existing_new_proof_attempt_flag=d['new_proof_attempt'],observed_paid_fresh_proof_phase=fresh,source=d['source'],observed_proof_seconds=d['proof_seconds'],observed_verification_seconds=d['verification_seconds'],measured_choice_seconds=d['measured_seconds'],actual_outcome=g['outcome']))
   if ply<len(actions):s.submit(actions[ply])
 assert prefixes==2459 and pairs==43
 selected=[h for h in hits if h['observed_paid_fresh_proof_phase']];r=dict(status='PASS_ALL_NATURAL_EXACT_RECORD_OPPORTUNITY_DEDUP',prefixes=prefixes,source_target_pairs=pairs,unique_target_lookup_events=len(hits),observed_paid_fresh_proof_events=len(selected),candidate_flagged_attempt_events=sum(h['is_candidate']and h['existing_new_proof_attempt_flag']for h in hits),nonfresh_events=len(hits)-len(selected),observed_paid_fresh_proof_seconds=sum(h['observed_proof_seconds']for h in selected),observed_fresh_choice_seconds=sum(h['measured_choice_seconds']for h in selected),by_source=dict(Counter(h['source']for h in hits)),rows=hits,seconds=time.perf_counter()-start,scope='Exactfullrule+entireGameRecord roots ONLY; prior(slot,ply)strict. ALL2459prefixes,14actualgenericcerts freshverifiedforaudit. Dedup43source-targetpairs intoactualtargetevents beforecosts. Freshproofphase usesobservedproof_seconds>0, distinctcandidateattemptflag. No runtimebank/admission/game/pricechange; hypotheticalskiptime notmeasuredspeedup and sourceverificationcostpaid. No differenthistorynaturalhit is added.')
 with(OUT/'result.json').open('x')as f:json.dump(r,f,indent=2)
 print(json.dumps({k:v for k,v in r.items()if k!='rows'}))
if __name__=='__main__':run()
