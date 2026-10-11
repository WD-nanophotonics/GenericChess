"""Witness actual compiled/fallback dispatch across same-ID public programs."""
import ast,json,time
from dataclasses import replace
from pathlib import Path
B=Path(__file__).parent
source=(B.parent/'task019/effect_composition.py').read_text(encoding='utf-8')
tree=ast.parse(source);prefix=[]
for node in tree.body:
 if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='out' for t in node.targets):break
 prefix.append(node)
env={'__file__':str(B.parent/'task019/effect_composition.py')}
exec(compile(ast.Module(body=prefix,type_ignores=[]),'<declared fixture only>','exec'),env)
p=env['p'];compile_rules=env['compile_semantic_ruleset'];pure=env['CompiledSemanticRuleset'];engine_for=env['semantic_engine_for'];Session=env['GameSession'];stopped=env['stopped']
original=env['compiled'];equivalent=compile_rules(env['rules'])
different=compile_rules(replace(env['rules'],semantic_actions=(replace(env['action'],effects=(env['effects'][0],),aux_state=()),)))
baseline=p.baseline;out={'complete':False,'scope':'ten finite actual route witnesses; two same-ID public effect programs; no timing or concurrent execution','rows':[]};start=time.monotonic()
for carrier in ('compat','pure'):
 stopped();assert time.monotonic()-start<120
 convert=lambda c:c if carrier=='compat' else pure(ir=c.ir,support=c.support)
 c,e,d=map(convert,(original,equivalent,different))
 engines=list(map(engine_for,(c,e,d)))
 positions=[Session(v).state.position for v in (c,e,d)]
 get=lambda en,pos:next((a,b) for a,b in en.iter_legal_action_bindings(pos) if b.pattern.pattern_id=='sem_00_independent_compound')
 ab,eb,db=[get(en,pos) for en,pos in zip(engines,positions)]
 assert ab[1].pattern is not eb[1].pattern and ab[1].pattern.pattern_id==db[1].pattern.pattern_id
 routes=[]
 def fallback(*args,**kw):
  routes.append('fallback');return baseline(*args,**kw)
 p.baseline=fallback
 def prepare(v):
  # prepare must inspect original function source, not the spy wrapper.
  p.baseline=baseline;p.prepare(v);p.baseline=fallback
  for pid,(pattern,fn) in list(p.plans.items()):
   def compiled_fn(*args,_fn=fn,**kw):
    routes.append('compiled');return _fn(*args,**kw)
   p.plans[pid]=(pattern,compiled_fn)
 prepare(c)
 cases=[('prepared-original',engines[0],positions[0],ab,'compiled'),
 ('equivalent-foreign-carrier',engines[1],positions[1],eb,'fallback'),
 ('equivalent-foreign-pattern',engines[0],positions[0],eb,'fallback')]
 values={}
 for name,en,pos,(a,b),expected in cases:
  routes.clear();counts=[0,0]
  def checkpoint(i):
   def cb():counts[i]+=1
   return cb
  old=baseline(en,pos,a,b,checkpoint(0));new=p.candidate(en,pos,a,b,checkpoint(1))
  assert old==new and counts[0]==counts[1] and routes==[expected]
  values[name]=new;out['rows'].append(dict(carrier=carrier,case=name,actual_routes=list(routes),callbacks=counts,child=repr(new),parent_unchanged=True))
 prepare(d)
 for name,en,pos,(a,b),expected in [('original-after-other-prepare',engines[0],positions[0],ab,'fallback'),('prepared-different-program',engines[2],positions[2],db,'compiled')]:
  routes.clear();counts=[0,0]
  def checkpoint(i):
   def cb():counts[i]+=1
   return cb
  old=baseline(en,pos,a,b,checkpoint(0));new=p.candidate(en,pos,a,b,checkpoint(1))
  assert old==new and counts[0]==counts[1] and routes==[expected]
  values[name]=new;out['rows'].append(dict(carrier=carrier,case=name,actual_routes=list(routes),callbacks=counts,child=repr(new),parent_unchanged=True))
 assert values['prepared-original'].board!=values['prepared-different-program'].board
 assert values['prepared-original']==values['original-after-other-prepare']
 p.baseline=baseline
out['complete']=True
(B/'plan_authority.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print('10 actual route witnesses pass; same IDs preserve distinct original programs')
