"""Natural same-Position reuse census; only chronologically available generic proofs."""
from pathlib import Path
from copy import copy
from collections import Counter
import json,time,hashlib
from dataclasses import replace
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import choices,execute
from scripts.generic_win_proof import _same_state,_Budget
from results.dev_aux.task2205.consume import decode_graph
from results.dev_aux.task2199.semantic_graph import verify_graph,GraphStrategyCursor
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path("results/dev_aux/task2305")
def run():
 assert not(OUT/"result.json").exists();start=time.perf_counter();stop=EvidenceStopReader(Path.cwd());folder=Path("results/dev_aux/task2289");p=json.loads((folder/"plan.json").read_text());assert(folder/"completion.json").exists();roots={r["index"]:r for r in json.loads(Path(p["input"]).read_text())};games=[json.loads(x)for x in(folder/"games.jsonl").read_text().splitlines()];raw=[json.loads(x)for x in(folder/"certificates.jsonl").read_text().splitlines()];bykey={};certs={};hits=[];exact=0;prefixes=0
 def cancel():stop();return time.perf_counter()-start>=300
 for index,row in enumerate(raw):
  if row['kind']!='GRAPH':continue
  r=roots[games[row['slot']]['root']];c=compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(row['root_record'])));cert=decode_graph(s,row['certificate']);assert verify_graph(s,cert,max_nodes=65536,seconds=5.,cancel=cancel)['verified'];key=(c.ruleset_fingerprint,repr(s.state.position));bykey.setdefault(key,[]).append(index);certs[index]=(row,s,cert)
 for g in games:
  if cancel():raise TimeoutError('census_cap')
  r=roots[g['root']];c=compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(r['record'])));actions=deserialize_game_record(json.dumps(g['record'])).actions[len(s.to_record().actions):]
  for ply in range(len(actions)+1):
   if s.result.status is SessionStatus.ONGOING:
    prefixes+=1;key=(c.ruleset_fingerprint,repr(s.state.position))
    for i in bykey.get(key,[]):
     source,root,cert=certs[i]
     if(source['slot'],source['ply'])>=(g['slot'],ply):continue
     assert _same_state(root.state.position,s.state.position)
     if root.to_record()==s.to_record():exact+=1;continue
     record=json.loads(serialize_game_record(s.to_record()));token=hashlib.sha256(json.dumps(dict(source=i,target=record),sort_keys=True).encode()).hexdigest();hits.append(dict(key=token,source_certificate=i,source_slot=source['slot'],source_ply=source['ply'],target_slot=g['slot'],target_ply=ply,rules=r['rules'],target_record=record,source_record=source['root_record']))
   if ply<len(actions):s.submit(actions[ply])
 unique={r['key']:r for r in hits};chosen=sorted(unique.values(),key=lambda r:r['key'])[:8];(OUT/'frozen-candidates.json').write_bytes(json.dumps(chosen,indent=2).encode());rows=[];conversions=[]
 for hit in chosen:
  if cancel():raise TimeoutError('admission_cap')
  tick=time.perf_counter();c=compile_ruleset_for_execution(deserialize_ruleset(Path(hit['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(hit['target_record'])));row,oldroot,old=certs[hit['source_certificate']];assert old.ruleset_fingerprint==c.ruleset_fingerprint and _same_state(oldroot.state.position,s.state.position)
  cert=replace(old,root_record=s.to_record(),root_state=s.state);v=verify_graph(s,cert,max_nodes=65536,seconds=5.,cancel=cancel);result=dict(source=hit['source_certificate'],source_slot=hit['source_slot'],target_slot=hit['target_slot'],target_ply=hit['target_ply'],verification=v,admission_seconds=time.perf_counter()-tick,current_cursor=None,actual_conversion_moves=0)
  if v['verified']:
   cur=GraphStrategyCursor(s,cert,max_nodes=65536,seconds=5.,cancel=cancel);result['current_cursor']=cur.receipt;result['admission_seconds']=time.perf_counter()-tick
   while s.result.status is SessionStatus.ONGOING:
    if cancel():raise TimeoutError('conversion_cap')
    before=copy(s);choice=cur.choose(s)if s.state.position.side_to_move==cert.target else next(choices(s,_Budget(1000,1.,cancel)));execute(s,choice);cur.observe(before,choice,s);result['actual_conversion_moves']+=1
   assert s.result.winner==cert.target;conversions.append(dict(candidate=len(rows),record=json.loads(serialize_game_record(s.to_record()))))
  rows.append(result)
 (OUT/'receipts.json').write_bytes(json.dumps(rows,indent=2).encode());(OUT/'conversions.json').write_bytes(json.dumps(conversions,indent=2).encode());result=dict(status='COMPLETE_NATURAL_CHRONOLOGICAL_GENERIC_ROOT_REUSE_CENSUS',games=len(games),ongoing_actual_prefixes=prefixes,available_generic_graph_certificates=len(certs),exact_record_hits=exact,nonexact_hit_occurrences=len(hits),unique_source_target_history_pairs=len(unique),predeclared_maximum_admissions=8,selected_admissions=len(chosen),verified=sum(r['verification']['verified']for r in rows),actual_conversion_moves=sum(r['actual_conversion_moves']for r in rows),seconds=time.perf_counter()-start,scope='ALLclosed2289actualprefixes; samecompiledFP+FULLPosition verified, source(slot,ply)strictlyearlier, generic2289GRAPHonly/noreferenceassistedproofs. Completecensus BEFOREfirst8hashorderedadmissions, no outcome/admission-success selection. Exactrecordtrivialhitsseparate; 8chosenqualificationsnotallhitproofs. No actualbank/default/priceutility or counterfactualgameoutcomeclaim; savedconverterqualificationnotnewtraining.')
 (OUT/'result.json').write_bytes(json.dumps(result,indent=2).encode());print(json.dumps(result))
if __name__=="__main__":run()
