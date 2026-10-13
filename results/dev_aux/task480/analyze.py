import json,time,sys,re,hashlib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task480';from fractions import Fraction
t0=time.perf_counter();r=json.loads((R/'results/dev_aux/task470/result.json').read_text(encoding='utf-8'));assert r['status']=='completed';rows=[];descriptors=[];ref=[0,90,315,405,495,855,990,540,0,540,540,540,540,945,1395,0];axes=[2,3,4,5,6,7,9,10,11,12,13,14];import math,statistics
for task,arm in [(468,'legacySEE'),(469,'handSEE')]:
 ep=json.loads((R/f'results/dev_aux/task{task}/endpoints.json').read_text(encoding='utf-8'))
 for p in ep['endpoints']:
  name=arm+'-trained-'+p['family'];descriptors.append(dict(arm=arm,family=p['family'],initial=p['initial'],endpoint=p['endpoint'],initial_log_ratio_MSE_to_source_prior=statistics.mean(math.log(p['initial'][a]/ref[a])**2 for a in axes),endpoint_log_ratio_MSE_to_source_prior=statistics.mean(math.log(p['endpoint'][a]/ref[a])**2 for a in axes)))
  for deploy in ['legacySEE','handSEE']:
   for env in ['unit','random']:
    a=sorted([x for x in r['rows'] if x['engine_arm']==deploy and x['opponent']==env and name+'-initial' in x['names']],key=lambda x:(x['root_index'],x['color']));b=sorted([x for x in r['rows'] if x['engine_arm']==deploy and x['opponent']==env and name+'-endpoint' in x['names']],key=lambda x:(x['root_index'],x['color']));assert len(a)==len(b)==8
    def metric(x,m):
     t=x['termination'];term=Fraction(0) if t['winner'] is None else Fraction(32 if t['winner']==x['color'] else -32);qty=Fraction(x['quantity'],19) if t['kind']=='cap24' else Fraction(0);assert term+qty==Fraction(x['goal']);return term+qty if m=='mixed' else term if m=='terminal' else term+(0 if t['winner'] is None else (1 if t['winner']==x['color'] else -1)*Fraction(24-x['plies'],24))
    for m in ['mixed','terminal','fast']:
     av=[metric(x,m) for x in a];bv=[metric(x,m) for x in b];diff=[y-x for x,y in zip(av,bv)];fam=[sum(diff[j:j+2])/2 for j in range(0,8,2)];rows.append(dict(train_engine=arm,start=p['family'],deployment_engine=deploy,opponent=env,metric=m,initial_mean=str(sum(av)/8),endpoint_mean=str(sum(bv)/8),gain=str(sum(diff)/8),paired_gains=list(map(str,diff)),root_family_gains=list(map(str,fam)),leave_one_family_gains=[str(sum(x for j,x in enumerate(fam) if i!=j)/3) for i in range(4)],initial_wins=sum(x['termination']['winner']==x['color'] for x in a),endpoint_wins=sum(x['termination']['winner']==x['color'] for x in b),initial_losses=sum(x['termination']['winner'] is not None and x['termination']['winner']!=x['color'] for x in a),endpoint_losses=sum(x['termination']['winner'] is not None and x['termination']['winner']!=x['color'] for x in b)))
qual=json.loads((R/'results/dev_aux/task479/result.json').read_text(encoding='utf-8'));assert qual['status']=='PASS';entries=0
for ack in qual['price_acks']:
 w=ack['weights'];seen=[]
 for line in ack['prices']:
  if not line.startswith('info string auxprice '):continue
  pc,val,sgn,cap,prom=map(int,line.split()[3:]);pt=pc%16;base=pt-8 if pt in range(9,15) else pt;assert val==w[pt] and sgn==(w[pt] if pc<16 else -w[pt]) and cap==(0 if pt in (0,8,15) else w[pt]+w[base]) and prom==(w[base+8]-w[base] if base in range(1,7) else 0);seen.append(pc);entries+=1
 assert sorted(seen)==list(range(32))
out=dict(status='PASS_DERIVATION',metrics=rows,source_prior_descriptors=descriptors,source_prior_scope='OfficialAperyWCSC26 sourceenum fixed c1b80eaa, NOTindependenthumanconsensus; readforALLdescriptiveendpoints onlyafter467fit/allcrossalreadyfrozen, neverfitness/selector/H/root/stop',source_prior=ref,new_go=0,additional_qualification_fulltable_entries=entries,seconds=time.perf_counter()-t0,scope='ALL4trained endpoints/BOTHengine implementations/BOTHopponents/threegoals, actualroot-family/leaveone; not newindependentholdout, unmodifiedmatureengine orgenericrule/humanprice recovery. Sourcepriordistance notoptimizationgoal.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps([x for x in rows if x['metric']=='mixed'],indent=2));print(descriptors)
