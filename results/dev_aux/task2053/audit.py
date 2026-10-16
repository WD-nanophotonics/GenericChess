"""Proof coverage schedule/receipt audit and portable sample verification, no search."""
from pathlib import Path
from collections import Counter
import json,hashlib
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from scripts.generic_session_win_proof import SessionWinCertificate,verify_session_certificate
from results.dev_aux.task2048.portable_certificate import decode
P=Path('results/dev_aux/task2052');OUT=Path('results/dev_aux/task2053')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def main():
 plan=read(P/'plan.json');result=read(P/'result.json');rows=[json.loads(x)for x in(P/'queries.jsonl').read_text(encoding='utf-8').splitlines()];scheduled=[(f,t,n)for f in plan['families']for t in plan['targets']for n in plan['PN_nodes']]
 assert len(scheduled)==192 and len(rows)==result['queries'] and(result['status']!='COMPLETE'or len(rows)==192)
 assert all(hashlib.sha256(Path(k).read_bytes()).hexdigest()==v for k,v in plan['files'].items())
 for ordinal,(expected,row)in enumerate(zip(scheduled,rows)):
  assert(row['family'],row['target'],row['budget'])==expected and row['ordinal']==ordinal and row['nodes']<=row['budget']
  assert(row['label']=='PROVED_WIN')==(row['verification']is not None and row['verification']['verified'])
  if row['label']=='PROVED_WIN':assert row['solver_status']=='PROVEN_WIN'and row['rank']is not None and 0<row['rank']<=64
 c=compile_ruleset_for_execution(deserialize_ruleset(Path(plan['rules']).read_text(encoding='utf-8')));roots=read(plan['roots'])['roots'];certificates=[]
 for n in plan['PN_nodes']:
  proven=[r for r in rows if r['budget']==n and r['label']=='PROVED_WIN'];samples=[r for r in rows if r['budget']==n and r['certificate_sample']is not None]
  assert len(samples)==(1 if proven else 0)
  if not samples:continue
  row=samples[0];assert row['ordinal']==proven[0]['ordinal'];data=read(P/row['certificate_sample']);session=GameSession(c,roots[row['family']]['setup'])
  assert data['root_record']==json.loads(serialize_game_record(session.to_record()))and data['target']==row['target']and data['budget']==n
  certificate=SessionWinCertificate(c.ruleset_fingerprint,session.to_record(),session.state,data['target'],decode(data['tree'],c.ruleset_fingerprint));receipt=verify_session_certificate(session,certificate,max_nodes=65536,seconds=3.);assert receipt['verified'];certificates.append(dict(budget=n,family=row['family'],target=row['target'],receipt=receipt))
 output=dict(status='PASS_FROZEN_PROOF_COVERAGE_RECEIPTS',queries=len(rows),planned=192,complete=result['status']=='COMPLETE',unrun=result['unrun'],label_counts=dict(Counter(r['label']for r in rows)),per_budget=result['summary'],verified_samples=certificates,new_PN_or_Native_calls=0,scope='Exposed-root diagnostic, not fresh valuevalidation. UNKNOWN remains unknown. Any supplied samples reverified through exact full-history GameSession; none exist if no proof succeeds; all receipt/call metadata bound to frozen source, no new proofs or stronger labels duringaudit.')
 (OUT/'result.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8');print(json.dumps(output))
if __name__=='__main__':main()
