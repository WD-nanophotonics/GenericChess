import sys,json,time,hashlib,re
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task360'));sys.path.insert(0,str(R/'results/dev_aux/task364'));sys.path.insert(0,str(R/'results/dev_aux/task381'));import adapter as A;import run as G;import audit as V
O=R/'results/dev_aux/task452';O.mkdir(exist_ok=True);assert not(O/'result.json').exists(),'Preserve completed qualification';D=json.loads((R/'results/dev_aux/task445/declaration.json').read_text(encoding='utf-8'));groups={};sources=[]
for task,budget in [(449,1024),(450,1024)]:
 folder=R/f'results/dev_aux/task{task}';assert json.loads((folder/'result.json').read_text(encoding='utf-8'))['status']=='fit_completed';file=folder/'queries.jsonl';sources.append(dict(path=file.relative_to(R).as_posix(),sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
 for line,text in enumerate(file.open(encoding='utf-8'),1):
  q=json.loads(text);assert q['nodes_limit']==budget;k=(budget,tuple(q['weights']));item=dict(file=file.relative_to(R).as_posix(),line=line,query=q)
  if k not in groups:groups[k]=[item,item]
  else:groups[k][1]=item
exes={'old':R/'.local_agent/yaneura25/yaneura-material1-aux.exe','reuse':R/'.local_agent/yaneura26/yaneura-material1-cold-reuse.exe'}
declaration=dict(question='Finite qualification EVERY actualprice/budget first&lastcold responses, no success/model filter',sources=sources,node_budgets=D['training_node_budgets'],groups=[dict(nodes=k[0],weights=list(k[1]),source_refs=[dict(file=x['file'],line=x['line']) for x in pair]) for k,pair in groups.items()],executable_hashes={a:hashlib.sha256(e.read_bytes()).hexdigest() for a,e in exes.items()},scope='ALL actualnewfitvectors, samecoldinput/goal; no retraining or globalhistory/options/NNUE proof',cost='4go/group max~200groups, expected1-2min/300sfuse; no newgames/training');(O/'declaration.json').write_text(json.dumps(declaration,indent=2),encoding='utf-8')
t0=time.perf_counter();responses={};acks=[];pv=0
for arm,exe in exes.items():
 A.EXE=exe;rs=[]
 with (O/(arm+'_queries.jsonl')).open('w',encoding='utf-8') as journal:
  for (budget,w),pair in groups.items():
   G.stop();assert time.perf_counter()-t0<300,'Declared qualification fuse';e=A.Engine(w,journal);acks.append(dict(arm=arm,nodes=budget,weights=list(w),prices=e.prices))
   try:
    for item in pair:
     G.stop();q=item['query'];new=e.search(q['initial_sfen'],q['history'],budget);pv+=V.query(new);rs.append(new)
   finally:e.close()
 responses[arm]=rs
semantic=lambda lines:[' '.join(re.sub(r'\b(?:time|nps) \d+','',l).split()) for l in lines]
mismatches=[]
for i,(a,b) in enumerate(zip(responses['old'],responses['reuse'])):
 keys=[k for k in ['initial_sfen','history','weights','nodes_limit','cold_isready','state','command','bestmove'] if a[k]!=b[k]]
 if semantic(a['lines'])!=semantic(b['lines']):keys.append('info_except_time_NPS')
 if keys:mismatches.append(dict(query_index=i,fields=keys,old=a,reuse=b))
result=dict(status='PASS' if not mismatches else 'FAIL_RESPONSE_MATCH',groups=len(groups),actual_go=sum(len(v) for v in responses.values()),PV_move_checks=pv,seconds=time.perf_counter()-t0,price_acks=acks,mismatches=mismatches,scope=declaration['scope']);(O/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print({k:v for k,v in result.items() if k not in ['price_acks','mismatches']});assert not mismatches,'Response mismatch saved; diagnose, never claim equivalence'
