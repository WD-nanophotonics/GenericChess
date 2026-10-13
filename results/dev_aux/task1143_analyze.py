from pathlib import Path
import json,collections
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1143';O.mkdir(exist_ok=False);out=[]
for source,world in [(1118,'5x5'),(1138,'8x8')]:
 gs=[json.loads(x) for x in (R/f'results/dev_aux/task{source}/games.jsonl').read_text().splitlines()]
 for arm in ['J','L']:
  ys={}
  for p in [64,90,164,262,671]:
   js={}
   for opp in ['unit_search','uniform_random']:
    xx=[g for g in gs if g['arm']==arm and g['price']==p and g['opponent']==opp];js[opp]=F(sum((g['label']=='W')-(g['label']=='L') for g in xx),len(xx))
   ys[p]=(js['uniform_random'],js['unit_search']-js['uniform_random'])
  cuts={F(0),F(1)}
  for p,(a,b) in ys.items():
   for q,(c,d) in ys.items():
    if b!=d and 0<(t:=(c-a)/(b-d))<1:cuts.add(t)
  cuts=sorted(cuts);intervals=[]
  def at(w):
   vals={p:a+b*w for p,(a,b) in ys.items()};m=max(vals.values());return dict(w=str(w),all_best=[p for p,v in vals.items() if v==m],scores={p:str(v) for p,v in vals.items()})
  for lo,hi in zip(cuts,cuts[1:]):mid=(lo+hi)/2;intervals.append(dict(open_lo=str(lo),open_hi=str(hi),midpoint=at(mid)))
  out.append(dict(world=world,arm=arm,source=source,line_intercept_random_and_slope={p:[str(a),str(b)] for p,(a,b) in ys.items()},boundaries=[at(w) for w in cuts],open_segments=intervals,reference_weights=[at(F(9,20)),at(F(1,2)),at(F(11,20))]))
(O/'result.json').write_text(json.dumps(dict(status='EXACT_TRAIN_ONLY_OPPONENT_WEIGHT_UPPER_ENVELOPE',rows=out,new_games=0,new_go=0,scope='Posthoc sensitivityofexistingtrueoutcomes, notnewfit/changedtarget/independentvalidation. SeparateJ/L; fixedmainobjectivew=1/2 preserved. Allbestisfinite testedprices notcontinuouspriceinterval'),indent=2),encoding='utf-8')
for x in out:print(x['world'],x['arm'],[(r['open_lo'],r['open_hi'],r['midpoint']['all_best']) for r in x['open_segments']])
