"""Independent frozen-selection, closed-certificate and actual-history consumer."""
from pathlib import Path
from collections import defaultdict,Counter
from copy import copy
import json,time,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import SessionChoice,execute
from results.dev_aux.task2320.refutation import verify_no_forced_win,RefutationCursor
from results.dev_aux.task2320.build import decode
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2322')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run():
 t=time.perf_counter();stop=EvidenceStopReader(Path.cwd());read=lambda p:json.loads(Path(p).read_text());frozen=read('results/dev_aux/task2311/inputs.json');assert not frozen['labels_read']and frozen['new_queries']==0 and sha(frozen['source'])==frozen['source_sha'];old=list(map(json.loads,Path(frozen['source']).read_text().splitlines()));slots={r['slot']:r for r in read('results/dev_aux/task2307/slots.json')};selected=[d for d in old if d['is_candidate']and d['new_proof_attempt']];assert len(selected)==len(frozen['occurrences'])==27;groups={}
 for d,o in zip(selected,frozen['occurrences']):
  assert o['slot']==d['slot']and o['ply']==d['ply']and d['regime']=='LOW';c=frozen['contexts'][o['context']];assert c['root_record']==d['root_record']and c['root_state_sha']==d['root_state_sha'];groups.setdefault((c['rules'],json.dumps(d['root_record'],sort_keys=True)),len(groups));assert o['context']==groups[(c['rules'],json.dumps(d['root_record'],sort_keys=True))];assert o['remaining_horizon']==96-d['ply']and o['ratio']==slots[d['slot']]['ratio']
 assert len(groups)==14
 folder=Path('results/dev_aux/task2321');p=read(folder/'plan.json');done=read(folder/'result.json');inputs=read(folder/'inputs.json');assert sha(folder/'inputs.json')==p['inputs_sha'];assert len(inputs)==14
 for name,h in p['pins'].items():assert sha(name)==h
 queries=list(map(json.loads,(folder/'queries.jsonl').read_text().splitlines()));candidates=list(map(json.loads,(folder/'candidates.jsonl').read_text().splitlines()));conversions={r['query']:r for r in read(folder/'conversions.json')};expected=[(m,r['context'])for m in p['modes']for r in inputs];assert len(queries)==done['queries']and done['missing']==28-len(queries);assert [(q['mode'],q['context'])for q in queries]==expected[:len(queries)];candidate_by={r['query']:r for r in candidates};summary=[];steps=0
 def cancel():stop();return time.perf_counter()-t>=600
 for q in queries:
  if cancel():raise TimeoutError('independent_negativeconsumer_cap')
  r=inputs[q['context']];assert r['root_record']==frozen['contexts'][r['context']]['root_record'];c=compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(r['root_record'])));assert sha_state(s)==r['root_state_sha'];assert q['discovery']['mode']==q['mode'];assert q['discovery']['positions']<=p['query_nodes']and q['discovery']['edges']<=p['query_edges']+1
  if q['query']not in candidate_by:assert not q['admitted']and q['claim']=='UNKNOWN';continue
  raw=candidate_by[q['query']];assert raw['mode']==q['mode']and raw['context']==q['context'];cert=decode(s,raw['certificate']);v=verify_no_forced_win(s,cert,max_nodes=65536,seconds=60.,cancel=cancel);assert v['verified'];entry=dict(query=q['query'],mode=q['mode'],context=q['context'],offline_verification=v,original_admitted=q['admitted'],actual_conversion_plies=0)
  if q['admitted']:
   assert q['claim']=='NO_FORCED_WIN'and q['independent']['verified']and q['current_cursor']['verified']and q['discovery']['closed'];assert q['independent']['seconds']+q['current_cursor']['seconds']<=15.1
   cur=RefutationCursor(s,cert,max_nodes=65536,seconds=60.,cancel=cancel);result=conversions[q['query']];actions=deserialize_game_record(json.dumps(result['record'])).actions[len(s.to_record().actions):];assert len(actions)==result['moves']
   for a in actions:
    before=copy(s);choice=SessionChoice('ACTION',action=a)
    if s.state.position.side_to_move!=cert.target:assert cur.choose(s)==choice
    execute(s,choice);cur.observe(before,choice,s);steps+=1
   assert s.result.status is not SessionStatus.ONGOING and s.result.winner!=cert.target and s.result.status.value==result['actual_result']and s.result.winner==result['actual_winner'];entry['actual_conversion_plies']=len(actions)
  else:assert q['claim']=='UNKNOWN'and q['query']not in conversions
  summary.append(entry)
 assert len(conversions)==sum(q['admitted']for q in queries)==done['qualified_actual_rollouts']and steps==done['qualified_actual_rollout_moves'];out=dict(status='PASS_ALL14_SELECTION_NEGATIVE_CANDIDATES_AND_ACTUAL_CURSOR_ROLLOUTS',frozen_occurrences=27,unique_fullhistory_contexts=14,queries=len(queries),missing=28-len(queries),candidates=len(candidates),original_admitted=len(conversions),actual_qualification_moves=steps,candidate_checks=summary,seconds=time.perf_counter()-t,scope='Completeactualselection/sourcepins/queryorder/caps andALLsavednegativecertificates independentlychecked; alloriginallyadmittedcurrentcursors/actualnon-targetWINterminals replayed. Offlinecertificatepass doesnotupgradeoriginaltimedUNKNOWN. Samepublicengine/checker notexternalsecondengine. No actualDRAWlabel/reward/onlinefilteradoption; explicitteacherprepaymentretained.')
 with(OUT/'result.json').open('x')as f:json.dump(out,f,indent=2)
 print(json.dumps({k:v for k,v in out.items()if k!='candidate_checks'}))
def sha_state(s):return hashlib.sha256(repr(s.state).encode()).hexdigest()
if __name__=='__main__':run()
