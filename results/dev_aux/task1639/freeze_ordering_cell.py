from pathlib import Path
from itertools import product
from fractions import Fraction
import json
R=Path.cwd();O=R/'results/dev_aux/task1663';O.mkdir(exist_ok=False);features=list(product([-1,0,1],repeat=3));theta=(1728,720,720);cuts=set()
for a in features:
 for b in features:
  d=[x-y for x,y in zip(a,b)]
  if d[0]:
   q=Fraction(-d[1]*theta[1]-d[2]*theta[2],d[0])
   if 0<=q<=4096:cuts.add(q)
lo=max(q for q in cuts if q<theta[0]);hi=min(q for q in cuts if q>theta[0]);prices=[(int(lo+(hi-lo)/10),720,720),(int(lo+9*(hi-lo)/10),720,720)]
def signs(p):
 return [((sum(x*y for x,y in zip(a,p))-sum(x*y for x,y in zip(b,p)))>0)-((sum(x*y for x,y in zip(a,p))-sum(x*y for x,y in zip(b,p)))<0) for a in features for b in features]
base=signs(theta)
assert all(signs(p)==base for p in prices)
old=json.loads((R/'results/dev_aux/task1651/plan.json').read_bytes())
plan={'status':'FROZEN_EQUAL_ALL_MATERIAL_LEAF_ORDERING_BEFORE_QUERIES','features':features,'original':theta,'R_cell_open':[int(lo),int(hi)],'profiles':prices,'primary_preserved_ordering_pairs':len(base),'family_subset':[f for f in old['families'] if f['phase']=='DEV'][:64],'H':48,'seeds_per_color':4,'single_seconds':600,'max_new_go':50000,'expected_seconds':150,'scope':'All27materialdifferencevectors forglobal<=1eachR/N/B preservepairwiseleaforders/ties, no clamp. Anycompletefixeddepthminimax tree withthe same terminalscoreordering andpriceindependenttie rule hasidenticalchoices; matureselectivesearch numericthresholds neednot. ExposedDEVmechanism, no winner/humanfit ornewholdout.','counterfactual':'Compare actualcold64fullphysicalrandom/no-mateDraw atthese two parameterinteriorpoints to originalfixed1728. Differentchoicesalone notgain.','priorstudy':'task1651','binary':old['binary'],'binary_sha256':old['binary_sha256'],'variant_ini':old['variant_ini']}
(O/'plan.json').write_text(json.dumps(plan,indent=2));print('LEAF_ORDERING_CELL',plan['R_cell_open'],prices,'729pairwisesignsidentical')

