"""Read and join frozen full-tree profiles; never execute a search."""
import hashlib,io,json,subprocess,zipfile
from pathlib import Path
B=Path(__file__).parent
REV='ee48d0a55c7bda3d702f45ce2dc4162cc3bbc0ac'
def blob(p):return subprocess.check_output(['git','show',REV+':'+p])
def load(index_path,names):
 i=json.loads(blob(index_path));a=i['archive'];raw=blob(a['path']);assert hashlib.sha256(raw).hexdigest()==a['sha256']
 z=zipfile.ZipFile(io.BytesIO(raw));out={};bindings=[]
 for name in names:
  entry=next(x for x in i['members'] if x['member']==name);data=z.read(name)
  assert len(data)==entry['bytes'] and hashlib.sha256(data).hexdigest()==entry['sha256']
  out[name]=data;bindings.append(entry)
 return i,out,bindings
prefix='.local_agent/availability-core-20261011/'
pi,pdata,pbindings=load('docs/research/data/runtime_cost_controls_20261011.json',[prefix+'residual-function-profile.json',prefix+'residual_function_profile.py'])
fi,fdata,fbindings=load('docs/research/data/availability_core_20261011.json',[prefix+'residual-bridge.json'])
p=json.loads(pdata[prefix+'residual-function-profile.json']);f=json.loads(fdata[prefix+'residual-bridge.json'])
assert p['complete'] and f['complete'] and len(p['rows'])==16
rows=[]
for root in sorted({r['root'] for r in p['rows']}):
 rs=[r for r in p['rows'] if r['root']==root];assert len(rs)==2
 plain=next(r for r in rs if not r['profiled']);prof=next(r for r in rs if r['profiled']);decision=prof['decision'];frozen=[r for r in f['rows'] if r['root']==root]
 for v in [plain['decision'],decision]+frozen:
  assert v['reason']=='completed_depth' and v['completed_depth']==2
  for k in ('move','score','work'):assert v[k]==decision[k],(root,k)
 counters=decision['runtime_counters'];assert decision['native_provider_active'] and counters['legal_provider_fallbacks']==counters['legal_provider_operational_failures']==0
 def fn(file,name):
  candidates=[v for v in prof['functions'] if v['file']==file and v['name']==name];assert len(candidates)==1,(root,file,name)
  return candidates[0]
 rt='generic_chess/core/search_runtime.py'
 stages={'provider':fn(rt,'_legal_actions_from_provider'),'push_including_terminal':fn(rt,'_push_impl'),'leaf_evaluation':fn('generic_chess/ai/evaluation/evaluator.py','evaluate'),'pop':fn(rt,'pop')}
 nested=fn('generic_chess/core/terminal.py','terminal_from_search_runtime')
 assert stages['provider']['total_calls']==decision['work']['legal_queries']==counters['legal_provider_calls']
 assert stages['push_including_terminal']['total_calls']==stages['pop']['total_calls']==decision['work']['pushes']==counters['pushes']==counters['pops']
 assert nested['inclusive_seconds']<=stages['push_including_terminal']['inclusive_seconds']
 assigned=sum(v['inclusive_seconds'] for v in stages.values());assert 0<assigned<=decision['wall_seconds']
 row=dict(root=root,work=decision['work'],move=decision['move'],score=decision['score'],plain_wall=plain['decision']['wall_seconds'],profile_wall=decision['wall_seconds'],profile_over_plain=decision['wall_seconds']/plain['decision']['wall_seconds'],coarse_scopes=stages,terminal_nested=nested,unassigned_wall=decision['wall_seconds']-assigned,python_filtered_self_sum=sum(v['self_seconds'] for v in prof['functions']),dominant_scope=max(stages,key=lambda k:stages[k]['inclusive_seconds']))
 rows.append(row)
 print(root,row['dominant_scope'],'profile/plain',round(row['profile_over_plain'],2),'scopes', {k:round(v['inclusive_seconds']/row['profile_wall']*100,1) for k,v in stages.items()},'unassigned%',round(row['unassigned_wall']/row['profile_wall']*100,1))
out=dict(complete=True,primary_revision=REV,profile_base=pi['base_sha'],source_only=True,profile_archive=pi['archive'],profile_members=pbindings,frozen_archive=fi['archive'],frozen_members=fbindings,rows=rows,limits=['All sixteen archived calls match the eighty frozen decisions and work, not their elapsed times.','Profile has no typed-token memo; provider reused across plain then profiled call, so syntax may be warm.','cProfile perturbation is large and nonuniform; these shares rank observed scopes, not attainable savings or a profiled/plain speedup.','Provider, push, evaluate, pop are nonrecursive coarse scopes under this caller with cached parent legality; terminal is nested in push and must not be added.','Wall residual contains script/control, labels, builtins and profiler effects; Python-only self totals exclude other work.','No pure C-kernel duration is isolated. Profile source base differs from current product only in a relevant support-limit accessor on inspected normal paths; source-stage repair remains declared.'])
(B/'profile_attribution.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
