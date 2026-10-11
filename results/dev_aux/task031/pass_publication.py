"""Pass publication is a distinct supported seam, no caller timing."""
import ast,collections,json,sys,time
from dataclasses import replace
from pathlib import Path
B=Path(__file__).parent
t=ast.parse((B.parent/'task023/same_kind_operands.py').read_text(encoding='utf-8'));prefix=[]
for n in t.body:
 if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='out' for x in n.targets):break
 prefix.append(n)
e={'__file__':str(B.parent/'task023/same_kind_operands.py')};exec(compile(ast.Module(body=prefix,type_ignores=[]),'<public fixture>','exec'),e)
f=e['env'];m=f['p'].m
observer_ast=ast.parse((B.parent/'task027/physical_profile.py').read_text(encoding='utf-8'))
functions=[n for n in observer_ast.body if isinstance(n,ast.FunctionDef) and n.name in ('consumer','trial','transition','init','freeze')]
original={'transition':m.SemanticEngine._transition,'trial':m.SemanticEngine._trial_child_if_s3_legal,'init':m._WorkingPosition.__init__,'freeze':m._WorkingPosition.to_position}
pass_original=m.SemanticEngine.transition_pass
rows=[]
for enabled in (False,True):
 compiled=f['compile_semantic_ruleset'](replace(e['rules'],pass_enabled=enabled))
 for carrier in ('compat','pure'):
  f['stopped']()
  c=compiled if carrier=='compat' else f['CompiledSemanticRuleset'](ir=compiled.ir,support=compiled.support)
  engine=f['semantic_engine_for'](c);initial=f['GameSession'](c).state.position
  slot=next(x for x in c.ir.aux_slots if x.value_kind=='bool')
  pos=replace(initial,aux_state=(((slot.slot_id,-1),1),))
  assert not engine.in_check(pos,pos.side_to_move)
  before=repr(pos);normal=engine.transition_pass(pos);legal=engine.pass_is_legal(pos)
  env={'sys':sys,'time':time,'saved':dict(original),'stage':'finite-pass','stack':[],
    'rows':collections.defaultdict(collections.Counter),'counts':collections.Counter(),'orphan':collections.Counter()}
  exec(compile(ast.Module(body=functions,type_ignores=[]),'<exact physical observers>','exec'),env)
  witness=[]
  def pass_witness(self,*args,**kw):
   witness.append('entry');value=pass_original(self,*args,**kw);witness.append('return');return value
  try:
   m.SemanticEngine._transition=env['transition'];m.SemanticEngine._trial_child_if_s3_legal=env['trial']
   m._WorkingPosition.__init__=env['init'];m._WorkingPosition.to_position=env['freeze']
   m.SemanticEngine.transition_pass=pass_witness
   child=engine.transition_pass(pos)
   observed_legal=engine.pass_is_legal(pos)
  finally:
   m.SemanticEngine._transition=original['transition'];m.SemanticEngine._trial_child_if_s3_legal=original['trial']
   m._WorkingPosition.__init__=original['init'];m._WorkingPosition.to_position=original['freeze']
   m.SemanticEngine.transition_pass=pass_original
  assert child==normal and child is not pos and child.board is pos.board and child.hands is pos.hands
  assert child.side_to_move==1-pos.side_to_move and dict(child.aux_state)[(slot.slot_id,-1)]==0
  assert legal==observed_legal==enabled and repr(pos)==before
  assert not env['counts'] and not env['stack']
  expected=2 if enabled else 1
  assert witness==['entry','return']*expected
  rows.append({'pass_enabled':enabled,'carrier':carrier,'pass_legality':legal,'actual_pass_entries_returns':expected,
    'physical_method_counts':dict(env['counts']),'new_immutable_child':True,'board_hands_shared':True,
    'aux1_to0':True,'same_normal_observed_child':True,'full_parent_unchanged':True})
out={'complete':True,'scope':'four declared pass-enabled/disabled x compat/pure controls; low-level direct unchecked pass plus public pass legality; no timing or Runtime history claim',
 'rows':rows,'decision':'WorkingPosition clocks are not all generated-domain Position publication clocks: opt-in semantic pass bypasses them, reuses board/hands and expires aux. Frozen western_chess has pass disabled, so this does not overturn its finite DEFER.',
 'limits':'Direct transition_pass is unchecked even when pass disabled; disabled control public pass_is_legal false. No claim that these calls represent primary weighted root.'}
(B/'pass_publication.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out,indent=2))
