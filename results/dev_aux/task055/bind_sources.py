"""Bind sources and selected frozen records without searches or extraction."""
import ast,hashlib,importlib.metadata,io,json,platform,subprocess,zipfile
from pathlib import Path
B=Path(__file__).parent;ROOT=B.resolve().parents[2];REV='ee48d0a55c7bda3d702f45ce2dc4162cc3bbc0ac';PRODUCT='b4108a68a7ee06327be39cb3a222939644085a52'
def sha(v):return hashlib.sha256(v).hexdigest()
def git(rev,p):return subprocess.check_output(['git','show',rev+':'+p])
def canon(v):return v.replace(b'\r\n',b'\n')
paths=['generic_chess/ai/alphabeta/player.py','generic_chess/ai/alphabeta/search.py','scripts/search_backend_comparison.py','scripts/research_record.py','scripts/chess_development.py','generic_chess/ai/evaluation/evaluator.py','generic_chess/ai/evaluation/config.py','generic_chess/ai/alphabeta/native_legality.py','generic_chess/core/search_runtime.py','generic_chess/core/attacks.py','generic_chess/core/terminal.py','generic_chess/native/compiler.py','generic_chess/native/semantic.py','generic_chess/_native/native_module.c','generic_chess/_native/native_eval.c','generic_chess/learning/shogi_rules.py']
product={}
for p in paths:
 local=(ROOT/p).read_bytes();fixed=git(PRODUCT,p);assert canon(local)==canon(fixed),p
 product[p]=dict(git_blob_sha256=sha(fixed),local_bytes_sha256=sha(local),canonical_lf_sha256=sha(canon(local)))
indices=['availability_core_20261011','runtime_cost_controls_20261011','completion_policy_20261011'];archives={};bound={}
for index in indices:
 path='docs/research/data/'+index+'.json';ib=git(REV,path);i=json.loads(ib);raw=git(REV,i['archive']['path']);assert len(raw)==i['archive']['bytes'] and sha(raw)==i['archive']['sha256'];archives[index]=(i,zipfile.ZipFile(io.BytesIO(raw)));bound[index]=dict(index_path=path,index_sha256=sha(ib),archive=i['archive'],selected_members=[])
def member(index,path):
 i,z=archives[index];e=next(x for x in i['members'] if x['member']==path);v=z.read(path);assert len(v)==e['bytes'] and sha(v)==e['sha256'];bound[index]['selected_members'].append(e);return v
private={}
for p in ['.local_agent/weighted-backend-20261011/bridge.py','.local_agent/availability-core-20261011/typed_token_probe.py']:
 fixed=member('availability_core_20261011',p);local=(ROOT/p).read_bytes();assert canon(fixed)==canon(local),p
 private[p]=dict(member_sha256=sha(fixed),local_bytes_sha256=sha(local),canonical_lf_sha256=sha(canon(local)))
profile_runtime=member('runtime_cost_controls_20261011','generic_chess/core/search_runtime.py')
replay=json.loads(member('completion_policy_20261011','evaluation-bitmaps-20261011/replay.json'));member('completion_policy_20261011','evaluation-bitmaps-20261011/replay.py');fixed=json.loads(member('completion_policy_20261011','weighted-backend-20261011/fixed.json'));member('completion_policy_20261011','weighted-backend-20261011/fixed.py');member('completion_policy_20261011','weighted-backend-20261011/bridge.py')
assert replay['complete'] and fixed['complete'] and len(fixed['audits'])==8
replay_summary=[]
for r in replay['roots']:
 assert r['all_scores_exact'] and len(r['components'])==r['calls']
 weighted=[v for v in r['replay'] if v['arm']=='weighted'];material=[v for v in r['replay'] if v['arm']=='material']
 assert len(weighted)==len(material)==2 and weighted[0]['scores']==weighted[1]['scores']==[v['score'] for v in r['components']] and material[0]['scores']==material[1]['scores']
 replay_summary.append(dict(root=r['root'],calls=r['calls'],weighted_walls=[v['wall_seconds'] for v in weighted],material_walls=[v['wall_seconds'] for v in material],component_sums=r['component_sums'],scope=replay['query_scope']))
assert sum(r['calls'] for r in replay_summary)==1046
specialized_trace_summary=[{k:r[k] for k in ('root','actual_evaluation_calls','adapter_seconds','evaluation_seconds','trace_core_wall','specialized_trace_wall','trace')} for r in fixed['audits']]
checks={}
for p in sorted(B.glob('*.py')):ast.parse(p.read_text(encoding='utf-8-sig'),filename=str(p));checks[p.name]='AST pass'
for p in sorted(B.glob('*.json')):
 if p.name!='source_binding.json':json.loads(p.read_bytes());checks[p.name]='JSON parse pass'
versions={}
for package in ('chess','pytest','cshogi'):
 try:versions[package]=importlib.metadata.version(package)
 except importlib.metadata.PackageNotFoundError:versions[package]='absent'
out=dict(complete=True,product_revision=PRODUCT,primary_revision=REV,python=platform.python_version(),packages=versions,product_sources=product,private_dependency_sources=private,selected_archives=bound,profile_runtime_member_sha256=sha(profile_runtime),archived_runtime_matches_local=canon(profile_runtime)==canon((ROOT/'generic_chess/core/search_runtime.py').read_bytes()),frozen_replay_summary=replay_summary,old_specialized_trace_summary=specialized_trace_summary,paired_gap_missing='Old trace records time specialized conversion/evaluation but not paired Core evaluator core. Never subtract cProfile times from these.',artifact_checks=checks,artifact_hashes={p.name:dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(B.iterdir()) if p.is_file() and p.name!='source_binding.json'},limits='Source and record integrity only, not binary build reproduction or full semantic/history proof. Binary independently pinned in each new observer. Existing1046input replay was parsed; no pickle was loaded or evaluator replayed. Archived snapshot-failure cleanup and source-stage differences preserved.')
(B/'source_binding.json').write_bytes((json.dumps(out,indent=2)+'\n').encode());print('bound',len(product),'product files,',len(private),'private dependencies,1046old replay inputs,',len(checks),'artifacts')
