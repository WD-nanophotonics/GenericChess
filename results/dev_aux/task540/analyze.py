import json,time,hashlib,math,statistics
from pathlib import Path
from fractions import Fraction
R=Path.cwd();O=R/'results/dev_aux/task540';d=json.loads((R/'results/dev_aux/task532/declaration.json').read_bytes());r=json.loads((R/'results/dev_aux/task537/result.json').read_bytes());assert r['status']=='completed';qual=json.loads((R/'results/dev_aux/task539/result.json').read_bytes());assert qual['status']=='PASS';t0=time.perf_counter();metrics=[];descriptors=[];ref=[0,90,315,405,495,855,990,540,0,540,540,540,540,945,1395,0];AX=d['axes'];nr=sum(f['phase']=='development' for f in d['roots']);N=2*nr
for condition in d['fit_conditions']:
 arm=condition['name'];ep=json.loads((R/f"results/dev_aux/task{condition['task']}/endpoints.json").read_bytes())
 for p in ep['endpoints']:
  name=arm+'-trained-'+p['family'];descriptors.append(dict(arm=arm,training_opponent=condition['opponent'],training_nodes=condition['nodes'],family=p['family'],initial=p['initial'],endpoint=p['endpoint'],initial_log_ratio_MSE_to_source_prior=statistics.mean(math.log(p['initial'][a]/ref[a])**2 for a in AX),endpoint_log_ratio_MSE_to_source_prior=statistics.mean(math.log(p['endpoint'][a]/ref[a])**2 for a in AX)))
  for budget in d['development_node_budgets']:
   for opponent in d['development_environments']:
    a=sorted([x for x in r['rows'] if x['nodes']==budget and x['opponent']==opponent and name+'-initial' in x['names']],key=lambda x:(x['root_index'],x['color']));b=sorted([x for x in r['rows'] if x['nodes']==budget and x['opponent']==opponent and name+'-endpoint' in x['names']],key=lambda x:(x['root_index'],x['color']));assert len(a)==len(b)==N
    def metric(x,m):
     t=x['termination'];terminal=Fraction(0) if t['winner'] is None else Fraction(32 if t['winner']==x['color'] else -32);quantity=Fraction(x['quantity'],19) if t['kind']=='cap24' else Fraction(0);assert terminal+quantity==Fraction(x['goal']);return terminal+quantity if m=='mixed' else terminal if m=='terminal' else terminal+(0 if t['winner'] is None else (1 if t['winner']==x['color'] else -1)*Fraction(24-x['plies'],24))
    for m in ['mixed','terminal','fast']:
     av=[metric(x,m) for x in a];bv=[metric(x,m) for x in b];diff=[y-x for x,y in zip(av,bv)];family=[sum(diff[i:i+2])/2 for i in range(0,N,2)];metrics.append(dict(train_engine=arm,training_opponent=condition['opponent'],training_nodes=condition['nodes'],start=p['family'],deployment_engine='warm_game',nodes=budget,opponent=opponent,metric=m,initial_mean=str(sum(av)/N),endpoint_mean=str(sum(bv)/N),gain=str(sum(diff)/N),paired_gains=list(map(str,diff)),root_family_gains=list(map(str,family)),leave_one_family_gains=[str(sum(x for j,x in enumerate(family) if i!=j)/(nr-1)) for i in range(nr)],initial_wins=sum(x['termination']['winner']==x['color'] for x in a),endpoint_wins=sum(x['termination']['winner']==x['color'] for x in b),initial_losses=sum(x['termination']['winner'] is not None and x['termination']['winner']!=x['color'] for x in a),endpoint_losses=sum(x['termination']['winner'] is not None and x['termination']['winner']!=x['color'] for x in b)))
entries=0
for ack in qual['price_acks']:
 w=ack['weights'];pcs=[]
 for line in ack['prices']:
  if not line.startswith('info string auxprice '):continue
  pc,value,sign,capture,prom=map(int,line.split()[3:]);pt=pc%16;base=pt-8 if pt in range(9,15) else pt;assert value==w[pt] and sign==(w[pt] if pc<16 else -w[pt]) and capture==(0 if pt in (0,8,15) else w[pt]+w[base]) and prom==(w[base+8]-w[base] if base in range(1,7) else 0);pcs.append(pc);entries+=1
 assert sorted(pcs)==list(range(32))
out=dict(status='PASS_ALL_METRICS',metrics=metrics,source_prior_descriptors=descriptors,source_prior=ref,source_prior_scope='OfficialAperyWCSC26 sourceenum c1b80eaa, NOTindependenthumanconsensus; ALL8endpoints andallcrossdevfreeze beforedescription. Neverfitness/selector/root/H/stop/modelcomparison winner.',additional_qualification_fulltable_entries=entries,new_go=0,seconds=time.perf_counter()-t0,scope='ALL4matchedfitconditions xBOTHinitials xBOTHdeploymentnodebudgets xBOTHopponents xTHREEmetrics with exactfractions/ALLrootfamily/leaveone. Unequalactualquery/cost/work curves, noequalcost/noisefreeCPU/Elo/globalidentifiability claim.')
(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(dict(status=out['status'],metric_rows=len(metrics),descriptive_endpoints=len(descriptors),additional_table_entries=entries)))
