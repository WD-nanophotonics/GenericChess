"""Read frozen scheduling evidence; no search calls or archive extraction."""
import hashlib, io, json, subprocess, zipfile
from pathlib import Path
REV='313900d3b5c0d9d79a117306ecf30cf6078dba43'
INDEX='docs/research/data/physical_publication_20261011.json'
PREFIX='.local_agent/physical-publication-20261011/'
B=Path(__file__).parent

def sha(raw): return hashlib.sha256(raw).hexdigest()
def git(path): return subprocess.check_output(['git','show',REV+':'+path])
ib=git(INDEX); index=json.loads(ib); raw=git(index['archive']['path'])
assert len(raw)==index['archive']['bytes'] and sha(raw)==index['archive']['sha256']
z=zipfile.ZipFile(io.BytesIO(raw)); members={m['path']:m for m in index['members']}; selected={}
def read(name):
 path=PREFIX+name; data=z.read(path); m=members[path]
 assert len(data)==m['bytes'] and sha(data)==m['sha256'],path
 selected[path]=m
 return json.loads(data) if name.endswith('.json') else data.decode()

def arm_record(a):
 d=a['decision'];s=a['stats']
 for k in ('nodes','qnodes','completed_depth','termination_reason','native_legality_calls','native_legality_fallbacks','native_legality_operational_failures'):
  assert d[k]==s[k],k
 assert a.get('restored_actual_multiset',a.get('actual_root_restored')),list(a)
 assert s['runtime_depth_balanced'] and s['runtime_pushes']==s['runtime_pops']
 assert s['native_legality_calls']>0 and s['native_legality_fallbacks']==s['native_legality_operational_failures']==0
 return {**{k:a[k] for k in ('pvs','aspiration','mode','mask_bound_depth') if k in a},**{k:d[k] for k in ('action','score','completed_depth','nodes','qnodes','termination_reason','result_source','result_ordinary_qdepth','result_check_hard_qdepth')},'work':d['nodes']+d['qnodes'],'runtime_pushes':s['runtime_pushes'],'native_calls':s['native_legality_calls'],'native_enabled':s['native_legality_enabled'],'wall':a.get('wall_observation',a.get('observed_choose_wall'))}

studies={}
for stem in ('pvs-caller','pvs-node','pvs-time','pvs-reference','pvs-tt-reference','aspiration','aspiration-samephase','aspiration-node'):
 v=read(stem+'-result.json');assert v['complete'];rows=[]
 for c in v['cells']:
  assert len(c['arms'])==2
  arms=[arm_record(a) for a in c['arms']]
  rows.append({'condition':c.get('spec',{k:c[k] for k in ('root','seconds','order','tt') if k in c}),'arms':arms,'same_action':arms[0]['action']==arms[1]['action'],'same_score':arms[0]['score']==arms[1]['score'],'same_completed_depth':arms[0]['completed_depth']==arms[1]['completed_depth'],'same_retained_q':arms[0]['result_ordinary_qdepth']==arms[1]['result_ordinary_qdepth']})
 studies[stem]=rows
 if stem!='pvs-time':read(stem+'-declaration.json')
read('pvs-time-declaration.json');read('pvs-time-cost-correction.json')
assert len(studies['pvs-time'])==20 and all(r['same_action'] and r['same_score'] and r['same_completed_depth'] and r['same_retained_q'] for r in studies['pvs-time'])
for root in ('chess-middle','chess-ep'):
 for budget in (.05,.1,1,4,8):
  cells=[r for r in studies['pvs-time'] if r['condition']['root']==root and r['condition']['seconds']==budget]
  assert len(cells)==2 and {tuple(r['condition']['order']) for r in cells}=={(False,True),(True,False)}
for stem in ('pvs-caller','pvs-reference','pvs-tt-reference','aspiration','aspiration-samephase'):
 assert all(r['same_action'] and r['same_score'] and r['same_completed_depth'] for r in studies[stem])
out={'complete':True,'revision':REV,'index':INDEX,'index_sha256':sha(ib),'archive':index['archive'],'selected_members':selected,'studies':studies,'recorded_call_count':sum(len(r['arms']) for rows in studies.values() for r in rows),'scope':'Existing records only, not independent execution. Positive provider calls/zero fallbacks and Runtime balance checked. No exact fresh-horizon, holdout, WDL or default deployment claim.'}
(B/'scheduling.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
print('verified',out['recorded_call_count'],'recorded calls;20opposite-order time pairs unchanged')
