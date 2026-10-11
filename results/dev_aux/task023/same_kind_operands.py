"""Identical kind sequence, distinct public operands; no code-template adoption."""
import ast,json
from dataclasses import replace
from pathlib import Path
B=Path(__file__).parent
tree=ast.parse((B.parent/'task019/effect_composition.py').read_text(encoding='utf-8'));prefix=[]
for node in tree.body:
 if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='out' for t in node.targets):break
 prefix.append(node)
env={'__file__':str(B.parent/'task019/effect_composition.py')}
exec(compile(ast.Module(body=prefix,type_ignores=[]),'<fixture construction>','exec'),env)
p=env['p'];base=p.baseline
C=env['PieceType']('C','C',(env['LeapAtom']((-1,0)),))
effects=env['effects'];ref=env['ref'];E=env['RuleActionEffect'];T=env['RuleTypeRef']
first=replace(env['action'],name='same_kind_first')
second=replace(env['action'],name='same_kind_second',effects=(effects[0],replace(effects[1],to_ref=ref('fixed',square=(3,0))),replace(effects[2],type_ref=T('explicit',type_id='C')),replace(effects[3],value=0)))
rules=env['_semantic_ruleset']((env['_king_type'](),env['actor'],env['target'],C),(first,second),n=4,rows=env['rules'].initial_position)
compiled=env['compile_semantic_ruleset'](rules)
out={'complete':False,'scope':'four new same-kind/different-operand controls; existing per-pattern prototype only; no shared-template acceptance','rows':[]}
for carrier in ('compat','pure'):
 env['stopped']()
 c=compiled if carrier=='compat' else env['CompiledSemanticRuleset'](ir=compiled.ir,support=compiled.support)
 engine=env['semantic_engine_for'](c);pos=env['GameSession'](c).state.position
 bindings=[(a,b) for a,b in engine.iter_legal_action_bindings(pos) if tuple(e.kind for e in b.pattern.effects)==tuple(e.kind for e in effects)]
 assert len(bindings)==2
 p.prepare(c);hits=[]
 for pid,(pattern,fn) in list(p.plans.items()):
  def wrapped(*args,_pid=pid,_fn=fn,**kw):
   hits.append(_pid);return _fn(*args,**kw)
  p.plans[pid]=(pattern,wrapped)
 children=[]
 for a,b in bindings:
  counts=[0,0];before=len(hits)
  def callback(i):
   def cb():counts[i]+=1
   return cb
  old=base(engine,pos,a,b,callback(0));new=p.candidate(engine,pos,a,b,callback(1))
  assert old==new and counts==[7,7] and hits[before:]==[b.pattern.pattern_id]
  assert pos.board==tuple(env['board']) and pos.side_to_move==0
  label=b.pattern.name
  if label=='same_kind_first':
   assert new.board[5].current_type_id=='B' and new.board[6]==env['board'][2] and new.board[3] is None and dict(new.aux_state)[(0,-1)]==1
  elif label=='same_kind_second':
   assert new.board[5].current_type_id=='C' and new.board[3]==env['board'][2] and new.board[6] is None and dict(new.aux_state)[(0,-1)]==0
  else:raise AssertionError(label)
  children.append(new)
  out['rows'].append({'carrier':carrier,'pattern_id':b.pattern.pattern_id,'effects':[repr(e) for e in b.pattern.effects],'callbacks':counts,'compiled_hits':hits[before:],'child':repr(new),'parent_unchanged':True})
 assert children[0]!=children[1] and children[0].ruleset_fingerprint==children[1].ruleset_fingerprint
out['complete']=True
(B/'same_kind_operands.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print('4 same-kind/different-operand compiled controls pass; actions remain distinct')
