from pathlib import Path
import json,random,math
R=Path.cwd();O=R/'results/dev_aux/task1348';O.mkdir()
d=json.loads((R/'results/dev_aux/task1331/result.json').read_bytes());rows=[v for v in d['rows'] if v['weight']=='1/2']
vs=[[float(x) for x in r['family_deltas'].values()] for r in rows];means=[sum(v)/64 for v in vs];se=[(sum((x-m)**2 for x in v)/63/64)**.5 for v,m in zip(vs,means)];rng=random.Random(2026409500);stats=[]
for _ in range(10000):
 ids=rng.choices(range(64),k=64)
 stats.append(max(abs(sum(v[i] for i in ids)/64-m)/s if s else 0 for v,m,s in zip(vs,means,se)))
stats.sort();critical=stats[9499]
out=dict(status='POSTHOC_SIMULTANEOUS_PRIMARY_FOUR_CONTRAST_SENSITIVITY',critical=critical,rows=[dict(effect=r['effect'],mean=m,clusterSE=s,band=[m-critical*s,m+critical*s],nominal95=r['bootstrap95']) for r,m,s in zip(rows,means,se)],scope='Post-result multiplicity sensitivity; four primarymixed contrasts share family resampling, centered fixedSE maxT. Descriptive bootstrap assumption not exact familywise theorem; not predeclared adjusted significance or price refit.')
(O/'result.json').write_text(json.dumps(out,indent=2));print(out)
