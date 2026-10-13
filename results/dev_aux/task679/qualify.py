import json,sys,time,re,hashlib,copy
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task679';d=json.loads((R/'results/dev_aux/task675/deployment_declaration.json').read_bytes());start=time.monotonic();deadline=start+60
for n in [360,364,381,509]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
from warm_adapter import ControlledEngine
sys.path.insert(0,str(R/'results/dev_aux/task583'));from controller_curriculum import native_game
A.EXE=R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe';source={}
for i,s in enumerate((R/'results/dev_aux/task676/games.jsonl').open(encoding='utf-8'),1):
 g=json.loads(s)
 if g['replica']==0 and g['profile']==0:source[(g['root']['index'],g['color'])]=(g,i)
def semq(q):
 x=copy.deepcopy(q);x.pop('seconds',None);x['lines']=[re.sub(r'\b(?:nps|time) \d+',lambda m:m[0].split()[0]+' OMIT',a) for a in x['lines']];return x
rows=[];go=0;pv=0
with (O/'queries.jsonl').open('w') as qj,(O/'games.jsonl').open('w') as gj:
 e=ControlledEngine(d['profiles'][0]['weights'],qj,'warm_game');acks=[dict(weights=e.w,prices=e.prices)]
 try:
  for f in d['roots']:
   for color in [0,1]:
    e.begin_game();g=native_game(e,None,e.w,f,color,None,dict(cap=12,nodes=1024,seed_base=d['seed_bases'][0]),deadline);gj.write(json.dumps(g)+'\n');old,line=source[(f['index'],color)];n=min(12,len(old['actions']));assert g['actions']==old['actions'][:n];oq=[q for q in old['queries'] if q['ply']<n];assert [semq(q) for q in g['queries']]==[semq(q) for q in oq];assert len(g['actions'])==n;go+=len(g['queries']);pv+=sum(V.query(q) for q in g['queries']);rows.append(dict(root=f['index'],color=color,H24_source_line=line,H12_actual_source_line=len(rows)+1,actual_queries=len(g['queries']),all_non_time_queries_and_actions_exact=True))
 finally:e.close()
out=dict(status='ALL32_ACTUAL_H12_VS_H24_PREFIX_PAIRS_EXACT',actual_games=len(rows),actual_go=go,legal_PV_moves=pv,rows=rows,price_acks=acks,seconds=time.monotonic()-start,scope='ActualH12warm1024uniformrandom onALL16newroots/bothcolors unitprice/firstfreshRNG, first12H24fullhistory/actions/query/pv/work/state exactexcludingtime/nps/seconds ONLY. Additional32physicalqualificationgames areNEW andnotalreadycachedprefix. Finitecontrolbounds observedcap-independence, notallprices/horizons proof. All384H12prefix scoredseparatelyliteral677678fullrule replay; newqualification neitherfit/newmodel norhumanrecovery.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:out[k] for k in ['status','actual_games','actual_go','legal_PV_moves','seconds']}))
