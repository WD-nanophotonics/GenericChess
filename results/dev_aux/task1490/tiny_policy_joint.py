from pathlib import Path
import json,random
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1529';O.mkdir(exist_ok=False);rows=json.loads((R/'results/dev_aux/task1512/result.json').read_bytes())['rows']+json.loads((R/'results/dev_aux/task1517/result.json').read_bytes())['rows'];rows.sort(key=lambda r:r['budget']);families=sorted(int(s) for s in rows[0]['family_deltas']);vectors={r['budget']:[float(F(r['family_deltas'][str(s)])) for s in families] for r in rows};means={b:sum(v)/64 for b,v in vectors.items()};rng=random.Random(2026650500);mx=[]
for _ in range(10000):
 ss=[rng.randrange(64) for i in range(64)];draw={b:sum(v[i] for i in ss)/64 for b,v in vectors.items()};mx.append(max(abs(draw[b]-means[b]) for b in means))
mx.sort();radius=mx[9499];out={'status':'THREE_FULL_POLICY_RESOURCE_GAINS_SHARED_FAMILY_SIMULTANEOUS_BANDS','rows':rows,'simultaneous3_95_centered_maxT':{b:[v-radius,v+radius] for b,v in means.items()},'radius':radius,'scope':'FixedTRAINselected1728/baseline720, same64fullorbits allthreebudgets. Fullcoldpolicy vsalllegalperfectbestresponse WDL; 16primary plus64/256 addedresourcecontrols frozenbeforefullpolicy results. Descriptive jointbootstrap, not game/sideindependence or universalhumanratio. Boundary2.4 retained.'};(O/'result.json').write_text(json.dumps(out,indent=2));print(out['simultaneous3_95_centered_maxT'])
