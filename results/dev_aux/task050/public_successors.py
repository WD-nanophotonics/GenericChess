"""Separate public child producer, no Task048 executed-loop replay."""
import ast,hashlib,json,time
from pathlib import Path
B=Path(__file__).parent
src=(B.parent/'task048/public_core_history.py').read_text(); tree=ast.parse(src); prefix=[]
for n in tree.body:
 if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='saved' for t in n.targets):break
 prefix.append(n)
env={'__file__':str(B.parent/'task048/public_core_history.py')}
exec(compile(ast.Module(body=prefix,type_ignores=[]),'<declarations only>','exec'),env)
from generic_chess.core.transition import legal_successors
S=env['S'];p=env['p'];base=env['base'];saved=S._transition;rows=[];started=time.monotonic()
try:
 for carrier in ('compat','pure'):
  c=base if carrier=='compat' else env['CompiledSemanticRuleset'](ir=base.ir,support=base.support)
  p.prepare(c);S._transition=p.baseline;root=env['initial_state'](c)
  action=next(a for a in env['legal_actions'](root,c) if getattr(a,'pattern_id',None)==env['pid'] and a.from_square==env['Square'](1,1) and a.to_square==env['Square'](1,2))
  changed=env['apply_action'](root,action,c)
  for label,parent in (('root',root),('transformed',changed)):
   env['env']['stopped']();assert time.monotonic()-started<120
   before=repr(parent);S._transition=p.baseline;old=legal_successors(parent,c);assert repr(parent)==before
   S._transition=p.candidate;new=legal_successors(parent,c);assert repr(parent)==before
   assert old==new
   assert [a for a,ch in new]==env['legal_actions'](parent,c)
   if label=='root':selected=next((a,ch) for a,ch in new if a==action)
   else:selected=next((a,ch) for a,ch in new if getattr(a,'actor_type_id',None)=='C' and a.from_square==env['Square'](2,2) and a.to_square==env['Square'](1,2))
   S._transition=p.baseline;reference=env['apply_action'](parent,selected[0],c)
   assert reference==selected[1] and repr(parent)==before
   rows.append(dict(carrier=carrier,parent=label,children=len(new),ordered_actions=[env['action_to_dict'](a) for a,ch in new],selected_child=repr(selected[1]),full_children_equal=True,public_apply_equal=True,immutable_parent=True))
finally:S._transition=saved
out=dict(complete=True,fixture_source_sha256=hashlib.sha256((B.parent/'task048/public_core_history.py').read_bytes()).hexdigest(),rows=rows,scope='4 public producer pairs and4 selected baseline apply comparisons; no search or timing')
(B/'public_successors.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
print('public legal_successors4pairs/4selected apply comparisons pass')
