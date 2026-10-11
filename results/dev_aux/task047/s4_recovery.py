"""Shared transition in actual S4 reply scan, finite and no-time."""
import ast,hashlib,json,time,sys
from dataclasses import replace
from pathlib import Path
B=Path(__file__).parent;ROOT=B.resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from generic_chess.rules.schema import RulePostcondition
src=(B.parent/'task044/frontier_recovery.py').read_text();tree=ast.parse(src);setup=[]
for node in tree.body:
 if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='compiled' for t in node.targets):break
 setup.append(node)
env={'__file__':str(B.parent/'task044/frontier_recovery.py')}
exec(compile(ast.Module(body=setup,type_ignores=[]),'<frozen public declarations>','exec'),env)
rules=replace(env['rules'],semantic_actions=tuple(
 replace(a,postconditions=(RulePostcondition('no_legal_reply',max_stratum='S3'),))
 if a.name=='source_square' else a for a in env['rules'].semantic_actions))
compiled=env['env']['compile_semantic_ruleset'](rules)
fixture=env['env'];engine=fixture['semantic_engine_for'](compiled);root=fixture['GameSession'](compiled).state.position
ids={name:i for i,name in enumerate(sorted(slot.name for slot in fixture['slots']))}
aux=dict(root.aux_state);aux[(ids['source_token'],-1)]=(2,2);aux[(ids['output_token'],-1)]=(3,1)
pos=replace(root,aux_state=tuple(sorted(aux.items())))
p=fixture['p'];p.prepare(compiled);hits=[]
for pid,(pattern,fn) in list(p.plans.items()):
 def hit(*args,_pid=pid,_fn=fn,**kw):hits.append(_pid);return _fn(*args,**kw)
 p.plans[pid]=(pattern,hit)
S=type(engine);saved=dict(transition=S._transition,reply=S._exists_s3_reply)
names={a.pattern_id:a.name for a in compiled.ir.patterns}
started=time.monotonic()
def observe(fn,stop=None):
 phase=None;depth=0;local=0;checks=[];transitions=[];probe=[];yielded=[];raised=False
 fault=RuntimeError('set_token ref unresolved');before=repr(pos);prior=len(hits)
 def checkpoint():
  stage='reply_transition' if phase=='reply' and depth else 'reply_frontier' if phase=='reply' else 'outer'
  checks.append((len(checks)+1,stage,local))
  if phase=='reply' and local==stop:raise fault
 def transition(self,current,action,binding,checkpoint=None):
  nonlocal depth
  depth+=1
  row=dict(pattern_id=binding.pattern.pattern_id,name=names[binding.pattern.pattern_id],
   stage=phase or 'outer',parent=repr(current),status='entered')
  transitions.append(row)
  try:
   child=fn(self,current,action,binding,checkpoint=checkpoint)
   row['status']='child';row['child']=repr(child);return child
  except RuntimeError as exc:
   assert exc is fault;row['status']='exact_callback_fault';raise
  finally:
   assert repr(current)==row['parent'];depth-=1
 def reply(self,child,checkpoint=None):
  nonlocal phase,local
  prior_phase=phase;phase='reply';local=0;stable=repr(child)
  parent_context=getattr(self,'_postcondition_parent',None)
  action_context=getattr(self,'_postcondition_action',None)
  assert parent_context is pos and action_context is not None
  assert names[action_context.pattern_id]=='source_square'
  record=dict(child=stable,context_parent_exact=True,context_action='source_square',status='entered')
  probe.append(record)
  def local_checkpoint():
   nonlocal local
   local+=1
   if checkpoint is not None:checkpoint()
  try:
   value=saved['reply'](self,child,checkpoint=local_checkpoint)
   record['status']='returned';record['result']=value;return value
  except RuntimeError as exc:
   assert exc is fault;record['status']='exact_callback_fault';raise
  finally:
   assert repr(child)==stable;phase=prior_phase
 S._transition=transition;S._exists_s3_reply=reply
 try:
  for action,binding in engine.iter_legal_action_bindings(pos,source=5,target=9,checkpoint=checkpoint):
   yielded.append(dict(action=repr(action),name=binding.pattern.name))
 except RuntimeError as exc:
  assert exc is fault and stop is not None;raised=True
 finally:
  S._transition=saved['transition'];S._exists_s3_reply=saved['reply']
 assert phase is None and depth==0 and repr(pos)==before
 assert getattr(engine,'_postcondition_parent',None) is None and getattr(engine,'_postcondition_action',None) is None
 if fn is p.candidate:assert hits[prior:]==[r['pattern_id'] for r in transitions]
 else:assert len(hits)==prior
 return dict(yielded=yielded,checks=checks,transitions=transitions,probe=probe,
  raised_exact_fault=raised,postcondition_fields_clear=True,full_parent_unchanged=True)
normal_a=observe(p.baseline);normal_b=observe(p.candidate);assert normal_a==normal_b
assert len(normal_a['probe'])==1 and normal_a['probe'][0]['result'] is True
assert {'source_square','pre_expiry_token'}<={r['name'] for r in normal_a['yielded']}
probe_checks=[r for r in normal_a['checks'] if r[1].startswith('reply')]
nested=[r for r in probe_checks if r[1]=='reply_transition'];assert nested
stops=[probe_checks[0][2],nested[0][2],nested[-1][2]];assert len(set(stops))==3
records=[]
for stop in stops:
 fixture['stopped']();assert time.monotonic()-started<120
 a=observe(p.baseline,stop);b=observe(p.candidate,stop);assert a==b and a['raised_exact_fault']
 retry_a=observe(p.baseline);retry_b=observe(p.candidate);assert retry_a==retry_b==normal_a
 records.append(dict(probe_stop=stop,interrupted=a,fresh_retry_equals_complete=True))
out=dict(complete=True,fixture_source_sha256=hashlib.sha256((B.parent/'task044/frontier_recovery.py').read_bytes()).hexdigest(),
 shared_source_sha256=hashlib.sha256((B.parent/'task025/compiled_effect_shared.py').read_bytes()).hexdigest(),
 normal=normal_a,faults=records,candidate_generated_calls=len(hits),
 scope='1normal filtered public pair;3S4/nested-transition fault pairs;6fresh retries;one global compatibility fixture',
 limits='No Task044comparison replay; setup imports declarations only. No search, timing, Native, OOM, all S4 kinds/scopes or full domain claim.')
(B/'s4_recovery.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
print('S4 shared1normal/3fault pairs,6fresh retries; real nested S3 and context cleanup')
