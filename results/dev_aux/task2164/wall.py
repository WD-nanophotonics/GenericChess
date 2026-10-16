from pathlib import Path
from fractions import Fraction
from collections import Counter
import json,time,hashlib
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from scripts.generic_proof_player import ProofMaterialPlayer
from scripts.generic_proof_rnb_bridge import uci
from results.dev_aux.task2100.campaign import evaluate
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2164')
def run():
 if(OUT/'started.json').exists():raise RuntimeError('singlecapneverrestart')
 p=json.loads((OUT/'plan.json').read_text(encoding='utf-8'));start=time.perf_counter();deadline=start+p['one_cap_seconds'];stop=EvidenceStopReader(Path.cwd());(OUT/'started.json').write_text(json.dumps(dict(source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cap=p['one_cap_seconds'])),encoding='utf-8');roots=json.loads(Path('results/dev_aux/task2158/inputs.json').read_text(encoding='utf-8'))['roots'][:32];expected={(r['family'],r['depth'],x['ratio']):x['first_action']for r in map(json.loads,Path('results/dev_aux/task2162/queries.jsonl').read_text(encoding='utf-8').splitlines())for x in r['fixed_cells']};rows=[];status='COMPLETE'
 def cancel():stop();return time.perf_counter()>=deadline
 with(OUT/'queries.jsonl').open('x',encoding='utf-8')as f:
  for root in roots:
   c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text(encoding='utf-8')));s=GameSession(c)
   for depth in p['depths']:
    off=(root['family']+depth)%3;walls=p['wall_seconds'][off:]+p['wall_seconds'][:off]
    for wall in walls:
     off=(root['family']+depth)%7;prices=p['ratios'][off:]+p['ratios'][:off]
     for price in prices:
      if cancel():status='CAP_PARTIAL';break
      d=ProofMaterialPlayer(c,evaluate(float(Fraction(price))),proof_enabled=False,max_depth=depth).choose(s.state,max_nodes=p['max_nodes'],seconds=wall,cancel=cancel)
      choice=None if d.action is None else uci(d.action);full=d.completed_depth==depth
      if full:assert choice==expected[(root['family'],depth,price)]
      r=dict(family=root['family'],depth=depth,price=price,wall=wall,nodes=d.nodes,seconds=d.seconds,completed_depth=d.completed_depth,full=full,choice=choice,source=d.source,exit_cause=d.exit_cause,expected_fullchoice=expected[(root['family'],depth,price)],wall_overrun=max(0.,d.seconds-wall));rows.append(r);f.write(json.dumps(r)+'\n');f.flush()
     if status!='COMPLETE':break
    if status!='COMPLETE':break
   if status!='COMPLETE':break
   if root['family']%8==7:print(json.dumps(dict(family=root['family'],queries=len(rows),seconds=time.perf_counter()-start)),flush=True)
 groups={}
 for d in p['depths']:
  for w in p['wall_seconds']:
   rr=[r for r in rows if r['depth']==d and r['wall']==w];groups[str(d)+'/'+str(w)]=dict(queries=len(rr),complete=sum(r['full']for r in rr),nochoice=sum(r['choice']is None for r in rr),depth0=sum(r['completed_depth']==0 for r in rr),nodes=sum(r['nodes']for r in rr),actual_seconds=sum(r['seconds']for r in rr),exit_causes=dict(Counter(r['exit_cause']for r in rr)),max_wall_overrun=max([r['wall_overrun']for r in rr]or[0]))
 out=dict(status=status,queries=len(rows),seconds=time.perf_counter()-start,groups=groups,new_game_or_fit_or_DEV=0,scope=p['scope']);(OUT/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out),flush=True)
if __name__=='__main__':run()
