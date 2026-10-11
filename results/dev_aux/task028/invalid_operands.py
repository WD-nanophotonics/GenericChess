"""New finite shared-template invalid operand controls, no timing."""
import ast,importlib.util,json,time
from dataclasses import replace
from pathlib import Path
B=Path(__file__).parent
tree=ast.parse((B.parent/'task023/same_kind_operands.py').read_text(encoding='utf-8'));prefix=[]
for node in tree.body:
 if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='out' for t in node.targets):break
 prefix.append(node)
env={'__file__':str(B.parent/'task023/same_kind_operands.py')}
exec(compile(ast.Module(body=prefix,type_ignores=[]),'<frozen fixture only>','exec'),env)
f=env['env'];compiled=env['compiled']
spec=importlib.util.spec_from_file_location('immutable_shared',B.parent/'task025/compiled_effect_shared.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
rows=[];started=time.monotonic()
for carrier in ('compat','pure'):
 f['stopped']();assert time.monotonic()-started<120
 c=compiled if carrier=='compat' else f['CompiledSemanticRuleset'](ir=compiled.ir,support=compiled.support)
 engine=f['semantic_engine_for'](c);root=f['GameSession'](c).state.position
 selected=[(a,b) for a,b in engine.iter_legal_action_bindings(root) if tuple(e.kind for e in b.pattern.effects)==('move','shift','set_current_type','set_bool')]
 assert len(selected)==2;p.prepare(c)
 assert p.plans[selected[0][1].pattern.pattern_id][1] is p.plans[selected[1][1].pattern.pattern_id][1]
 hits=[]
 for pid,(pattern,fn) in list(p.plans.items()):
  def wrapped(*args,_pid=pid,_fn=fn,**kw):
   hits.append(_pid);return _fn(*args,**kw)
  p.plans[pid]=(pattern,wrapped)
 for action,binding in selected:
  target=6 if binding.pattern.name=='same_kind_first' else 3
  for kind in ('valid','missing_shift_actor','wrong_shift_owner','occupied_shift_target','missing_mover'):
   board=list(root.board)
   if kind=='missing_shift_actor':board[2]=None
   if kind=='wrong_shift_owner':board[2]=replace(board[2],owner=1)
   if kind=='occupied_shift_target':board[target]=f['Piece'](0,'B','B')
   if kind=='missing_mover':board[1]=None
   pos=replace(root,board=tuple(board));before=repr(pos);results=[];calls=[]
   for fn in (p.baseline,p.candidate):
    checkpoints=[];prior=len(hits)
    try:
     child=fn(engine,pos,action,binding,lambda:checkpoints.append(len(checkpoints)+1))
     result={'status':'child','child':repr(child)}
    except RuntimeError as exc:
     result={'status':'rejection','exception_type':type(exc).__name__,'message':str(exc)}
    assert repr(pos)==before
    results.append(result);calls.append(len(checkpoints))
    if fn is p.candidate:assert hits[prior:]==[binding.pattern.pattern_id]
   assert results[0]==results[1] and calls[0]==calls[1]
   assert (results[0]['status']=='child')==(kind=='valid')
   # Separate S3/public contract: the original transition guard rejects these
   # inputs; _trial converts its RuntimeError to no legal child, both arms.
   s3=[];membership=[];prior=len(hits)
   saved=p.m.SemanticEngine._transition
   try:
    for installed in (p.baseline,p.candidate):
     p.m.SemanticEngine._transition=installed
     child=engine._trial_child_if_s3_legal(binding.pattern,pos,action,binding)
     s3.append(repr(child))
     membership.append(action in tuple(engine.iter_legal_actions(pos)))
   finally:p.m.SemanticEngine._transition=saved
   assert s3[0]==s3[1] and membership[0]==membership[1]==(kind=='valid')
   assert repr(pos)==before
   rows.append({'carrier':carrier,'pattern':binding.pattern.name,'cell':kind,'result':results[0],
    'callbacks':calls,'direct_actual_candidate_hit':True,'s3_equal':True,'public_membership':membership,
    'parent_full_repr_unchanged':True})
out={'complete':True,'candidate_pin':'80a6bd06d5e093cd29ad51c7a01cc6719b357533',
 'new_scope':'20 pairs:4positive16negative shared-template distinct dynamic inputs; direct transition plus S3/public membership; frozen action/binding intentionally reused for negative direct seam',
 'rows':rows,'limits':'Finite public fixture; no generalized invalid operand guarantee or first per-pattern cost claim, no callback fault rerun.'}
(B/'invalid_operands.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print('20 direct+S3/public pairs agree,4positive16rejected; actual shared path and full parents stable')
for row in rows:print(row['carrier'],row['pattern'],row['cell'],row['callbacks'],row['result']['status'])
