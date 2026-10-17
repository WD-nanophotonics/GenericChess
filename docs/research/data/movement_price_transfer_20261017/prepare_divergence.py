from pathlib import Path
from collections import defaultdict
import sys,json,hashlib
R=Path.cwd();sys.path.insert(0,str(R));from tools.local_agent.common import write_json
D=R/'.local_agent/movement-transfer-20261017';p=json.loads((D/'plan.json').read_bytes());div=json.loads((D/'first-divergences.json').read_bytes())['rows'];chosen={}
for r in div:
 if r['comparison']not in ['static-fixed','static-free','free-fixed']:continue
 label=r['right']if r['comparison'].startswith('static')else r['left'];prefix='fixed5'if label.startswith('fixed5')else'free6';seed=int(label[len(prefix):]);key=r['comparison'],r['rule'],r['foe'],seed
 if key not in chosen:chosen[key]=dict(r,seed=seed)
allkeys=[(c,r,f,s)for c in ['static-fixed','static-free','free-fixed']for r in p['rules']for f in p['foes']for s in p['seeds']];missing=[x for x in allkeys if x not in chosen];roots={(r['rule'],r['family']):r for r in json.loads((D/'roots.json').read_bytes())['rows']};refs={}
for r in chosen.values():
 relative=r['absolute_ply']-roots[r['rule'],r['family']]['prefix_completed']
 for k in ['left','right']:refs[r[k+'_slot'],relative]=None
for line in (D/'queries.jsonl').open(encoding='utf-8'):
 q=json.loads(line);key=q['slot'],q['relative_ply']
 if key in refs:refs[key]=q
assert all(v is not None for v in refs.values())
selectedslots={r[k+'_slot']for r in chosen.values()for k in ['left','right']};records={}
for line in (D/'games.jsonl').open(encoding='utf-8'):
 g=json.loads(line)
 if g['slot']in selectedslots:records[g['slot']]=g['record']
rows=[]
for key in allkeys:
 if key not in chosen:continue
 r=chosen[key];rel=r['absolute_ply']-roots[r['rule'],r['family']]['prefix_completed'];record=dict(records[r['left_slot']]);record['actions']=record['actions'][:r['absolute_ply']]
 a=refs[r['left_slot'],rel];b=refs[r['right_slot'],rel];assert a['before_sha256']==b['before_sha256']and a['actor']==b['actor']==r['owner']
 rows.append(dict(r,left_query=a,right_query=b,parent_record=record))
write_json(D/'divergence-plan.json',dict(question='Are the FIRST fixed prespecified movement-transfer divergences genuine floating preferences or Native256 rounding/ties?',planned_groups=len(allkeys),limits=dict(cap_seconds=180,core_visits=1500000),selection='First record order per comparison/variant/fixedfoe/modelseed; no outcome/margin/mostdivergent selection. Missing groups stay missing without refilling roots/games.',scope='Posthoc mechanismcheck selectedwithoutoutcomelabels; exhaustiveCoreD2 forbothprofiles FLOAT andINT, no nativequery/newgame/fit. Limited384groups notall6669contexts or all-domainproof.'))
write_json(D/'divergence-inputs.json',dict(planned_groups=len(allkeys),returned=len(rows),missing=len(missing),missing_groups=missing,unique_query_refs=len(refs),rows=rows))
f=D/'divergence.py';t=f.read_text(encoding='utf-8');t=t.replace("planned=96,returned=len(rows),missing=96-len(rows)","planned=P['planned_groups'],returned=len(rows),missing=P['planned_groups']-len(rows)");t=t.replace('Onefirstdivergencepereach96comparison/rule/foe/seedgroup,125uniquerecordedqueryreferences','Firstavailabledivergenceper384declaredcomparison/variant/foe/seedgroups, absentgroupspreserved; exactqueryreferencecountininputs');t=t.replace('Notall6088contexts','Notall6669contexts');f.write_bytes(t.encode())
print('FIRST GROUPS',len(rows),'missing',len(missing),'refs',len(refs))
