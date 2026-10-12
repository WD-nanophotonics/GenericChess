import json,sys,time,hashlib,re
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task360'));sys.path.insert(0,str(R/'results/dev_aux/task364'));sys.path.insert(0,str(R/'results/dev_aux/task381'));import adapter as A;import run as G;import audit as V
O=R/'results/dev_aux/task427';O.mkdir(exist_ok=True);cross=json.loads((R/'results/dev_aux/task425/result.json').read_text(encoding='utf-8'));cache={};groups={}
for row in cross['rows']:
 ref=row['source'];p=ref['file']
 if p not in cache:cache[p]=[json.loads(x) for x in (R/p).read_text(encoding='utf-8').splitlines()]
 g=cache[p][ref['line']-1];w=tuple(g['weights'])
 for qi,q in enumerate(g['queries']):
  if q['player']!='candidate':continue
  item=dict(game_source=ref,query_index=qi,initial_sfen=q['initial_sfen'],history=q['history'],weights=q['weights'])
  if w not in groups:groups[w]=[item,item]
  else:groups[w][1]=item
assert len(groups)==len(cross['profiles'])==6
exes={'old':R/'.local_agent/yaneura25/yaneura-material1-aux.exe','reuse':R/'.local_agent/yaneura26/yaneura-material1-cold-reuse.exe'}
decl=dict(question='Qualify experimentalcold-reuse at8192nodes before sameprofile budgetdiagnostic',pairs=[dict(weights=list(w),queries=qs) for w,qs in groups.items()],selection='ALL6 cross425frozenprofileprices, first&lastcandidatequeries acrossALL96declaredsourcecells; nooutcomes/successfilter;2coldqueries/vector/entry',nodes=8192,executable_hashes={k:hashlib.sha256(v.read_bytes()).hexdigest() for k,v in exes.items()},expected_cost='24actualgo, estimate<10s/120sfuse; no games/training',scope='finite8192qualification, not fulloptions/allhistories/deepNNUE guarantee');(O/'declaration.json').write_text(json.dumps(decl,indent=2),encoding='utf-8');responses={};acks=[];pv=0;t0=time.perf_counter();semantic=lambda lines:[' '.join(re.sub(r'\b(?:time|nps) \d+','',l).split()) for l in lines]
for arm,exe in exes.items():
 A.EXE=exe;rs=[]
 with (O/(arm+'_queries.jsonl')).open('w',encoding='utf-8') as qj:
  for w,qs in groups.items():
   G.stop();assert time.perf_counter()-t0<120;e=A.Engine(w,qj);acks.append(dict(arm=arm,weights=list(w),prices=e.prices))
   try:
    for q in qs:
     r=e.search(q['initial_sfen'],q['history'],8192);pv+=V.query(r);rs.append(r)
   finally:e.close()
 responses[arm]=rs
for a,b in zip(responses['old'],responses['reuse']):
 for key in ['initial_sfen','history','weights','nodes_limit','cold_isready','state','command','bestmove']:assert a[key]==b[key],key
 assert semantic(a['lines'])==semantic(b['lines']),(a['lines'],b['lines'])
out=dict(status='PASS',price_vectors=6,actual_go=sum(len(x) for x in responses.values()),PV_checks=pv,seconds=time.perf_counter()-t0,exact_response_except_time_NPS=True,price_acks=acks,scope=decl['scope']);(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print({k:v for k,v in out.items() if k!='price_acks'})
