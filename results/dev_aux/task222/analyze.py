import json,math,statistics
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task222';O.mkdir(exist_ok=True);X=json.loads((R/'results/dev_aux/task219/games.json').read_bytes());M=json.loads((R/'results/dev_aux/task218/models.json').read_bytes());D=json.loads((R/'results/dev_aux/task214/declaration.json').read_bytes());assert X['complete'];out=[]
def val(c):
 s=c['result']['score'];return [c['result']['reward'],(0 if s['winner'] is None else (1 if s['winner']==c['result']['agent_color'] else -1)) if s['terminal'] else s['quantity_difference']/15,s['quantity_difference']/15]
def dist(w):return statistics.mean(abs(math.log(w[k]/208/D['human_reference'][k])) for k in 'NBRQ')
for m in M['models']:
 name=f"s{m['seed']}-lambda{str(m['lambda_return']).replace('.','p')}";res=dict(seed=m['seed'],lambda_return=m['lambda_return'],prices={k:m['final_weights'][k]/208 for k in 'NBRQ'},initial_distance=dist(m['initial_weights']),final_distance=dist(m['final_weights']),opponents={})
 for opp in ('random','unit2ply'):
  pairs=[]
  for oi in range(8):
   a=[]
   for col in (True,False):
    base=next(c for c in X['calls'] if c['profile']==f"initial-s{m['seed']}" and c['opponent']==opp and c['opening_index']==oi and c['result']['agent_color']==col);end=next(c for c in X['calls'] if c['profile']==name and c['opponent']==opp and c['opening_index']==oi and c['result']['agent_color']==col);a.append([y-x for x,y in zip(val(base),val(end))])
   pairs.append(dict(root=oi,delta=[statistics.mean(x[j] for x in a) for j in range(3)]))
  delta=[statistics.mean(p['delta'][j] for p in pairs) for j in range(3)];loo=[[statistics.mean(p['delta'][j] for p in pairs if p['root']!=i) for j in range(3)] for i in range(8)];res['opponents'][opp]=dict(delta=dict(zip(('original','bounded','quantity'),delta)),root_pairs=pairs,leave_one_root_ranges={k:[min(v[j] for v in loo),max(v[j] for v in loo)] for j,k in enumerate(('original','bounded','quantity'))})
 out.append(res)
report=dict(complete=True,results=out,scope='All9lambda endpoints vs owninitial, fresh8pairedrootclusters. Familyexposeddevelopment, descriptivehumanreferenceonly; no modelselected or universalconvergence/strength claim.')
(O/'analysis.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps([dict(seed=r['seed'],lambda_return=r['lambda_return'],distance=r['final_distance'],delta={o:r['opponents'][o]['delta'] for o in r['opponents']}) for r in out],indent=2))
