"""Assemble a new complete-order TRAIN matrix with explicit original-source provenance."""
from pathlib import Path
import json,hashlib,copy
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2358')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run():
 EvidenceStopReader(Path.cwd())();new_folder=Path('results/dev_aux/task2355');p=json.loads((new_folder/'plan.json').read_text());done=json.loads((new_folder/'completion.json').read_text());matrix=json.loads((new_folder/'matrix.json').read_text());cache={}
 for task in(2325,2340,2355):
  folder=Path(f'results/dev_aux/task{task}');cache[task]={name:[json.loads(x)for x in(folder/name).read_text().splitlines()]for name in('games.jsonl','decisions.jsonl','certificates.jsonl')}
 games=[];ds=[];cs=[];missing=[];sources=[];slots=[]
 for m in matrix:
  expected={k:m[k]for k in('root','opponent','candidate_color','ratio','arm')};expected.update(slot=m['matrix_slot'],matrix_slot=m['matrix_slot']);slots.append(expected);source=cache[m['source_task']];gs=[g for g in source['games.jsonl']if g['slot']==m['source_slot']]
  if not gs:missing.append(m);continue
  assert len(gs)==1;g=gs[0];assert g['root']==m['root']and g['ratio']==m['ratio']and g['candidate_color']==m['candidate_color'];out=copy.deepcopy(g);out.update(expected);out.update(source_task=m['source_task'],source_slot=m['source_slot'],reused=m['kind']=='REUSED_ACTUAL_TERMINAL');games.append(out)
  for name,dest in(('decisions.jsonl',ds),('certificates.jsonl',cs)):
   for row in source[name]:
    if row['slot']==m['source_slot']:
     r=copy.deepcopy(row);r['slot']=m['matrix_slot'];dest.append(r)
  sources.append(dict(matrix_slot=m['matrix_slot'],source_task=m['source_task'],source_slot=m['source_slot'],kind=m['kind'],source_game_sha=hashlib.sha256(json.dumps(g,sort_keys=True).encode()).hexdigest()))
 def save(n,v):
  with(OUT/n).open('x',encoding='utf-8')as f:json.dump(v,f,indent=2)
 save('inputs.json',json.loads(Path(p['input']).read_text()));save('slots.json',slots)
 for name,rows in(('games.jsonl',games),('decisions.jsonl',ds),('certificates.jsonl',cs)):
  with(OUT/name).open('x',encoding='utf-8')as f:
   for row in rows:f.write(json.dumps(row)+'\n')
 p.update(input=str(OUT/'inputs.json'),input_sha=sha(OUT/'inputs.json'),slots_sha=sha(OUT/'slots.json'),expected_games=160);p['pins']=dict(p['pins'],**{str(new_folder/'plan.json'):sha(new_folder/'plan.json'),str(OUT/'assemble.py'):sha(OUT/'assemble.py')});p['scope']='DERIVEDnew82TRAINmatrix65reused+95fresh; virtualassemblynotnewgames. Originalsourceplan/caps/failed2340 unchanged; everyrecord/proof has source task+slot. Actualunknown/missingretained, novalidationpricequeries.';save('plan.json',p);save('completion.json',dict(status='COMPLETE'if len(games)==160 and all(g['reward']is not None for g in games)else'PARTIAL_MATRIX',games=len(games),expected_games=160,missing=160-len(games),decisions=len(ds),certificates=len(cs),outcomes={x:sum(g['outcome']==x for g in games)for x in'WLDU'},new_task_status=done['status'],scope=p['scope']));save('matrix-games.json',games);save('provenance.json',dict(rows=sources,missing=missing,source_stream_sha={str(Path(f'results/dev_aux/task{t}')/n):sha(Path(f'results/dev_aux/task{t}')/n)for t in cache for n in cache[t]}));print(json.dumps(dict(matrix_records=len(games),missing=len(missing),new_returned=done['games'])))
if __name__=='__main__':run()
