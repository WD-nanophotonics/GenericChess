"""Frozen material common-time rows; no search, no timing rerun."""
import hashlib,io,json,statistics,subprocess,zipfile
from pathlib import Path
B=Path(__file__).parent;REV='ee48d0a55c7bda3d702f45ce2dc4162cc3bbc0ac'
def blob(p):return subprocess.check_output(['git','show',REV+':'+p])
i=json.loads(blob('docs/research/data/search_attribution_20261010.json'));raw=blob(i['archive']);assert hashlib.sha256(raw).hexdigest()==i['archive_sha256'];z=zipfile.ZipFile(io.BytesIO(raw))
bindings={}
def member(n):
 v=z.read(n);e=i['members'][n];assert len(v)==e['bytes'] and hashlib.sha256(v).hexdigest()==e['sha256'];bindings[n]=e;return v
u=json.loads(member('utility.json'));member('utility-used-source.py');member('utility-runtime-source.py')
assert len(u['rows'])==240 and len(u['references'])==8 and u['budgets']==[0.25,1.0,4.0] and u['repeat']==2
assert all(r['legal'] and r['finite_D4_regret'] is not None and r['finite_D4_regret']>=0 and r['selected_child_D3']['reason']=='completed_depth' and r['selected_child_D3']['completed_depth']==3 for r in u['rows'])
refs={r['case']:r for r in u['references']};assert all(r['reason']=='completed_depth' and r['completed_depth']==4 for r in refs.values())
assert all(r['statistics']['native_legality_enabled']==1 and r['statistics']['native_legality_calls']>0 and r['statistics']['native_legality_fallbacks']==r['statistics']['native_legality_operational_failures']==0 for r in u['rows'] if r['backend']=='supported_native_legality')
assert all(r['statistics']['qnodes']==0 for r in u['rows'] if r['backend'].startswith('supported'))
backends=sorted({r['backend'] for r in u['rows']});summary=[];cohorts=[]
for backend in backends:
 rs=[r for r in u['rows'] if r['backend']==backend];assert len(rs)==48
 summary.append(dict(backend=backend,choices=len(rs),positive_D4_regret=sum(r['finite_D4_regret']>0 for r in rs),legal_choices=sum(r['legal'] for r in rs)))
 for root in sorted(refs):
  for seconds in u['budgets']:
   pair=[r for r in rs if r['case']==root and r['seconds']==seconds];assert len(pair)==2 and {r['repeat'] for r in pair}=={0,1}
   def depth(r):return r['statistics']['completed_depth'] if backend.startswith('supported') else r['completed_depth']
   def nodes(r):return r['statistics']['nodes']+r['statistics']['qnodes'] if backend.startswith('supported') else r['work']['nodes']
   decisions=[]
   for r in pair:
    assert r['selected_value_D4']==refs[root]['score']-r['finite_D4_regret']
    decisions.append(dict(repeat=r['repeat'],move=r['move'],score=r['score'],depth=depth(r),reason=r['reason'],regret=r['finite_D4_regret'],wall_seconds=r['wall_seconds'],budget_overrun=r['wall_seconds']-seconds,node_count=nodes(r),qnodes=r.get('statistics',{}).get('qnodes'),interrupted_root_completed=r.get('interrupted_root_completed'),provider_calls=r.get('statistics',{}).get('native_legality_calls'),provider_fallbacks=r.get('statistics',{}).get('native_legality_fallbacks')))
   cohorts.append(dict(root=root,backend=backend,seconds=seconds,decisions=decisions,paired_choice_equal=pair[0]['move']==pair[1]['move']))
 print(summary[-1])
for root in ('chess-ep','shogi-middle','shogi-drop'):
 print(root,[(r['backend'],[d['depth'] for d in r['decisions']],[d['regret'] for d in r['decisions']]) for r in cohorts if r['root']==root and r['seconds']==1])
out=dict(complete=True,source_only=True,primary_revision=REV,archive_path=i['archive'],archive_sha256=i['archive_sha256'],members=bindings,summary=summary,cohorts=cohorts,limits=['Old arbitrary MATERIAL evaluator, not weighted D2 attribution. Do not apply its D4 teacher to weighted scores.','240 correlated exposed choices, not independent samples; fixed D4 diagnostic is not WDL or strength.','Minimal visits include root, terminal, leaf and aborted iterative attempts. Supported main+q visits across depths are a different unit; no normalized throughput comparison.','Archived source is accounting pre-fix; native backend metrics missing on minimal iterative rows are unknown, not zero.','Returned duration/budget overrun is descriptive old-source behavior, not current SLA. Constructors/compiler preparation are outside returned times.','Mature engines are not in this aligned utility cohort; their different evaluations are overall references.'])
(B/'utility_attribution.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
