"""Distinct equivalent carrier fallback, finite public apply."""
import ast,hashlib,json,time
from pathlib import Path
B=Path(__file__).parent;fixture=B.parent/'task048/public_core_history.py';prefix=[]
for n in ast.parse(fixture.read_text()).body:
 if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='saved' for t in n.targets):break
 prefix.append(n)
env={'__file__':str(fixture)};exec(compile(ast.Module(body=prefix,type_ignores=[]),'<declarations only>','exec'),env)
S=env['S'];p=env['p'];base=env['base'];pure=env['CompiledSemanticRuleset'](ir=base.ir,support=base.support)
assert base is not pure and base.ir is pure.ir
saved=S._transition;rows=[];started=time.monotonic()
try:
 for prepared_name,prepared in (('compat',base),('pure',pure)):
  p.prepare(prepared);hits=[]
  for pattern_id,(pattern,fn) in list(p.plans.items()):
   def hit(*args,_pid=pattern_id,_fn=fn,**kw):hits.append(_pid);return _fn(*args,**kw)
   p.plans[pattern_id]=(pattern,hit)
  for used_name,c in (('compat',base),('pure',pure)):
   env['env']['stopped']();assert time.monotonic()-started<120
   S._transition=p.baseline;root=env['initial_state'](c);before=repr(root)
   a=next(a for a in env['legal_actions'](root,c) if getattr(a,'pattern_id',None)==env['pid'] and a.from_square==env['Square'](1,1) and a.to_square==env['Square'](1,2))
   old=env['apply_action'](root,a,c);prior=len(hits)
   S._transition=p.candidate;new=env['apply_action'](root,a,c);used=len(hits)-prior
   assert old==new and repr(root)==before
   assert (used>0)==(c is prepared)
   rows.append(dict(prepared_carrier=prepared_name,used_carrier=used_name,same_ir_object=True,owned_semantic=c is prepared,generated_calls=used,full_child_equal=True,immutable_parent=True))
finally:S._transition=saved
out=dict(complete=True,fixture_source_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),shared_source_sha256=hashlib.sha256((B.parent/'task025/compiled_effect_shared.py').read_bytes()).hexdigest(),rows=rows,scope='4public apply pairs;different equivalent carriers must fall back, no cost/search claim')
(B/'carrier_fallback.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
print('carrier fallback4public apply pairs pass;owned generated,borrowed baseline')
