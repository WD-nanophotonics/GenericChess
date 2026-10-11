"""Independent record invariants for declared fixed-node counterexamples."""
from pathlib import Path
import collections,json,hashlib,subprocess,zipfile,io
ROOT=Path.cwd();PIN='bebe3d98ebb0832207e112ca0755fa9837cef3e7'
all_summaries={}
for task in ('task061','task062'):
 B=ROOT/'results/dev_aux'/task;r=json.loads((B/'result.json').read_bytes());d=json.loads((B/'DECLARATION.json').read_bytes());assert r['complete'] and r['declaration']==d and len(r['rows'])==d['calls']
 assert len(r['seeds'])==(2 if task=='task061' else 1)
 for seed in r['seeds']:
  assert seed['decision']['completed_depth']==2 and seed['decision']['termination_reason']=='completed_depth'
  assert seed['stats']['runtime_depth_balanced'] and seed['stats']['runtime_pushes']==seed['stats']['runtime_pops']
 pairs=collections.defaultdict(dict);counts=collections.Counter();losses=[]
 for x in r['rows']:
  v,s=x['decision'],x['stats'];key=(x['root'],x['lineage'],x['node_cap']);assert x['arm'] not in pairs[key];pairs[key][x['arm']]=x
  assert x['root_full_runtime_restored'] and s['runtime_depth_balanced'] and s['runtime_pushes']==s['runtime_pops']
  assert s['native_legality_enabled']==1 and s['native_legality_calls']>0 and s['native_legality_fallbacks']==s['native_legality_operational_failures']==0
  assert v['termination_reason'] in ('node_limit','completed_depth') and v['nodes']+v['qnodes']<=x['node_cap']
  for k in set(v)&set(s):assert v[k]==s[k]
  if v['termination_reason']=='node_limit':assert v['nodes']+v['qnodes']==x['node_cap']
  if x['lineage']=='cold':assert x['tt_before']['entries']==0
  else:assert x['tt_before']==next(z['tt'] for z in r['seeds'] if z['root']==x['root'])
  ev=x['events']
  if x['arm']=='baseline':assert ev==[]
  elif x['arm']=='skip_warm_root':assert ev==[] and len(x['selection'])==1 and x['selection'][0]['skip_refresh'] and x['selection'][0]['entry_depth']==2 and x['selection'][0]['entry_bound']=='EXACT'
  else:
   assert [e['phase'] for e in ev] in (['reserve','begin','complete'],['reserve','begin','aborted'])
   a,b,c=ev;assert len({e['budget_identity'] for e in ev})==len({e['deadline'] for e in ev})==1
   assert all(e['q']==4 and e['runtime_balanced'] and e['runtime_restored'] and e['runtime_depth']==0 for e in ev)
   assert a['nodes']==b['nodes'] and a['qnodes']==b['qnodes'] and b['tt_hits']==c['tt_hits']
   assert b['nodes']<=c['nodes']<=v['nodes'] and b['qnodes']<=c['qnodes']<=v['qnodes']
   assert not b['use_tt'] and not c['use_tt']
   if c['phase']=='aborted':assert (v['action'],v['score'],v['principal_variation'])==(a['action'],a['score'],a['pv']) and v['completed_depth']==1
   elif v['completed_depth']==1:assert (v['action'],v['score'],v['principal_variation'])==(c['action'],c['score'],c['pv'])
  counts['calls']+=1;counts['visits']+=v['nodes']+v['qnodes'];counts['wall_observation']+=x['wall_observation']
 expected={(root,lineage,cap) for root in d['roots'] for lineage in (d.get('lineages') or ['same_baseline_D2_TT']) for cap in d['node_caps']};assert set(pairs)==expected
 matrix=[]
 for key,arms in pairs.items():
  assert set(arms)==set(d['arms']);assert len({json.dumps(x['tt_before'],sort_keys=True) for x in arms.values()})==1
  bv=arms['baseline']['decision'];row=dict(root=key[0],lineage=key[1],node_cap=key[2],arms={})
  for a,x in arms.items():
   v=x['decision'];cell=dict(depth=v['completed_depth'],q=v['result_ordinary_qdepth'],score=v['score'],depth_delta=v['completed_depth']-bv['completed_depth'],action_changed=v['action']!=bv['action'],score_changed=v['score']!=bv['score'],pv_length=len(v['principal_variation']),tt_hits=v['tt_hits']);row['arms'][a]=cell
   if a!='baseline' and cell['depth_delta']<0:losses.append(dict(root=key[0],lineage=key[1],node_cap=key[2],arm=a,**cell))
  matrix.append(row)
 summary=dict(task=task,source_pin=PIN,counts=dict(counts),matrix=matrix,losses=losses,scope='Completed-depth bookkeeping under selective TT, not fresh uniform-horizon or strength evidence; all stops node/depth, no time-guard censoring.');(B/'analysis.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8');all_summaries[task]=dict(counts=dict(counts),losses=losses)
export=ROOT/'.local_agent/pinned_bebe';raw=subprocess.check_output(['git','archive','--format=zip',PIN,'generic_chess','scripts']);z=zipfile.ZipFile(io.BytesIO(raw));files=[]
for info in z.infolist():
 if info.is_dir():continue
 b=z.read(info);assert (export/info.filename).read_bytes()==b
 files.append(dict(path=info.filename,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
for rel in ('docs/research/data/chess_zero_target_correction_20261005.json','tests/product/test_h50b2a_semantic_native_search.py'):
 b=subprocess.check_output(['git','show',PIN+':'+rel]);actual=export/('native_initial_fixture.py' if rel.startswith('tests/') else rel);assert actual.read_bytes()==b;files.append(dict(path=rel,export_path=str(actual.relative_to(export)),bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
(ROOT/'results/dev_aux/task061/export_manifest.json').write_text(json.dumps(dict(pin=PIN,files=files),indent=2)+'\n',encoding='utf-8')
print(json.dumps(all_summaries,indent=2))

d=json.loads((ROOT/'results/dev_aux/task061/DECLARATION.json').read_bytes())
for name,key in [('weighted.py','weighted_helper_sha256'),('pvs_probe.py','restoration_helper_sha256')]:assert hashlib.sha256((export/name).read_bytes()).hexdigest()==d[key]
