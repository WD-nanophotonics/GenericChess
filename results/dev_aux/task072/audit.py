from pathlib import Path
import collections,json,hashlib
R=Path.cwd();E=R/'.local_agent/fixed_q4_tradeoff/.local_agent';B=Path(__file__).resolve().parent;out={}
cohorts=[('q4-prospective-20261011-repaired',112),('q4-equal-node-20261011',48),('q4-ui-offline-20261011',120)]
for name,count in cohorts:
 source=(E/name/'producer.py').read_bytes();d=json.loads((E/name/'declaration.json').read_bytes());r=json.loads((E/name/'result.json').read_bytes());assert r['complete'] and len(r['rows'])==count and hashlib.sha256(source).hexdigest()==d['source_sha256'];pairs=collections.defaultdict(dict);tot=collections.Counter();losses=[];events=collections.Counter();reasons=collections.Counter()
 for x in r['rows']:
  key=(x['root'],x['order'],x['native_requested'],x.get('max_nodes'));assert x['arm'] not in pairs[key];pairs[key][x['arm']]=x;v,s=x['decision'],x['stats'];assert x['root_restored'] and s['runtime_depth_balanced'] and s['runtime_pushes']==s['runtime_pops']
  for k in set(v)&set(s):assert v[k]==s[k],(name,x['root'],k)
  assert s['native_legality_fallbacks']==s['native_legality_operational_failures']==0
  if x['native_requested']:assert s['native_legality_enabled']==1 and s['native_legality_calls']>0
  else:assert s['native_legality_enabled']==s['native_legality_calls']==0
  if name=='q4-equal-node-20261011':assert v['termination_reason']=='node_limit' and v['nodes']+v['qnodes']==x['max_nodes']
  if name=='q4-ui-offline-20261011':assert v['termination_reason']=='time_limit' and x['seconds']==1
  ev=x['events'];ph=tuple(z['phase'] for z in ev);events[str(ph)]+=1;reasons[v['termination_reason']]+=1
  if x['arm']=='baseline':assert not ev
  elif ev:
   assert ph in (('reserve','begin','complete'),('reserve','begin','aborted'));a,b,c=ev
   assert len({z['budget_identity'] for z in ev})==len({z['deadline'] for z in ev})==1
   assert all(z['q']==4 and z['runtime_depth']==0 and z['runtime_balanced'] and z['runtime_restored'] for z in ev)
   assert a['nodes']==b['nodes'] and a['qnodes']==b['qnodes'] and b['tt_hits']==c['tt_hits']
   assert not b['use_tt'] and not c['use_tt']
   if c['phase']=='aborted':assert (v['action'],v['score'],v['principal_variation'])==(a['action'],a['score'],a['pv']) and v['completed_depth']==1 and v['result_ordinary_qdepth']==0
  for dest,k in [('main_visits','nodes'),('q_visits','qnodes'),('pushes','runtime_pushes'),('legal_generations','legal_generation_calls'),('evaluations','evaluation_calls'),('Native_calls','native_legality_calls')]:tot[dest]+=s[k]
  tot['call_wall_seconds']+=x['wall']
 rootset={x['root'] for x in r['rows']};capset={x.get('max_nodes') for x in r['rows']};nativeflags={False} if name=='q4-ui-offline-20261011' else {False,True};assert set(pairs)=={(root,order,native,cap) for root in rootset for order in (0,1) for native in nativeflags for cap in capset}
 counts=collections.Counter()
 for key,p in pairs.items():
  assert set(p)=={'baseline','fullq4_refresh'};a=p['baseline']['decision'];c=p['fullq4_refresh']['decision'];delta=c['completed_depth']-a['completed_depth'];counts['equal' if delta==0 else 'lost' if delta<0 else 'gained']+=1
  if a['result_ordinary_qdepth']==0 and c['result_ordinary_qdepth']==4:counts['q0_to_q4']+=1
  if a['action']!=c['action']:counts['action_changed']+=1
  if p['fullq4_refresh']['events'] and p['fullq4_refresh']['events'][-1]['phase']=='aborted':counts['refresh_aborted']+=1
  if delta<0:losses.append({'root':key[0],'order':key[1],'native_requested':key[2],'cap':key[3],'depths':[a['completed_depth'],c['completed_depth']],'qdepths':[a['result_ordinary_qdepth'],c['result_ordinary_qdepth']],'action_changed':a['action']!=c['action']})
 out[name]={'calls':count,'pairs':len(pairs),'roots':len(rootset),'counts':dict(counts),'totals':dict(tot),'losses':losses,'phases':dict(events),'termination':dict(reasons),'producer_sha':hashlib.sha256(source).hexdigest()}
bridges={}
for depth,name in [(1,'generated-thin-q4-20261011'),(2,'generated-thin-d2-q4-20261011')]:
 r=json.loads((E/name/'result.json').read_bytes());d=json.loads((E/name/'declaration.json').read_bytes());assert r['complete'] and len(r['rows'])==16 and hashlib.sha256((E/name/'producer.py').read_bytes()).hexdigest()==d['source_sha256'];groups=collections.defaultdict(list)
 for x in r['rows']:
  assert x['reason']=='complete' and x['root_restored'] and x['work']['physical_push']==x['work']['physical_pop'] and x['provider_fallbacks']==x['provider_operational_failures']==0
  assert (x['provider_calls']>0)==x['native_requested'];groups[x['root']].append(x)
 assert set(groups)==set(d['roots'])
 for root,rows in groups.items():
  assert {(x['order'],x['native_requested']) for x in rows}=={(o,n) for o in (0,1) for n in (False,True)}
  assert len({json.dumps([x[k] for k in ('action','score','work','trace')],sort_keys=True) for x in rows})==1;bridges[(root,depth)]=rows[0]
caps=json.loads((E/'native-capsule-q4-20261011/result.json').read_bytes());assert caps['complete'] and len(caps['rows'])==16
for x in caps['rows']:
 base=bridges[(x['root'],x['depth'])];assert x['reason']=='complete' and x['root_restored'] and x['work']['physical_push']==x['work']['physical_pop'];assert all(x[k]==base[k] for k in ('action','score','work','trace'));assert x['provider_calls']>0 and x['provider_fallbacks']==x['provider_operational_failures']==0
out['bridge']={'thin_calls':32,'capsule_calls':16,'all_action_score_work_trace_match':True,'restoration_scope':'Capsule root_restored checks Nativefullsnapshot/stack, not complete Python projectedstate;Task073 supplies actual separate ply drift. Traces record legalaction sequences and noisy/main backed values, not a full snapshot for every rejected/terminal leaf.'}
(B/'audit.json').write_bytes((json.dumps(out,indent=2)+'\n').encode());print(json.dumps(out,indent=2))
