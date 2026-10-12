import sys,json,time,hashlib,re,os
from pathlib import Path
import cshogi as C
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task360'));sys.path.insert(0,str(R/'results/dev_aux/task364'));sys.path.insert(0,str(R/'results/dev_aux/task381'));import adapter as A;import run as G;import audit as V
O=R/'results/dev_aux/task402';O.mkdir(exist_ok=True);A.EXE=R/'.local_agent/yaneura26/yaneura-material1-cold-reuse.exe';source=R/'results/dev_aux/task387/queries.jsonl';groups={}
for line,text in enumerate(source.open(encoding='utf-8'),1):
 q=json.loads(text);key=tuple(q['weights'])
 if key not in groups:groups[key]=[(line,q),(line,q)]
 else:groups[key][1]=(line,q)
decl=dict(source_file='results/dev_aux/task387/queries.jsonl',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),executable_sha256=hashlib.sha256(A.EXE.read_bytes()).hexdigest(),pairs=[dict(weights=list(k),source_lines=[x[0] for x in v]) for k,v in groups.items()],selection='EVERYuniqueactualpricevector, its first andlastcomplete recordedquery; no label/successscreen, bothwithoriginal1024nodes/fullhistory/coldreset',cost='2go pervector, onefreshpriceprocess pervector, sequential;300secondfuse; no learning/refitting/humanselection');(O/'declaration.json').write_text(json.dumps(decl,indent=2),encoding='utf-8');rows=[];acks=[];t0=time.perf_counter();pv=0;calls=0
semantic=lambda lines:[' '.join(re.sub(r'\b(?:time|nps) \d+','',line).split()) for line in lines]
with (O/'queries.jsonl').open('w',encoding='utf-8') as journal:
 for wi,(w,pair) in enumerate(groups.items()):
  G.stop();assert time.perf_counter()-t0<300;e=A.Engine(w,journal)
  try:
   valid=0
   for line in e.prices:
    if not line.startswith('info string auxprice '):continue
    pc,val,signed,cap,prom=map(int,line.split()[3:]);pt=pc%16;base=pt-8 if 9<=pt<=14 else pt;assert val==w[pt] and signed==(1 if pc<16 else -1)*w[pt] and cap==(0 if pt in [0,8,15] else w[pt]+w[base]) and prom==(w[base+8]-w[base] if 1<=base<=6 else 0);valid+=1
   assert valid==32;acks.append(dict(weights=list(w),prices=e.prices))
   for line,old in pair:
    G.stop();new=e.search(old['initial_sfen'],old['history'],old['nodes_limit']);pv+=V.query(new)
    for k in ['initial_sfen','history','weights','nodes_limit','cold_isready','state','command','bestmove']:assert new[k]==old[k],(wi,line,k)
    assert semantic(new['lines'])==semantic(old['lines']),(wi,line,old['lines'],new['lines']);calls+=1;rows.append(dict(price_index=wi,source_query_line=line,actual_query_line=calls,fullinfo_equal_except_time_NPS=True))
  finally:e.close()
  if wi%20==0:print('qualified',wi+1,'of',len(groups),flush=True)
result=dict(status='PASS',price_vectors=len(groups),actual_go=calls,price_table_entries=32*len(groups),PV_move_checks=pv,seconds=time.perf_counter()-t0,rows=rows,scope='allactual387pricevectors first/laststate exactcold response, source/rawrefs preserved. Finite qualification notallhistory/default/NNUE/options guarantee; no duplicate learning');(O/'price_acks.json').write_text(json.dumps(acks,indent=2),encoding='utf-8');(O/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='rows'}))