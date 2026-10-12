import json,sys,time,hashlib
from pathlib import Path
from fractions import Fraction
R=Path.cwd();O=R/'results/dev_aux/task448';O.mkdir(exist_ok=True);rows=[];t0=time.perf_counter()
r=json.loads((R/'results/dev_aux/task434/result.json').read_text(encoding='utf-8'))
for label in ['random1024','random8192']:
 ep=json.loads((R/f'results/dev_aux/task{432 if label=="random1024" else 433}/endpoints.json').read_text(encoding='utf-8'))
 for p in ep['endpoints']:
  prefix=label+'-trained-'+p['family']
  for budget in (1024,8192):
   for env in ('unit','random'):
    a=sorted([x for x in r['rows'] if x['nodes']==budget and x['opponent']==env and prefix+'-initial' in x['names']],key=lambda x:(x['root_index'],x['color']));b=sorted([x for x in r['rows'] if x['nodes']==budget and x['opponent']==env and prefix+'-endpoint' in x['names']],key=lambda x:(x['root_index'],x['color']));assert len(a)==len(b)==8;diff=[Fraction(y['goal'])-Fraction(x['goal']) for x,y in zip(a,b)];fam=[sum(diff[i:i+2])/2 for i in range(0,8,2)]
    def parts(x):
     term=x['termination'];pure=Fraction(0) if term['winner'] is None else Fraction(32 if term['winner']==x['color'] else -32);qty=Fraction(x['quantity'],19) if term['kind']=='cap24' else Fraction(0);assert pure+qty==Fraction(x['goal']);return pure,qty
    ta,qa=zip(*map(parts,a));tb,qb=zip(*map(parts,b));terminal=sum(tb)/8-sum(ta)/8;qty=sum(qb)/8-sum(qa)/8;assert terminal+qty==sum(diff)/8
    rows.append(dict(train_nodes=int(label[6:]),family=p['family'],development_nodes=budget,opponent=env,initial_mean=str(sum(Fraction(x['goal']) for x in a)/8),endpoint_mean=str(sum(Fraction(x['goal']) for x in b)/8),gain=str(sum(diff)/8),terminal_component_gain=str(terminal),quantity_component_gain=str(qty),paired_gains=[str(x) for x in diff],root_family_gains=[str(x) for x in fam],leave_one_family_gains=[str(sum(x for j,x in enumerate(fam) if j!=i)/3) for i in range(4)],initial_true_wins=sum(x['termination']['winner']==x['color'] for x in a),endpoint_true_wins=sum(x['termination']['winner']==x['color'] for x in b),initial_true_losses=sum(x['termination']['winner'] is not None and x['termination']['winner']!=x['color'] for x in a),endpoint_true_losses=sum(x['termination']['winner'] is not None and x['termination']['winner']!=x['color'] for x in b),changed_axes=sum(u!=v for u,v in zip(p['initial'],p['endpoint']))))
out=dict(status='PASS_DERIVATION',rows=rows,new_go=0,seconds=time.perf_counter()-t0,scope='ALLfour endpoints/BOTHnodes/BOTHopponents, aliasesretainunchangedendpoint, exactrule/quantity/family components. Budgetspecialization/interaction ratherthanunique shallow-error correction; unitopponent search alsochangesnodes. Random branch fixedopponentpolicy, but trajectories/terminal availability change. No samplingCI, model/node/price selector.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(rows,indent=2))
