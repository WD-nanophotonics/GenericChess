
from pathlib import Path
from fractions import Fraction as F
import json,collections
R=Path.cwd();O=R/'results/dev_aux/task1202';O.mkdir(exist_ok=False);D=json.loads((R/'results/dev_aux/task1201/plan.json').read_bytes());out=[]
for source in D['sources']:
 gs=[json.loads(s) for s in (R/f'results/dev_aux/task{source}/games.jsonl').read_text().splitlines()]
 gs=[g for g in gs if (g['root']['composition_ordinal']<4 if source==1154 else g['arm']=='J' and g['price']==720)]
 def x(g):return [F(sum(1 if c==g['color'] else -1 for t2,c in zip(g['root']['types'],g['root']['colors']) if t2==t)) for t in [4,2]]
 gram=None;coef={}
 for opp in ['unit_search','uniform_random']:
  ss=[g for g in gs if g['opponent']==opp];xx=[x(g) for g in ss];yy=[F((g['label']=='W')-(g['label']=='L')) for g in ss]
  assert [sum(q[i] for q in xx) for i in range(2)]==[0,0]
  a=[[sum(q[i]*q[j] for q in xx)/len(xx) for j in range(2)] for i in range(2)];z=[sum(q[i]*y for q,y in zip(xx,yy))/len(xx) for i in range(2)]
  if gram is None:gram=a
  else:assert a==gram
  det=a[0][0]*a[1][1]-a[0][1]*a[1][0];assert det
  b=[(z[0]*a[1][1]-z[1]*a[0][1])/det,(z[1]*a[0][0]-z[0]*a[1][0])/det];coef[opp]=b
 rows=[]
 for w in map(F,D['weights']):
  b=[w*coef['unit_search'][i]+(1-w)*coef['uniform_random'][i] for i in range(2)];rows.append(dict(search_weight=str(w),coef=list(map(str,b)),positive_ratio=str(b[0]/b[1]) if all(v>0 for v in b) else None))
 out.append(dict(source=source,N=len(gs),gram=[[str(v) for v in row] for row in gram],endpoint_coefficients={o:list(map(str,b)) for o,b in coef.items()},rows=rows,root_color_stock_balancing_exact=True))
(O/'result.json').write_text(json.dumps(dict(status='EXACT_OBSERVATIONAL_NU_WEIGHT_CURVES_NO_RESELECTION',rows=out,new_go=0,scope='C/Dlabelzero remainfiniteH24, sameπ differentν; no humanprior/positiveclipping/favorableweightselection orpolicydeployment.'),indent=2));print(out)
