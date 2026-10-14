from pathlib import Path
import json,random
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1557';O.mkdir(exist_ok=False);rows=json.loads((R/'results/dev_aux/task1555/result.json').read_bytes())['rows'];vectors={r['budget']:[float(F(r['family_deltas'][str(f)])) for f in range(128)] for r in rows};means={b:sum(v)/128 for b,v in vectors.items()};rng=random.Random(2026673500);mx=[]
for k in range(10000):
 ss=[rng.randrange(128) for j in range(128)];mx.append(max(abs(sum(v[i] for i in ss)/128-means[b]) for b,v in vectors.items()))
mx.sort();rad=mx[9499];out={'status':'COMPLETE_POLICY_TRANSFER_THREE_SHARED_FAMILY_BANDS','rows':rows,'simultaneous3_95':{b:[m-rad,m+rad] for b,m in means.items()},'canonical_primary':64,'scope':'128new fullrectangleD2color mixedKRvsKNfamilies, fixedprior1728 versus720; actualcompletecoldpolicy ALLlegal bestresponse, exactWDL.16/256frozen resourcecontrols, no bestbudget selection, stock+board+objective differfrom original3x3training.'};(O/'result.json').write_text(json.dumps(out,indent=2));print(out['simultaneous3_95'])
