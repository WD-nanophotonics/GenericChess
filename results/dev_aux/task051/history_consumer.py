"""Finite direct no-progress consumer; no policy-enabled terminal claim."""
import ast,hashlib,json,time
from pathlib import Path
B=Path(__file__).parent
fixture=B.parent/'task048/public_core_history.py';prefix=[]
for n in ast.parse(fixture.read_text()).body:
 if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='saved' for t in n.targets):break
 prefix.append(n)
env={'__file__':str(fixture)};exec(compile(ast.Module(body=prefix,type_ignores=[]),'<declarations only>','exec'),env)
from generic_chess.rules.compiled import CompiledNoProgressDraw as Policy
from generic_chess.core.adjudication import no_progress_draw_status,IncompleteAdjudicationHistoryError
S=env['S'];p=env['p'];base=env['base'];saved=S._transition;rows=[];started=time.monotonic()
try:
 for carrier in ('compat','pure'):
  c=base if carrier=='compat' else env['CompiledSemanticRuleset'](ir=base.ir,support=base.support)
  p.prepare(c);arms=[]
  for fn in (p.baseline,p.candidate):
   env['env']['stopped']();assert time.monotonic()-started<120
   S._transition=fn;root=env['initial_state'](c)
   a=next(a for a in env['legal_actions'](root,c) if getattr(a,'pattern_id',None)==env['pid'] and a.from_square==env['Square'](1,1) and a.to_square==env['Square'](1,2))
   changed=env['apply_action'](root,a,c)
   cap=next(a for a in env['legal_actions'](changed,c) if getattr(a,'actor_type_id',None)=='C' and a.from_square==env['Square'](2,2) and a.to_square==env['Square'](1,2))
   captured=env['apply_action'](changed,cap,c);answers=[]
   for label,state,policy,expected in (
    ('transform_reset_A',changed,Policy(1,False,('A',)),None),
    ('transform_reset_B',changed,Policy(1,False,('B',)),'DRAW'),
    ('capture_reset',captured,Policy(1,True),None),
    ('capture_no_reset',captured,Policy(1,False),'DRAW')):
    before=repr(state)
    value=no_progress_draw_status(policy,state.position,state.ply_count,state.repetition_counts,state.history,c)
    assert value==expected and repr(state)==before
    answers.append(dict(case=label,value=value,expected=expected,full_parent_unchanged=True))
   before=repr(captured)
   try:no_progress_draw_status(Policy(1,False),captured.position,captured.ply_count,captured.repetition_counts,captured.history[1:],c)
   except IncompleteAdjudicationHistoryError as exc:error=str(exc)
   else:raise AssertionError('incomplete history accepted')
   assert repr(captured)==before
   arms.append(dict(answers=answers,truncated_history_error=error))
  assert arms[0]==arms[1];rows.append(dict(carrier=carrier,result=arms[0]))
finally:S._transition=saved
out=dict(complete=True,fixture_source_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),rows=rows,scope='8 direct classifier pairs and2 truncated-history rejection pairs; public state construction, no policy-enabled terminal compilation')
(B/'history_consumer.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
print('history consumer8classifier pairs/2truncated history pairs pass')
