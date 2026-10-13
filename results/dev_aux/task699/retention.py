import json,hashlib,time
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task699'
for n in [688,697]:assert json.loads((R/f'results/dev_aux/task{n}/result.json').read_bytes())['status'].startswith('PASS_ALL_')
models=[];inputs={};cells_by={}
def load(task,score):
 p=R/f'results/dev_aux/task{task}';r=json.loads((p/'result.json').read_bytes());gs=[json.loads(t) for t in (p/'games.jsonl').open(encoding='utf-8')];inputs[str(task)]=hashlib.sha256((p/'games.jsonl').read_bytes()).hexdigest();assert json.loads((R/f'results/dev_aux/task{score}/score_table_frozen.json').read_bytes())['source_sha256']==inputs[str(task)]
 return {name:[gs[s['line']-1] for s in row['batch']['sources']] for row in r['rows'] for name in row['names']}
a,b=load(687,689),load(696,698)
for start in ['unit','random2514']:
 aa=a[start+'-initial'];ba=b[start+'-initial'];assert len(aa)==len(ba)==32
 for x,y in zip(aa,ba):
  assert (x['replica'],x['root'],x['color'],x['weights'])==(y['replica'],y['root'],y['color'],y['weights']);assert x['actions']==y['actions'] and x['termination']==y['termination'] and x['quantity12']==y['quantity12'] and x['quantity24']==y['quantity24']
 method=[]
 for label,rows in [('A_mean12_24',a),('B_quantity12',b)]:
  cells=[]
  for x,y in zip(rows[start+'-initial'],rows[start+'-endpoint']):
   assert (x['replica'],x['root'],x['color'])==(y['replica'],y['root'],y['color']);g12=F(y['quantity12']-x['quantity12'],19);g24=F(y['quantity24']-x['quantity24'],19);cells.append(dict(replica=x['replica'],family=x['root']['source_family'],color=x['color'],g12=str(g12),g24=str(g24),minimum=str(min(g12,g24)),h12_positive=g12>0,h24_negative=g24<0,h24_nonpositive=g24<=0,late_negative_from_early_positive=g12>0 and g24<0))
  def stats(cc):
   m=sum(F(c['minimum']) for c in cc)/len(cc);avg=sum((F(c['g12'])+F(c['g24']))/2 for c in cc)/len(cc);pen=sum(abs(F(c['g12'])-F(c['g24']))/2 for c in cc)/len(cc);assert m==avg-pen
   return dict(cells=len(cc),M=str(m),mean_two_horizon_gain=str(avg),divergence_penalty=str(pen),g12=str(sum(F(c['g12']) for c in cc)/len(cc)),g24=str(sum(F(c['g24']) for c in cc)/len(cc)),both_nonnegative=sum(F(c['g12'])>=0 and F(c['g24'])>=0 for c in cc),negative_either=sum(F(c['minimum'])<0 for c in cc),early_positive=sum(c['h12_positive'] for c in cc),late_negative=sum(c['h24_negative'] for c in cc),early_positive_late_negative=sum(c['late_negative_from_early_positive'] for c in cc))
  method.append(dict(method=label,overall=stats(cells),by_replica=[dict(replica=r,**stats([c for c in cells if c['replica']==r])) for r in [0,1]],by_family=[dict(family=f,**stats([c for c in cells if c['family']==f])) for f in sorted({c['family'] for c in cells})],cells=cells))
 models.append(dict(start=start,methods=method,M_A_minus_B=str(F(method[0]['overall']['M'])-F(method[1]['overall']['M'])),same_actual_initial_all32cell_paths=True))
out=dict(status='ALL64_PAIRED_RETENTION_CELLS_AND_IDENTITY_PASS',models=models,source_sha256=inputs,new_games=0,new_go=0,scope='693post-A/exploratory/pre-B diagnostic on originalALL32devcells perstart. Cellmin beforemean, unchangedfitness, no early-positivefilter. Bothinitial physicalpaths exact across A/B onall32cells, timingexcluded. PositiveM difference notallfamily/negative-cell/universalvalueproof.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps([dict(start=m['start'],difference=m['M_A_minus_B'],methods=[dict(label=x['method'],**x['overall']) for x in m['methods']]) for m in models]))
