"""Frozen finite-domain threshold scheduling comparison; old labels unchanged."""
from pathlib import Path
from dataclasses import replace
import json,hashlib,time
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import RuleDeclaration
from generic_chess.session.session import GameSession
from scripts.generic_session_win_proof import verify_session_certificate
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn
from scripts.generic_session_win_proof_terminal_first import prove_session_win_terminal_first
OUT=Path('results/dev_aux/task1840')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name,data):
 with (OUT/name).open('x',encoding='utf-8') as f:json.dump(data,f,indent=2)
def freeze():
 files=[__file__,'scripts/generic_session_win_proof_terminal_first.py','scripts/generic_session_win_proof_batch_pn.py','results/dev_aux/task1830/cases.jsonl','results/dev_aux/task1822/rules.json']
 write('plan.json',dict(question='Can ordering already generated actual terminal successors reduce visited work without omitting defenses or changing certified finite outcomes?',source_sha={str(p):sha(p) for p in files},max_nodes=65536,seconds=3.,max_depth=5,whole_seconds=180,expected_calls=64,scope='Existing exposed32target labels from16finite rules; no new oracle labels, no policy/game/price selection, no oldcap continuation. Counterbalance method order by case+target. No universal equivalence claim.'))
def run():
 p=json.loads((OUT/'plan.json').read_text());assert all(sha(f)==h for f,h in p['source_sha'].items())
 base=deserialize_ruleset(Path('results/dev_aux/task1822/rules.json').read_text());cases=[json.loads(x) for x in Path('results/dev_aux/task1830/cases.jsonl').read_text().splitlines()]
 profiles={'NONE':(),'DEFENDER_RESTART':(RuleDeclaration('restart',1,require_not_in_check=False,failure_outcome='RESTART'),),'DEFENDER_LOSS':(RuleDeclaration('loss',1,require_not_in_check=False,failure_outcome='LOSS'),),'ACTOR_WIN':(RuleDeclaration('win',0,require_not_in_check=False,failure_outcome='WIN'),)}
 rows=[];start=time.perf_counter();error=None
 with (OUT/'calls.jsonl').open('x',encoding='utf-8') as log:
  try:
   for ci,case in enumerate(cases):
    c=compile_ruleset_for_execution(replace(base,max_ply=4,declarations=profiles[case['profile']]))
    assert c.ruleset_fingerprint==case['fingerprint'];s=GameSession(c,case['setup'])
    for target in (0,1):
     methods=[('BATCH',prove_session_win_batch_pn),('TERMINAL_FIRST',prove_session_win_terminal_first)]
     if (ci+target)%2:methods.reverse()
     pair=[]
     for method,solver in methods:
      assert time.perf_counter()-start<p['whole_seconds']
      r=solver(s,target=target,max_nodes=p['max_nodes'],seconds=p['seconds'],max_depth=p['max_depth'])
      v=None
      if r.certificate is not None:
       assert case['target0_wdl']==(1 if target==0 else -1)
       v=verify_session_certificate(s,r.certificate,max_nodes=262144,seconds=3.);assert v['verified']
      row=dict(family=case['family'],profile=case['profile'],target=target,method=method,status=r.status,reason=r.reason,nodes=r.nodes,seconds=r.seconds,frontiers=r.frontiers,transitions=r.transitions,eager_board_successors=r.eager_board_successors,claims_assessed=r.claims_assessed,iterations=r.iterations,recursive_calls=getattr(r,'recursive_calls',None),selections=getattr(r,'selections',None),certificate_sha=hashlib.sha256(repr(r.certificate).encode()).hexdigest() if r.certificate else None,verification=v)
      rows.append(row);pair.append(row);log.write(json.dumps(row)+'\n');log.flush()
     assert pair[0]['status']==pair[1]['status']
     print(json.dumps([dict(method=x['method'],family=x['family'],profile=x['profile'],target=target,status=x['status'],nodes=x['nodes']) for x in pair]),flush=True)
  except BaseException as ex:error=type(ex).__name__+':'+str(ex)
 write('result.json',dict(status='COMPLETE' if error is None else 'PARTIAL_PRESERVED',error=error,calls=len(rows),expected=p['expected_calls'],seconds=time.perf_counter()-start,groups=[dict(method=m,calls=sum(x['method']==m for x in rows),nodes=sum(x['nodes'] for x in rows if x['method']==m),seconds=sum(x['seconds'] for x in rows if x['method']==m),proven=sum(x['method']==m and x['status']=='PROVEN_WIN' for x in rows)) for m in ('BATCH','TERMINAL_FIRST')],new_native_or_games=0))
if __name__=='__main__':
 import sys
 {'freeze':freeze,'run':run}[sys.argv[1]]()
