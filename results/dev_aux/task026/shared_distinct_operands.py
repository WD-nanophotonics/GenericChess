"""Immutable shared-code candidate; actual operands and precise callback boundaries."""
import ast,importlib.util,json,time
from pathlib import Path
B=Path(__file__).parent
tree=ast.parse((B.parent/'task023/same_kind_operands.py').read_text(encoding='utf-8'));prefix=[]
for n in tree.body:
 if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='out' for t in n.targets):break
 prefix.append(n)
env={'__file__':str(B.parent/'task023/same_kind_operands.py')}
exec(compile(ast.Module(body=prefix,type_ignores=[]),'<frozen public fixture only>','exec'),env)
fixture=env['env'];compiled=env['compiled']
spec=importlib.util.spec_from_file_location('immutable_shared',B.parent/'task025/compiled_effect_shared.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
out={'complete':False,'candidate_pin':'80a6bd06d5e093cd29ad51c7a01cc6719b357533','shared_source_sha256':'bceefeec2483a0b43e6a04cc42072cfbe1a62c0049c9b88314732dd210b632a7','scope':'new shared candidate only, four same-kind distinct-operand cells plus56 precise callback faults; no timing','rows':[]}
start=time.monotonic()
for carrier in ('compat','pure'):
 fixture['stopped']();assert time.monotonic()-start<120
 c=compiled if carrier=='compat' else fixture['CompiledSemanticRuleset'](ir=compiled.ir,support=compiled.support)
 engine=fixture['semantic_engine_for'](c);pos=fixture['GameSession'](c).state.position
 bindings=[(a,b) for a,b in engine.iter_legal_action_bindings(pos) if tuple(e.kind for e in b.pattern.effects)==('move','shift','set_current_type','set_bool')]
 assert len(bindings)==2;p.prepare(c)
 assert p.plans[bindings[0][1].pattern.pattern_id][1] is p.plans[bindings[1][1].pattern.pattern_id][1]
 metadata={k:v for k,v in p.metadata.items() if k!='prepare_seconds'};hits=[]
 for pid,(pattern,fn) in list(p.plans.items()):
  def wrapped(*args,_pid=pid,_fn=fn,**kw):
   hits.append(_pid);return _fn(*args,**kw)
  p.plans[pid]=(pattern,wrapped)
 children=[]
 for a,b in bindings:
  before=len(hits);counts=[0,0]
  def callback(i):
   def cb():counts[i]+=1
   return cb
  old=p.baseline(engine,pos,a,b,callback(0));new=p.candidate(engine,pos,a,b,callback(1))
  assert old==new and counts==[7,7] and hits[before:]==[b.pattern.pattern_id]
  assert pos.board==tuple(fixture['board']) and pos.side_to_move==0
  children.append(new);fault_cells=0
  for stop in range(1,8):
   for fn in (p.baseline,p.candidate):
    fault=RuntimeError('one shared-template callback');seen=[]
    def checkpoint():
     seen.append(len(seen)+1)
     if len(seen)==stop:raise fault
    try:fn(engine,pos,a,b,checkpoint)
    except RuntimeError as exc:assert exc is fault and len(seen)==stop
    else:raise AssertionError('checkpoint omitted')
    assert pos.board==tuple(fixture['board']);fault_cells+=1
  out['rows'].append({'carrier':carrier,'pattern_id':b.pattern.pattern_id,'metadata':metadata,'same_generated_template_object':True,'normal_actual_compiled_hit':b.pattern.pattern_id,'callbacks':counts,'callback_fault_cells':fault_cells,'child':repr(new),'parent_unchanged':True})
 assert children[0]!=children[1] and children[0].ruleset_fingerprint==children[1].ruleset_fingerprint
out['complete']=True
(B/'shared_distinct_operands.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print('new immutable shared candidate:4 distinct-operand transitions+56 callback faults pass; actual same template')
