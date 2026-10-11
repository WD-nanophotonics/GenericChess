"""Audit completed primary scientific records; no benchmark imports or reruns."""
import hashlib,json,math
from pathlib import Path
B=Path(__file__).parent
read=lambda name:json.loads((B/name).read_text(encoding='utf-8'))
v=read('frozen_control.json');slot=read('frozen_slot.json');analysis=read('frozen_cost_analysis.json')
assert v['complete'] and len(v['fixed'])==64 and len(v['completed'])==4 and len(v['setup'])==8
assert slot['exit']==0 and slot['within_slot']
setup={r['root']:r['seconds'] for r in v['setup']}
clean=lambda x:{k:clean(y) for k,y in x.items() if 'seconds' not in k and not k.startswith('time_')} if isinstance(x,dict) else list(map(clean,x)) if isinstance(x,list) else x
out={'complete':False,'source':'PRIMARY_SANDBOX supplied already executed controls; independently audited by DEV_AUX','rows':[]}
for kind in ('fixed','completed'):
 for root in sorted({r['root'] for r in v[kind]}):
  rr=[r for r in v[kind] if r['root']==root];repeats=sorted({r['repeat'] for r in rr})
  assert repeats==list(range(4 if kind=='fixed' else 2))
  pairs=[];base=0;candidate=0
  for repeat in repeats:
   rows=[r for r in rr if r['repeat']==repeat]
   assert len(rows)==2 and [r['candidate'] for r in rows]==([False,True] if repeat%2==0 else [True,False])
   pair={r['candidate']:r for r in rows}
   assert clean(pair[False]['decision'])==clean(pair[True]['decision'])
   a=pair[False]['wall'];c=pair[True]['wall'];assert math.isfinite(a) and math.isfinite(c) and a>0 and c>0
   base+=a;candidate+=c
   pairs.append({'repeat':repeat,'warm_ratio':c/a,'one_call_cold_ratio':(c+setup[root])/a,'nodes':pair[False]['decision']['nodes'],'qnodes':pair[False]['decision']['qnodes'],'completed_depth':pair[False]['decision']['completed_depth'],'termination_reason':pair[False]['decision']['termination_reason'],'accepted_native_calls':pair[False]['decision'].get('native_legality_calls'),'normal_or_operational_fallbacks':pair[False]['decision'].get('native_legality_fallbacks')})
  reported=next(r for r in analysis['rows'] if r['condition']==kind and r['root']==root)
  approx=lambda a,b:math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12)
  assert approx(reported['warm_aggregate_ratio'],candidate/base)
  assert approx(reported['candidate_reuse_batch_with_one_setup_ratio'],(candidate+setup[root])/base)
  for calc,got in zip(pairs,reported['pairs']):
   assert approx(calc['warm_ratio'],got['warm_ratio']) and approx(calc['one_call_cold_ratio'],got['one_call_cold_ratio'])
  saving=(base-candidate)/len(repeats);n=math.ceil(setup[root]/saving) if saving>0 else None
  assert reported['estimated_calls_to_amortize']==n
  out['rows'].append({'condition':kind,'root':root,'pairs':pairs,'warm_ratio':candidate/base,'one_setup_batch_ratio':(candidate+setup[root])/base,'descriptive_amortization_calls':n,'all_declared_arms_retained':True,'non_time_metadata_equal':True})
out.update(complete=True,files=[{'path':f.name,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in sorted(B.glob('frozen*'))],scope='independent record/source review, not independent execution or speed forecast',limitations=['Accepted Native counters do not count every C entry/return or Core trial.', 'Cold totals add prototype prepare; original rules compilation and Session creation stay outside both arm timers.', 'Fresh Player/TT/provider inside caller timers; reused rule preparation differs from warm TT.', 'Break-even from finite means is descriptive; global single-prepared-carrier and no deployed reuse are distinct boundaries.', 'Resource ACK reserves DEV_AUX only, not a whole-machine atomic lease.'])
(B/'cost_record_audit.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print([(r['condition'],r['root'],round(r['warm_ratio'],3),round(r['one_setup_batch_ratio'],3),r['descriptive_amortization_calls']) for r in out['rows']])
