import json,time,sys,hashlib
from pathlib import Path
from fractions import Fraction as F
import cshogi as C
R=Path.cwd();O=R/'results/dev_aux/task588';O.mkdir(exist_ok=True);start=time.perf_counter();sys.path.insert(0,str(R/'results/dev_aux/task381'));import audit as V
src=(R/'results/dev_aux/task570/analyze.py').read_text();exec(compile(src[src.index('def prefix('):src.index('cache={}')],'original570prefix','exec'))
old=json.loads((R/'results/dev_aux/task556/result.json').read_bytes());new=json.loads((R/'results/dev_aux/task567/result.json').read_bytes());cells=[]
for task,res,route in [(556,old,'pure24'),(567,new,'mixed12')]:
 gs=[json.loads(x) for x in (R/f'results/dev_aux/task{task}/games.jsonl').open()]
 for row in res['rows']:cells.append(dict(route=route,names=row['names'],opponent=row['opponent'],games=[gs[s['line']-1] for s in row['batch']['sources']],sources=row['batch']['sources']))
cache={}
for cell in cells:
 for H in [12,24]:cache[(cell['route'],tuple(cell['names']),cell['opponent'],H)]=[prefix(g,H) for g in cell['games']]
rows=[];summ=[]
for route,tasks in [('pure24',[(554,'unit'),(555,'random')]),('mixed12',[(565,'unit'),(566,'random')])]:
 for task,opp in tasks:
  ep=json.loads((R/f'results/dev_aux/task{task}/endpoints.json').read_bytes())
  for e in ep['endpoints']:
   name=opp+'-'+e['family']
   for env in ['unit','random']:
    ai=next(c for c in cells if c['route']=='pure24' and c['opponent']==env and name+'-initial' in c['names']);bi=next(c for c in cells if c['route']==route and c['opponent']==env and name+'-endpoint' in c['names']);vals=[]
    for i in range(32):
     a12,b12=[cache[(x['route'],tuple(x['names']),env,12)][i] for x in [ai,bi]];a24,b24=[cache[(x['route'],tuple(x['names']),env,24)][i] for x in [ai,bi]];assert a12['root']==b12['root']==a24['root']==b24['root'] and a12['color']==b12['color']==a24['color']==b24['color'];mix=b12['mixed']-a12['mixed'];terminal12=b12['terminal']-a12['terminal'];quantity=mix-terminal12;later=b24['terminal']-a24['terminal'];assert mix==terminal12+quantity
     row=dict(route=route,training_opponent=opp,start=e['family'],evaluation_opponent=env,root=a12['root'],color=a12['color'],initial_source=ai['sources'][i],endpoint_source=bi['sources'][i],H12_mixed_gain=str(mix),H12_terminal_gain=str(terminal12),H12_unfinished_quantity_gain=str(quantity),H24_terminal_gain=str(later),initial_H12=a12['status'],endpoint_H12=b12['status'],initial_H24=a24['status'],endpoint_H24=b24['status'],quantity_positive_later_worse=(mix>0 and quantity>0 and later<0),both_H24_unfinished=a24['status']==b24['status']=='UNFINISHED',H24_information=a24['status']!='UNFINISHED' or b24['status']!='UNFINISHED');rows.append(row);vals.append(row)
    fam=[]
    for fi in range(16):
     v=vals[2*fi:2*fi+2];assert v[0]['root']==v[1]['root'];fam.append(dict(root=v[0]['root'],H12_mixed=str(sum(F(x['H12_mixed_gain']) for x in v)/2),H12_terminal=str(sum(F(x['H12_terminal_gain']) for x in v)/2),H12_quantity=str(sum(F(x['H12_unfinished_quantity_gain']) for x in v)/2),H24_terminal=str(sum(F(x['H24_terminal_gain']) for x in v)/2),quantity_positive_later_worse=sum(x['quantity_positive_later_worse'] for x in v),H24_information=sum(x['H24_information'] for x in v)))
    def stats(v):return dict(cells=len(v),H12_mixed=str(sum(F(x['H12_mixed_gain']) for x in v)/len(v)),H12_quantity=str(sum(F(x['H12_unfinished_quantity_gain']) for x in v)/len(v)),H12_terminal=str(sum(F(x['H12_terminal_gain']) for x in v)/len(v)),H24_terminal=str(sum(F(x['H24_terminal_gain']) for x in v)/len(v)),quantity_positive_later_worse=sum(x['quantity_positive_later_worse'] for x in v),quantity_positive_cells=sum(F(x['H12_mixed_gain'])>0 and F(x['H12_unfinished_quantity_gain'])>0 for x in v),both_H24_unfinished=sum(x['both_H24_unfinished'] for x in v),H24_information=sum(x['H24_information'] for x in v))
    summ.append(dict(route=route,training_opponent=opp,start=e['family'],evaluation_opponent=env,all=stats(vals),families=fam,leave_one=[dict(omit=f['root'],**stats([x for x in vals if x['root']!=f['root']])) for f in fam]))
assert len(rows)==512 and len(summ)==16
out=dict(status='PASS_ALL_PAIRED',rows=rows,summaries=summ,all_cells=512,quantity_positive_later_worse=sum(x['quantity_positive_later_worse'] for x in rows),quantity_positive_cells=sum(F(x['H12_mixed_gain'])>0 and F(x['H12_unfinished_quantity_gain'])>0 for x in rows),both_H24_unfinished=sum(x['both_H24_unfinished'] for x in rows),H24_information=sum(x['H24_information'] for x in rows),seconds=time.perf_counter()-start,new_go=0,scope='ALL8actualendpoints/correspondinginitials/BOTHfixedopponents/SAMEroot+color paired H24physicalpaths andH12prefix; unfinished0onlycensoredterminalscoreNOTdraw/final0. Sourcefreedescription; notcounterfactualH12training, repeatedcells/not512independentfamilies. No claimquantityalone explains pure24failure.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k not in ['rows','summaries']}));print(json.dumps([dict(route=x['route'],train=x['training_opponent'],start=x['start'],eval=x['evaluation_opponent'],**x['all']) for x in summ]))