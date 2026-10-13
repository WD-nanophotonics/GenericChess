from pathlib import Path
import json,collections,numpy as np,math
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task941';O.mkdir(exist_ok=False);gs=[json.loads(l) for l in (R/'results/dev_aux/task938/games.jsonl').open()];p=json.loads((R/'results/dev_aux/task936/endpoints.json').read_bytes());rows=[];pairs=[]
def st(g):
 t=g['termination'];return 'C' if t['kind'].startswith('cap') else 'D' if t['winner'] is None else 'W' if t['winner']==g['color'] else 'L'
def val(g):return 1 if st(g)=='W' else -1 if st(g)=='L' else 0
for phase in ['development','validation']:
 for opp in ['unit_search','uniform_random']:
  for price in p['profiles']:
   a=[g for g in gs if g['pool']==phase and g['opponent']==opp and g['weights'][5]==price];co=collections.Counter(map(st,a));score=str(F(sum(map(val,a)),len(a)));rows.append(dict(phase=phase,opponent=opp,price=price,N=len(a),counts=dict(co),J24=score))
  for base in [512,1448,4096]:
   a=[g for g in gs if g['pool']==phase and g['opponent']==opp and g['weights'][5]==base];b=[g for g in gs if g['pool']==phase and g['opponent']==opp and g['weights'][5]==128];assert [(g['root'],g['color']) for g in a]==[(g['root'],g['color']) for g in b];by=collections.defaultdict(list)
   for x,y in zip(a,b):by[x['root']['source_family']].append(val(y)-val(x))
   ids=sorted(by);v=np.array([float(sum(by[i])/len(by[i])) for i in ids]);rng=np.random.default_rng(2026149900);bm=v[rng.integers(0,len(v),(20000,len(v)))].mean(axis=1);lo,hi=np.quantile(bm,[.025,.975]);radius=math.sqrt(8*math.log(40)/len(v));mm=float(v.mean());pairs.append(dict(phase=phase,opponent=opp,base=base,candidate=128,Nfamilies=len(v),delta=str(F(sum(val(y)-val(x) for x,y in zip(a,b)),len(a))),transitions=dict(collections.Counter(st(x)+'->'+st(y) for x,y in zip(a,b))),family_deltas=[dict(seed=i,delta=str(F(sum(by[i]),len(by[i])))) for i in ids],descriptive_family_bootstrap95=[float(lo),float(hi)],unadjusted_distribution_free_Hoeffding95=[max(-2,mm-radius),min(2,mm+radius)],bootstrap_constant=bool(np.ptp(v)==0)))
out=dict(status='ALL352_STOCK_HELDOUT_OUTCOME_AND_FAMILY_UNCERTAINTY_REVIEW',rows=rows,pairs=pairs,new_go=0,scope='Allpredeclaredfourprices, exactsamefamilies/colors/RNG. Blockseedunit, colorsnotindependent. Bootstrap posthocdescriptive/notmultiplicityadjusted; constantbootstrapnotpopulationequivalence. Hoeffding assumes iidfamilydraws bounded[-2,2], conditionalgrammarandstockeligibility; nofullWDL/epsilonclaim.',handling_correction='First inlineanalysis hadsyntaxerror; earliercheckpoint prematurely named941 beforecreation. Actualsuccessfulanalysis recordednow, errornotresearchsuccess.');(O/'result.json').write_text(json.dumps(out,indent=2));print('ROWS',rows);print('PAIRS',[(x['phase'],x['opponent'],x['base'],x['delta'],x['descriptive_family_bootstrap95']) for x in pairs])
