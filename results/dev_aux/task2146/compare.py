"""Paired saved-certificate verifier cost/acceptance, no new proof or game."""
from pathlib import Path
from collections import Counter
from dataclasses import replace
import json,time,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.generic_session_win_proof import SessionWinCertificate,verify_session_certificate,SessionProofNode
from scripts.generic_win_proof import _same_state
from results.dev_aux.task2048.portable_certificate import decode
from results.dev_aux.task2145.verify import verify_prefix_session_certificate
from results.dev_aux.task2131.stop_reader import ParsedStopReader
OUT=Path('results/dev_aux/task2146')
def run():
 if(OUT/'started.json').exists():raise RuntimeError('single180cap neverrestart')
 start=time.perf_counter();deadline=start+180;stop=ParsedStopReader(Path.cwd())
 def cancel():stop();return time.perf_counter()>=deadline
 (OUT/'started.json').write_text(json.dumps(dict(source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cap_seconds=180)),encoding='utf-8')
 cases=[];inputs=json.loads(Path('results/dev_aux/task2139/inputs.json').read_text(encoding='utf-8'))['roots'];gg={g['physical_id']:g for g in map(json.loads,Path('results/dev_aux/task2139/games.jsonl').read_text(encoding='utf-8').splitlines())if g['reused_from']is None}
 for r in map(json.loads,Path('results/dev_aux/task2139/certificates.jsonl').read_text(encoding='utf-8').splitlines()):cases.append((f"2139-{r['physical_id']}-{r['ply']}",inputs[gg[r['physical_id']]['family']]['rules'],r))
 for r in json.loads(Path('results/dev_aux/task2143/certificates.json').read_text(encoding='utf-8')):cases.append((f"2143-{r['family']}",r['rules'],r))
 compiled={};rows=[];mutations=[]
 for index,(name,rules,r)in enumerate(cases):
  if rules not in compiled:compiled[rules]=compile_ruleset_for_execution(deserialize_ruleset(Path(rules).read_text(encoding='utf-8')))
  c=compiled[rules];s=GameSession.replay(c,deserialize_game_record(json.dumps(r['root_record'])));cert=SessionWinCertificate(c.ruleset_fingerprint,s.to_record(),s.state,r['target'],decode(r['tree'],c.ruleset_fingerprint));before=s.to_record();state=s.state
  arms=[('REFERENCE',verify_session_certificate),('PREFIX',verify_prefix_session_certificate)]
  if index%2:arms.reverse()
  caps=[.2,1.5,4.]if name.startswith('2143')else[.2]
  for seconds in caps:
   for arm,fn in arms:
    if cancel():raise TimeoutError('original180cap')
    vr=fn(s,cert,max_nodes=16384,seconds=seconds,cancel=cancel);rows.append(dict(case=name,arm=arm,seconds_cap=seconds,receipt=vr))
  # All-case target and root-binding forgeries; larger tree structure adversaries below.
  bad=[('booltarget',replace(cert,target=bool(cert.target))),('wrongfingerprint',replace(cert,ruleset_fingerprint='forged')),('nondecreasingrootrank',replace(cert,tree=replace(cert.tree,rank=0)))]
  if cert.tree.edges:
   choice,child=cert.tree.edges[0];bad.append(('same_rank_child',replace(cert,tree=replace(cert.tree,edges=((choice,replace(child,rank=cert.tree.rank)),)+cert.tree.edges[1:]))))
  for label,forged in bad:
   got=[fn(s,forged,max_nodes=16384,seconds=4.,cancel=cancel)for _,fn in arms];assert all(not x['verified']for x in got);mutations.append(dict(case=name,mutation=label,reasons=[x['reason']for x in got]))
  assert s.to_record()==before and _same_state(s.state,state)
 complete={}
 for arm in('REFERENCE','PREFIX'):
  rr=[r for r in rows if r['arm']==arm and r['seconds_cap']==.2];complete[arm]=dict(queries=len(rr),verified=sum(r['receipt']['verified']for r in rr),nodes=sum(r['receipt']['nodes']for r in rr),seconds=sum(r['receipt']['seconds']for r in rr))
 out=dict(status='PASS_PAIRED_CAPPED_SAVED_CERTIFICATES_AND_FORGERIES',certificates=len(cases),queries=len(rows),forgeries=len(mutations),cap_point2=complete,seconds=time.perf_counter()-start,actual_stop_reads=stop.reads,scope='Sameactualsavedcertificates andfullhistory, cold verifier state eachquery, pairedcounterbalance. No free earlierverification/reward/policyadoption; ordinaryconcurrentload.',larger=[r for r in rows if r['case'].startswith('2143')])
 (OUT/'queries.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');(OUT/'mutations.json').write_text(json.dumps(mutations,indent=2),encoding='utf-8');(OUT/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out),flush=True)
if __name__=='__main__':run()
