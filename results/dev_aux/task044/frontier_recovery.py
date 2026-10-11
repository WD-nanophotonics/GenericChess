"""Public nullable-token frontier/retry witness; declared no-time."""
import ast,hashlib,json,time
from dataclasses import replace
from pathlib import Path
B=Path(__file__).parent
src=(B.parent/'task040/deferred_square.py').read_text()
tree=ast.parse(src);prefix=[]
for n in tree.body:
 if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='rows' for t in n.targets):break
 prefix.append(n)
env={'__file__':str(B.parent/'task040/deferred_square.py')}
exec(compile(ast.Module(body=prefix,type_ignores=[]),'<frozen fixture imports>','exec'),env)
outer=next(n for n in tree.body if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='scope')
env['scope']='global';setup=[]
for n in outer.body:
 if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='c' for t in n.targets):break
 setup.append(n)
exec(compile(ast.Module(body=setup,type_ignores=[]),'<frozen declarations>','exec'),env)
rules=env['_semantic_ruleset']((env['_king_type'](),env['A']),tuple(reversed(env['actions'])),n=4,
 rows=tuple(tuple(env['board'][i:i+4]) for i in range(0,16,4)))
compiled=env['compile_semantic_ruleset'](rules)
engine=env['semantic_engine_for'](compiled);root=env['GameSession'](compiled).state.position
ids={name:i for i,name in enumerate(sorted(slot.name for slot in env['slots']))}
aux=dict(root.aux_state);aux[(ids['source_token'],-1)]=(2,2);aux[(ids['output_token'],-1)]=(3,1)
normal=replace(root,aux_state=tuple(sorted(aux.items())))
missing_aux=dict(normal.aux_state);missing_aux[(ids['source_token'],-1)]=None
states=[('normal',normal),('missing',replace(normal,aux_state=tuple(sorted(missing_aux.items()))))]
p=env['p'];p.prepare(compiled)
semantic_ids={x.name:x.pattern_id for x in compiled.ir.patterns if x.name in ('source_square','pre_expiry_token')}
assert p.plans[semantic_ids['source_square']][1] is p.plans[semantic_ids['pre_expiry_token']][1]
generated_hits=[]
for pid,(pattern,fn) in list(p.plans.items()):
 def hit(*args,_pid=pid,_fn=fn,**kw):
  generated_hits.append(_pid);return _fn(*args,**kw)
 p.plans[pid]=(pattern,hit)
S=type(engine);saved=S._transition
names={x.pattern_id:x.name for x in compiled.ir.patterns};records=[];started=time.monotonic()
def observe(fn,pos,fault_name=None,fault_local=None):
 yielded=[];transitions=[];checkpoints=[];phase=None;prior_hits=len(generated_hits)
 fault=RuntimeError('set_token ref unresolved');raised=False
 def checkpoint():
  checkpoints.append((len(checkpoints)+1,phase))
  if fault_name is not None and phase==fault_name and transitions[-1]['local_checkpoints']==fault_local:raise fault
 def transition(self,current,action,binding,checkpoint=None):
  nonlocal phase
  prior_phase=phase;phase=names[binding.pattern.pattern_id];count=0
  record=dict(name=phase,pattern_id=binding.pattern.pattern_id,action=repr(action),local_checkpoints=0,status='entered')
  transitions.append(record)
  def local():
   nonlocal count
   count+=1;record['local_checkpoints']=count
   if checkpoint is not None:checkpoint()
  try:
   child=fn(self,current,action,binding,checkpoint=local)
   record['status']='child';record['child']=repr(child);return child
  except RuntimeError as exc:
   record['status']='fault' if exc is fault else 'semantic_rejection'
   record['message']=str(exc);raise
  finally:phase=prior_phase
 S._transition=transition;before=repr(pos)
 try:
  for action in engine.iter_legal_actions(pos,checkpoint=checkpoint):yielded.append(repr(action))
 except RuntimeError as exc:
  assert exc is fault and fault_name is not None;raised=True
 finally:S._transition=saved
 assert repr(pos)==before
 if fn is p.candidate:assert generated_hits[prior_hits:]==[a['pattern_id'] for a in transitions]
 else:assert len(generated_hits)==prior_hits
 assert getattr(engine,'_postcondition_parent',None) is None and getattr(engine,'_postcondition_action',None) is None
 return dict(yielded=yielded,transitions=transitions,checkpoints=checkpoints,raised_exact_fault=raised,
  full_parent_unchanged=True,postcondition_fields_clear=True)
try:
 for label,pos in states:
  env['stopped']();assert time.monotonic()-started<120
  a=observe(p.baseline,pos);b=observe(p.candidate,pos);assert a==b
  semantic=[r for r in a['transitions'] if r['name'] in ('pre_expiry_token','source_square')]
  assert [r['name'] for r in semantic]==['pre_expiry_token','source_square']
  assert [r['status'] for r in semantic]==(['child','child'] if label=='normal' else ['semantic_rejection','child'])
  valid_patterns=[names[act.pattern_id] for act in engine.legal_actions(pos)]
  assert 'source_square' in valid_patterns and ('pre_expiry_token' in valid_patterns)==(label=='normal')
  faults=[]
  for row in semantic:
   for stop in (1,row['local_checkpoints']):
    env['stopped']();assert time.monotonic()-started<120
    x=observe(p.baseline,pos,row['name'],stop);y=observe(p.candidate,pos,row['name'],stop)
    assert x==y and x['raised_exact_fault']
    retry_a=observe(p.baseline,pos);retry_b=observe(p.candidate,pos)
    assert retry_a==retry_b==a
    faults.append(dict(action=row['name'],local_stop=stop,interrupted=x,fresh_retry_equals_complete=True))
  records.append(dict(state=label,normal=a,legal_pattern_names=valid_patterns,faults=faults))
finally:S._transition=saved
out=dict(complete=True,fixture_source_sha256=hashlib.sha256((B.parent/'task040/deferred_square.py').read_bytes()).hexdigest(),
 shared_source_sha256=hashlib.sha256((B.parent/'task025/compiled_effect_shared.py').read_bytes()).hexdigest(),
 named_shared_function_identity=True,candidate_generated_calls=len(generated_hits),records=records,scope='2normal full-public-frontier pairs;8fault pairs and16fresh retries;one global compatibility fixture',
 limits='No Task04012pair replay or Task041 direct-S3 replay. Setup compiles ordered public actions and initializes a semantic session. No timing/search/Native/OOM/all-domain claim.')
(B/'frontier_recovery.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
print('public frontier2normal/8fault pairs pass; semantic rejection followed by valid action;16fresh retries')
