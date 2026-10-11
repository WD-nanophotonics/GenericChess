"""Independent frozen-record verification; never runs search or extracts archives."""
import hashlib, io, json, subprocess, zipfile
from pathlib import Path
REV='d4a588fe50a5f90c0ad5026f28f02905ee86ed65'
INDEX='docs/research/data/q4_caller_20261011.json'
PREFIX='.local_agent/q4-caller-attribution-20261011/'
B=Path(__file__).parent

def sha(b): return hashlib.sha256(b).hexdigest()
def git(p): return subprocess.check_output(['git','show',REV+':'+p])
ib=git(INDEX); index=json.loads(ib); raw=git(index['archive']['path'])
assert len(raw)==index['archive']['bytes'] and sha(raw)==index['archive']['sha256']
z=zipfile.ZipFile(io.BytesIO(raw)); members={m['path']:m for m in index['members']}; selected={}
def read(name):
 p=PREFIX+name; b=z.read(p); m=members[p]
 assert len(b)==m['bytes'] and sha(b)==m['sha256'],p
 selected[p]=m
 return json.loads(b) if name.endswith('.json') else b.decode()

DK=('action','score','completed_depth','result_source','result_ordinary_qdepth','result_check_hard_qdepth','termination_reason','nodes','qnodes')
SK=('runtime_pushes','native_legality_calls','native_legality_actions','evaluation_calls','legal_actions_generated')
def verify(r):
 d=r['decision']; s=r['stats']; native=r['native_requested']
 assert r['actual_root_restored'] and r['public_action_legal']
 assert s['runtime_depth_balanced'] and s['runtime_pushes']==s['runtime_pops']
 assert s['native_legality_fallbacks']==s['native_legality_operational_failures']==0
 assert bool(s['native_legality_enabled'])==native
 assert (s['native_legality_calls']>0)==native
 for k in set(d)&set(s): assert d[k]==s[k],k
 visits=d['nodes']+d['qnodes']; assert visits>0
 return {**{k:r[k] for k in ('root','seconds','order','native_requested','tt','ruleset_fingerprint','adapter') if k in r},**{k:d[k] for k in DK},**{k:s[k] for k in SK},'q_fraction_of_visits':d['qnodes']/visits,'physical_pushes_per_visit':s['runtime_pushes']/visits,'wall':r['wall'],'setup_seconds':r.get('setup_seconds',0)}

studies={}
for stem,count in [('capability',32),('generic-capability',24),('mixed-postfix-capability',8)]:
 v=read(stem+'-result.json'); assert v['complete'] and len(v['rows'])==count
 rows=[verify(r) for r in v['rows']]; pairs=[]
 keys=sorted({(r['root'],r['seconds'],r['order']) for r in rows})
 assert len(keys)*2==count
 for root,sec,order in keys:
  arms=[r for r in rows if (r['root'],r['seconds'],r['order'])==(root,sec,order)]
  assert len(arms)==2 and {a['native_requested'] for a in arms}=={False,True}
  arms.sort(key=lambda a:a['native_requested']); core,native=arms
  pairs.append({'root':root,'seconds':sec,'order':order,'core_depth':core['completed_depth'],'native_depth':native['completed_depth'],'core_q':core['result_ordinary_qdepth'],'native_q':native['result_ordinary_qdepth'],'same_action':core['action']==native['action'],'same_score':core['score']==native['score'],'semantically_comparable':not(stem=='generic-capability' and root.startswith('mixed-'))})
 for root,sec in {(p['root'],p['seconds']) for p in pairs}:
  assert {p['order'] for p in pairs if p['root']==root and p['seconds']==sec}=={0,1}
 totals={k:sum(r[k] for r in rows) for k in ('nodes','qnodes',*SK,'wall','setup_seconds')}
 studies[stem]={'rows':rows,'pairs':pairs,'totals':totals}
 assert all(p['same_action'] for p in pairs if p['semantically_comparable'])
for stem in ['mixed-discrepancy','mixed-postfix']:
 v=read(stem+'-result.json'); assert v['complete'] and len(v['rows'])==4
 rows=[verify(r) for r in v['rows']]
 for tt in [False,True]:
  pair=sorted([r for r in rows if r['tt']==tt],key=lambda r:r['native_requested']); assert len(pair)==2
  assert all(r['completed_depth']==4 and r['termination_reason']=='completed_depth' for r in pair)
  if stem=='mixed-postfix':
   for k in ('action','score','nodes','qnodes','runtime_pushes'): assert pair[0][k]==pair[1][k],k
  else: assert pair[0]['score']==4557 and pair[1]['score']==3921
 studies[stem]={'rows':rows}
f=read('mixed-postfix-frontier-result.json')
assert f['complete'] and f['actual_root_restored'] and f['checked_frontiers']==2000 and not f['mismatches']
studies['mixed-postfix-frontier']={k:f[k] for k in ('checked_frontiers','binding_pairs','mismatches','scope')}
for n in ['capability-declaration.json','capability.py','generic-capability-declaration.json','generic_capability.py','mixed-postfix-capability-declaration.json','mixed_postfix_capability.py','mixed-discrepancy-declaration.json','mixed_discrepancy.py','mixed-frontier-observer-declaration.json','mixed_frontier_observer.py','mixed-frontier-observer-result.json','mixed_postfix.py','mixed_postfix_frontier.py']:
 read(n)
# Derive the paired-order visit fraction rather than interpreting it as elapsed fraction.
workmix=[]
for root,sec,native in sorted({(r['root'],r['seconds'],r['native_requested']) for r in studies['capability']['rows']}):
 rows=[r for r in studies['capability']['rows'] if (r['root'],r['seconds'],r['native_requested'])==(root,sec,native)]
 nodes=sum(r['nodes'] for r in rows)/2; q=sum(r['qnodes'] for r in rows)/2; pushes=sum(r['runtime_pushes'] for r in rows)/2
 workmix.append({'root':root,'seconds':sec,'native':native,'nodes':nodes,'qnodes':q,'runtime_pushes':pushes,'q_fraction':q/(nodes+q),'physical_per_visit':pushes/(nodes+q),'retained_depths':[r['completed_depth'] for r in rows],'retained_q':[r['result_ordinary_qdepth'] for r in rows]})
source=read('caller-work-mix.json')
for r in workmix:
 original=[v for v in source['cells'] if (v['root'],v['seconds'],v['native'])==(r['root'],r['seconds'],r['native'])]
 assert len(original)==1
 for k in r: assert r[k]==original[0][k],k
out={'complete':True,'revision':REV,'index':INDEX,'index_sha256':sha(ib),'archive':index['archive'],'base_sha':index['base_sha'],'selected_members':selected,'studies':studies,'work_mix':workmix,'scope':'Independent record/source audit, not independent execution. Old mixed timed records are semantic failures; fixed records do not overwrite them. Visits are attempted work including aborted iterations; fractions are not wall-time attribution. No strength, full-domain, fresh-horizon or deployment proof.'}
(B/'capability.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
print(json.dumps({k:v.get('totals',{}) for k,v in studies.items()})); print('PASS 64 timed records +8 fixed-depth records;2000 recorded frontiers')
