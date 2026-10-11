"""Audit frozen completion/caller curves; no engine calls or extraction."""
import hashlib,io,json,subprocess,zipfile,collections
from pathlib import Path
B=Path(__file__).parent;R='d4a588fe50a5f90c0ad5026f28f02905ee86ed65';I='docs/research/data/terminal_frontier_20261010.json';P='.local_agent/terminal-frontier-20261010/'
def sha(b):return hashlib.sha256(b).hexdigest()
def git(p,rev=R):return subprocess.check_output(['git','show',rev+':'+p])
ib=git(I);i=json.loads(ib);raw=git(i['archive']);assert len(raw)==i['archive_bytes'] and sha(raw)==i['archive_sha256'];z=zipfile.ZipFile(io.BytesIO(raw));selected={}
def read(n):
 p=P+n;b=z.read(p);m=i['members'][p];assert len(b)==m['bytes'] and sha(b)==m['sha256'],p;selected[p]=m
 return json.loads(b) if n.endswith('.json') else b.decode()
v=read('algorithm-curves.json');w=read('resource-curves.json')
assert v['complete'] and len(v['rows'])==120 and w['complete'] and len(w['rows'])==32
assert v['source_sha256']==sha(z.read(P+'algorithm_curves.py')) and w['source_sha256']==sha(z.read(P+'resource_curves.py'))
read('algorithm_curves.py');read('resource_curves.py')
records=[]
for r in v['rows']:
 mode=r['backend'];assert r['root_restored']
 assert r['cap_nodes']==1000000 and r['cap_seconds'] in [.25,1,4] and r['repeat'] in [0,1]
 out={k:r[k] for k in ['case','backend','repeat','cap_seconds','cap_nodes','completed_depth','move','score','exit_cause','setup_seconds','total_caller_seconds']}
 if mode.startswith('minimal_'):
  out.update(nodes=r['work']['nodes'],qnodes=0,node_unit='minimal recursive entries, terminal/static root/leaves included')
  out.update({k:r[k] for k in ['preparation_seconds','search_seconds','validation_seconds','budgeted_seconds']})
 elif mode=='product_native_full':
  s=r['result'];assert s['qnodes']==0 and s['tt_probes']==s['tt_hits']==s['tt_cutoffs']==0
  assert not s['root_window_pruning']
  for k in ['score','completed_depth']:assert s[k]==r[k]
  out.update(nodes=s['nodes'],qnodes=s['qnodes'],node_unit='C recursive iterative-search entries; includes native selected-PV work',kernel_seconds=r['kernel_seconds'],external_validation_seconds=r['external_validation_seconds'],caller_minus_kernel=r['total_caller_seconds']-r['kernel_seconds'])
 else:
  s=r['statistics'];assert s['qnodes']==0 and s['runtime_depth_balanced'] and s['runtime_pushes']==s['runtime_pops']
  assert s['completed_depth']==r['completed_depth'];native=mode=='product_native_legality'
  assert bool(s['native_legality_calls'])==native and s['native_legality_fallbacks']==s['native_legality_operational_failures']==0
  out.update(nodes=s['nodes'],qnodes=s['qnodes'],node_unit='production main+q recursive entries across iterations',native_calls=s['native_legality_calls'],runtime_pushes=s['runtime_pushes'],external_validation_seconds=r['external_validation_seconds'])
 out['caller_plus_recorded_setup']=r['total_caller_seconds']+r['setup_seconds'];records.append(out)
roots=sorted({r['case'] for r in records})
assert roots==['chess-ep','generated-202610082000-ply3','generated-202610082001-ply3','shogi-drop'],roots
expected={r:({'minimal_core','product_core','product_native_legality','minimal_specialized'} if r=='shogi-drop' else {'minimal_core','product_core','product_native_legality','minimal_native_state','product_native_full'} | ({'minimal_specialized'} if r=='chess-ep' else set())) for r in roots}
for root in roots:
 for cap in [.25,1,4]:
  for repeat in [0,1]:
   cell=[r for r in records if (r['case'],r['cap_seconds'],r['repeat'])==(root,cap,repeat)]
   assert {r['backend'] for r in cell}==expected[root] and len(cell)==len(expected[root])
resource=[]
for r in w['rows']:
 assert r['root_restored'];resource.append({k:r[k] for k in ['case','backend','repeat','cap_seconds','cap_nodes','completed_depth','move','score','exit_cause','setup_seconds','caller_seconds','preparation_seconds','search_seconds','validation_seconds','budgeted_seconds']} | {'nodes':r['work']['nodes']})
for root in ['shogi-tactic','shogi-drop']:
 for sec in [.25,1]:
  for cap in [100000,500000]:
   for repeat in [0,1]:
    cell=[r for r in resource if (r['case'],r['cap_seconds'],r['cap_nodes'],r['repeat'])==(root,sec,cap,repeat)]
    assert len(cell)==2 and {r['backend'] for r in cell}=={'Core','Specialized'}
resource_pairs=[]
for root in ['shogi-tactic','shogi-drop']:
 for sec in [.25,1]:
  for repeat in [0,1]:
   for mode in ['Core','Specialized']:
    arms=sorted([r for r in resource if (r['case'],r['cap_seconds'],r['repeat'],r['backend'])==(root,sec,repeat,mode)],key=lambda r:r['cap_nodes'])
    resource_pairs.append({'case':root,'cap_seconds':sec,'repeat':repeat,'backend':mode,'depths':[r['completed_depth'] for r in arms],'same_move':arms[0]['move']==arms[1]['move'],'same_score':arms[0]['score']==arms[1]['score'],'exit_causes':[r['exit_cause'] for r in arms],'budgeted_seconds':[r['budgeted_seconds'] for r in arms]})
groups=[]
for root in roots:
 for cap in [.25,1,4]:
  for mode in sorted(expected[root]):
   rows=[r for r in records if (r['case'],r['cap_seconds'],r['backend'])==(root,cap,mode)]
   groups.append({'case':root,'cap_seconds':cap,'backend':mode,'depths':[r['completed_depth'] for r in rows],'moves':[r['move'] for r in rows],'scores':[r['score'] for r in rows],'exit_causes':[r['exit_cause'] for r in rows],'mean_caller':sum(r['total_caller_seconds'] for r in rows)/2,'mean_setup':sum(r['setup_seconds'] for r in rows)/2})
full=[r for r in records if r['backend']=='product_native_full']
out={'complete':True,'revision':R,'index':I,'index_sha256':sha(ib),'base_commit':i['base_commit'],'archive_sha256':sha(raw),'selected_members':selected,'algorithm_records':records,'groups':groups,'resource_records':resource,'resource_pairs':resource_pairs,'full_native_cells':len(full),'full_native_caller_minus_kernel_range':[min(r['caller_minus_kernel'] for r in full),max(r['caller_minus_kernel'] for r in full)],'counter':dict(collections.Counter((r['backend']+':'+r['exit_cause']) for r in records)),'scope':'Historical material/q0 exposed controls; independent parsing, not execution, current q4, weighted evaluator, matched algorithms or strength. Thin semantic checkpoint differences require source-stage review. Original overlapped cohort remains excluded and preserved upstream.'}
(B/'result.json').write_bytes((json.dumps(out,indent=2)+'\n').encode());print(json.dumps({k:out[k] for k in ['complete','full_native_cells','full_native_caller_minus_kernel_range','counter']}));print('resource',json.dumps(resource_pairs))
