"""Closed76 evidence consumer, no producer/proof search or price fitting."""
from pathlib import Path
import json,time,hashlib
from dataclasses import replace
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import SessionWinCertificate,verify_session_certificate
from results.dev_aux.task2048.portable_certificate import decode as tree_decode
from results.dev_aux.task2205.consume import decode_graph
from results.dev_aux.task2199.semantic_graph import verify_graph
from scripts.generic_win_proof import _same_state
OUT=Path('results/dev_aux/task2215')
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def replay(root):
 c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text(encoding='utf-8')))
 s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])))
 assert hashlib.sha256(repr(s.state).encode()).hexdigest()==root['state_sha'];return s
def run():
 roots={r['index']:r for r in read('results/dev_aux/task2208/roots.json')};summaries={};checks=[];paths=0;moves=0;start=time.perf_counter()
 for task in(2208,2209):
  folder=Path(f'results/dev_aux/task{task}');done=read(folder/'completion.json');plan=read(folder/'plan.json');rows=[json.loads(l)for l in(folder/'queries.jsonl').read_text().splitlines()];certs=[json.loads(l)for l in(folder/'certificates.jsonl').read_text().splitlines()]
  assert len(rows)==done['queries']and done['missing']==plan['expected_queries']-len(rows)
  assert [r['query']for r in rows]==list(range(len(rows)))
  byq={r['query']:r for r in certs};assert len(byq)==len(certs);groups={}
  for row in rows:
   key=(row['root'],row['arm'],row.get('proof_cap',plan['proof_seconds']));assert key not in groups;groups[key]=row
   if row['actual_mate']is not None:
    s=replay(roots[row['root']]);actual=GameSession.replay(s.compiled,deserialize_game_record(json.dumps(row['actual_mate']['record'])))
    assert actual.result.status is not SessionStatus.ONGOING and actual.result.winner==roots[row['root']]['target']
    assert len(actual.to_record().actions)-len(s.to_record().actions)==row['actual_mate']['moves'];paths+=1;moves+=row['actual_mate']['moves']
  for i,item in byq.items():
   row=rows[i];assert item['root']==row['root']and item['arm']==row['arm'];s=replay(roots[row['root']]);target=roots[row['root']]['target']
   if row['arm']=='FULL_HISTORY_PN':
    cert=SessionWinCertificate(s.compiled.ruleset_fingerprint,s.to_record(),s.state,target,tree_decode(item['certificate'],s.compiled.ruleset_fingerprint));vr=verify_session_certificate(s,cert,max_nodes=262144,seconds=4.)
   else:
    cert=decode_graph(s,item['certificate']);vr=verify_graph(s,cert,max_nodes=262144,seconds=4.)
   assert vr['verified'];checks.append(dict(task=task,query=i,root=row['root'],arm=row['arm'],verified=vr,rank=cert.tree.rank if row['arm']=='FULL_HISTORY_PN'else cert.nodes[0].rank))
  summaries[task]=dict(status=done['status'],queries=len(rows),missing=done['missing'],saved_certificates=len(certs))
 result=dict(status='PASS_CLOSED76_SAVED_PROOFS_AND_ACTUAL_PATHS',seconds=time.perf_counter()-start,summaries=summaries,certificate_checks=checks,actual_paths=paths,actual_moves=moves,scope='Reconstructtypedcertificates solelyfromsavedJSON+fullactualrecord/rules; independentall-defenseverifiers/publicSessionactualwinner. No proofsearch/teacher/fit orfreshstatisticalgames. SamepublicCoreauthority shared, notindependentall-domainruleinterpreter.')
 with(OUT/'proof-consumer.json').open('x',encoding='utf-8')as f:json.dump(result,f,indent=2)
 print(json.dumps({k:result[k]for k in('status','seconds','actual_paths','actual_moves')}))
if __name__=='__main__':run()
