import json,re,hashlib,time,sys
from pathlib import Path
from fractions import Fraction
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task381'));import audit as V
O=R/'results/dev_aux/task430';O.mkdir(exist_ok=True);datasets={n:json.loads((R/f'results/dev_aux/task{n}/result.json').read_text(encoding='utf-8')) for n in (425,428)};cache={}
def game(row):
 s=row['source'];p=s['file']
 if p not in cache:cache[p]=[json.loads(line) for line in (R/p).open(encoding='utf-8')]
 return cache[p][s['line']-1]
resources=[];transfer=[];cells=[]
for task,r in datasets.items():
 nodes=1024 if task==425 else 8192
 for env in ['unit','random']:
  rows=[x for x in r['rows'] if x['arm']==env];gs=[game(row) for row in rows];qs=[q for g in gs for q in g['queries']];counters=[]
  for q in qs:
   lines=[l for l in q['lines'] if re.search(r'\bnodes (\d+)',l)]
   if lines:counters.append(int(re.search(r'\bnodes (\d+)',lines[-1]).group(1)))
  resources.append(dict(nodes=nodes,env=env,games=len(gs),actual_go=len(qs),actual_plies=sum(len(g['actions']) for g in gs),true_terminals=sum(g['termination']['kind']!='cap24' for g in gs),wins=sum(g['termination']['winner']==g['color'] for g in gs),losses=sum(g['termination']['winner'] is not None and g['termination']['winner']!=g['color'] for g in gs),gamewall_sum=sum(g['seconds'] for g in gs),reported_lastinfo_nodes_sum=sum(counters),reported_node_range=[min(counters),max(counters)],unreported_node_queries=len(qs)-len(counters),scope='425logical96 reuses64actual418/419games, distinctphysicalcounts separate; cold fullprotocol gamewall includesbothplayers. Transportmonotonic timercoarse, notpureCPU/equaltime'))
  for trainarm in ['unit','random']:
   for start in ['unit','random2514']:
    label=trainarm+'-trained-'+start;initial=sorted([x for x in rows if label+'-initial' in x['names']],key=lambda x:(x['root_index'],x['color']));endpoint=sorted([x for x in rows if label+'-endpoint' in x['names']],key=lambda x:(x['root_index'],x['color']));assert len(initial)==len(endpoint)==8;pairs=[Fraction(b['goal'])-Fraction(a['goal']) for a,b in zip(initial,endpoint)];families=[sum(pairs[i:i+2])/2 for i in range(0,8,2)]
    transfer.append(dict(nodes=nodes,environment=env,train_opponent=trainarm,start=start,initial_mean=str(sum(Fraction(x['goal']) for x in initial)/8),endpoint_mean=str(sum(Fraction(x['goal']) for x in endpoint)/8),gain=str(sum(pairs)/8),family_gains=[str(x) for x in families],leave_one_family_gains=[str(sum(v for j,v in enumerate(families) if j!=i)/3) for i in range(4)]))
  for root in range(4):
   for c in (0,1):
    rr=[x for x in rows if x['root_index']==root and x['color']==c];assert len(rr)==6;outcomes=[('unfinished' if x['termination']['kind']=='cap24' else 'draw' if x['termination']['winner'] is None else 'win' if x['termination']['winner']==c else 'loss') for x in rr]
    cells.append(dict(nodes=nodes,environment=env,root=root,color=c,outcomes=outcomes,terminal_response=len(set(outcomes))>1,allwin_saturated=all(x=='win' for x in outcomes),goal_response=len({x['goal'] for x in rr})>1))
physical_games=0;physical_go=24;totalwall=0
for task in (406,411,412,418,419,421,425,428):
 r=json.loads((R/f'results/dev_aux/task{task}/result.json').read_text(encoding='utf-8'));physical_games+=r.get('new_games',r.get('games',0));physical_go+=r.get('new_go',r.get('actual_go',0))
ackcount=0
for task,field in [(411,'price_acknowledgements'),(412,'price_acknowledgements'),(421,'prices'),(425,'price_acks'),(428,'price_acks'),(427,'price_acks')]:
 r=json.loads((R/f'results/dev_aux/task{task}/result.json').read_text(encoding='utf-8'))
 for a in r[field]:
  w=a['weights'];pcs=[]
  for line in a['prices']:
   if not line.startswith('info string auxprice '):continue
   pc,val,sgn,cap,prom=map(int,line.split()[3:]);pt=pc%16;base=pt-8 if pt in range(9,15) else pt;assert val==w[pt] and sgn==(1 if pc<16 else -1)*w[pt] and cap==(0 if pt in (0,8,15) else w[pt]+w[base]) and prom==(w[base+8]-w[base] if base in range(1,7) else 0);pcs.append(pc);ackcount+=1
  assert sorted(pcs)==list(range(32))
qualified=[]
for arm in ('old','reuse'):
 qs=[json.loads(x) for x in (R/f'results/dev_aux/task427/{arm}_queries.jsonl').open(encoding='utf-8')];assert len(qs)==12;qualified.append(dict(arm=arm,queries=len(qs),PV_move_checks=sum(V.query(q) for q in qs)))
out=dict(status='PASS',resources=resources,transfer=transfer,cells=cells,physical_new_games=physical_games,physical_actual_go=physical_go,auxsee_calls=546,additional_fulltable_ack_entries=ackcount,standalone_qualification=qualified,scope='Allfixedprofiles/budgets no re-fitting orhorizon/price/budget selector. Actualresource/resultcurve notequal-time or machineexclusive. One fixedrandomcondition; oldcaps/failures unchanged. Extra8192work doesnotbyitself solvehumanprice identification');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k not in ['cells','qualified']},indent=2))
