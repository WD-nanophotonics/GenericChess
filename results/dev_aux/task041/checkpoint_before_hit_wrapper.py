"""S3 exception provenance at a deferred aux boundary, finite no-time."""
import ast,hashlib,json
from dataclasses import replace
from pathlib import Path
B=Path(__file__).parent
source=(B.parent/'task040/deferred_square.py').read_text()
tree=ast.parse(source);prefix=[]
for node in tree.body:
 if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='rows' for t in node.targets):break
 prefix.append(node)
env={'__file__':str(B.parent/'task040/deferred_square.py')}
exec(compile(ast.Module(body=prefix,type_ignores=[]),'<frozen fixture imports>','exec'),env)
outer=next(n for n in tree.body if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='scope')
env['scope']='global'
before_carrier=[]
for n in outer.body:
 if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='carrier':inner=n;break
 before_carrier.append(n)
exec(compile(ast.Module(body=before_carrier,type_ignores=[]),'<one public fixture>','exec'),env)
env['carrier']='compat';env['started']=env['time'].monotonic();setup=[]
for n in inner.body:
 if isinstance(n,ast.For) and isinstance(n.target,ast.Tuple):break
 setup.append(n)
exec(compile(ast.Module(body=setup,type_ignores=[]),'<one carrier setup>','exec'),env)
engine=env['engine'];pos=env['pos'];p=env['p'];ids=env['ids']
action,binding=next((a,b) for a,b in env['selected'] if b.pattern.name=='pre_expiry_token')
missing=dict(pos.aux_state);missing[(ids['source_token'],-1)]=None
states=[('normal',pos),('missing',replace(pos,aux_state=tuple(sorted(missing.items()))))]
S=type(engine);saved=S._transition;rows=[]
try:
 for label,current in states:
  env['stopped']();parent=repr(current);direct=[]
  try:p.baseline(engine,current,action,binding,lambda:direct.append(len(direct)+1))
  except RuntimeError as exc:assert label=='missing' and str(exc)=='set_token ref unresolved'
  assert direct
  for stop in (None,1,len(direct)):
   arms=[]
   for fn in (p.baseline,p.candidate):
    S._transition=fn;seen=[];fault=RuntimeError('set_token ref unresolved');prior=len(env['hits'])
    def checkpoint():
     seen.append(len(seen)+1)
     if len(seen)==stop:raise fault
    try:
     child=engine._trial_child_if_s3_legal(binding.pattern,current,action,binding,checkpoint)
     result={'status':'rejected' if child is None else 'child','child':repr(child)}
     assert stop is None
    except RuntimeError as exc:
     assert stop is not None and exc is fault
     result={'status':'checkpoint_exception','same_object':True,'message':str(exc)}
    assert repr(current)==parent
    if fn is p.candidate:assert env['hits'][prior:]==[binding.pattern.pattern_id]
    arms.append((result,seen))
   assert arms[0]==arms[1]
   if stop is None:assert arms[0][0]['status']==('child' if label=='normal' else 'rejected')
   rows.append(dict(state=label,fault_checkpoint=stop,last_direct_checkpoint=len(direct),
    result=arms[0][0],callbacks=arms[0][1],actual_compiled_hit=True,full_parent_unchanged=True))
finally:S._transition=saved
out=dict(complete=True,scope='6realS3 pairs +2direct baseline boundary controls; global compatibility fixture only',
 fixture_source_sha256=hashlib.sha256((B.parent/'task040/deferred_square.py').read_bytes()).hexdigest(),
 rows=rows,decision='Identical error text is not the classifier: transition checkpoint provenance preserves exact RuntimeError while missing token is S3-rejected. New shared deferred-aux boundary finite pass, not universal exception safety or performance.',
 limits='Fixture imports/setup compile only one global/compat case and invoke ordinary semantic initialization/legal binding checks. No replay of Task04012comparison loop; no search,C-provider,timing or allocation-failure claim.')
(B/'checkpoint_provenance.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
print('S3 provenance6pairs pass: semantic missing token rejected; identical-text RuntimeError exact callbacks propagate')
