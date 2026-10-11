"""Outer Core typed transform/base capture witness; finite, no search/timing."""
import ast,hashlib,importlib.util,json,sys,time
from pathlib import Path
B=Path(__file__).parent;ROOT=B.resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from generic_chess.core.actions import action_from_dict,action_to_dict
from generic_chess.core.coordinates import Square
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import initial_state,apply_action
from generic_chess.core.semantic_executor import SemanticEngine as S
from generic_chess.rules.ir import CompiledSemanticRuleset
src=(B.parent/'task045/current_type_child.py').read_text();tree=ast.parse(src);prefix=[]
for n in tree.body:
 if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='records' for t in n.targets):break
 prefix.append(n)
env={'__file__':str(B.parent/'task045/current_type_child.py')}
exec(compile(ast.Module(body=prefix,type_ignores=[]),'<frozen public declarations>','exec'),env)
base=env['compiled'];pid=next(x.pattern_id for x in base.ir.patterns if x.name=='change_type')
spec=importlib.util.spec_from_file_location('own_public_core_shared',B.parent/'task025/compiled_effect_shared.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
saved=S._transition;rows=[];started=time.monotonic()
for carrier in ('compat','pure'):
 c=base if carrier=='compat' else CompiledSemanticRuleset(ir=base.ir,support=base.support)
 p.prepare(c);hits=[]
 for pattern_id,(pattern,fn) in list(p.plans.items()):
  def hit(*args,_pid=pattern_id,_fn=fn,**kw):hits.append(_pid);return _fn(*args,**kw)
  p.plans[pattern_id]=(pattern,hit)
 arms=[]
 try:
  for fn in (p.baseline,p.candidate):
   env['stopped']();assert time.monotonic()-started<120
   S._transition=fn;prior=len(hits);state=initial_state(c);root=repr(state);trace=[];actions=[]
   for step in (1,2):
    before=repr(state);frontier=legal_actions(state,c)
    if step==1:
     selected=[a for a in frontier if getattr(a,'pattern_id',None)==pid and a.from_square==Square(1,1) and a.to_square==Square(1,2)]
    else:
     selected=[a for a in frontier if getattr(a,'actor_type_id',None)=='C' and a.from_square==Square(2,2) and a.to_square==Square(1,2)]
    assert len(selected)==1;action=selected[0]
    child=apply_action(state,action,c);assert repr(state)==before
    assert child.ply_count==step and child.history[-1].position_key==repetition_identity_key(child.position,c)
    assert json.loads(child.history[-1].action_signature)==action_to_dict(action)
    if step==1:
     piece=child.position.board[9];assert (piece.base_type_id,piece.current_type_id,piece.promoted)==('A','B',True)
    else:
     piece=child.position.board[9];assert (piece.owner,piece.base_type_id,piece.current_type_id)==(1,'C','C')
     hand=dict(child.position.hands[1].counts)
     assert hand.get('A')==1 and hand.get('B',0)==0 and child.position.board[5] is None
    actions.append(action_to_dict(action))
    trace.append(dict(step=step,frontier=[action_to_dict(a) for a in frontier],chosen=actions[-1],child=repr(child)))
    state=child
   assert len(state.history)==3 and [h.actor for h in state.history]==[-1,0,1]
   assert sum(n for key,n in state.repetition_counts)==3
   replay=initial_state(c)
   for item in actions:replay=apply_action(replay,action_from_dict(item),c)
   assert replay==state
   if fn is p.candidate:assert len(hits)>prior
   else:assert len(hits)==prior
   arms.append(dict(root=root,trace=trace,final=repr(state),typed_replay_same_complete_state=True,
    full_parents_unchanged=True))
  assert arms[0]==arms[1]
  rows.append(dict(carrier=carrier,result=arms[0],candidate_generated_calls=len(hits)))
 finally:S._transition=saved
out=dict(complete=True,fixture_source_sha256=hashlib.sha256((B.parent/'task045/current_type_child.py').read_bytes()).hexdigest(),
 shared_source_sha256=hashlib.sha256((B.parent/'task025/compiled_effect_shared.py').read_bytes()).hexdigest(),
 rows=rows,scope='2carrier normal2-ply Core pairs;4typed replay flows;8totalflows16public applies;private transition only, original attack dispatch',
 limits='Public initialization/frontier/membership/terminal/history work included. No SearchPathRuntime, TT, search, callback exception, OOM, Native, timing or all-domain proof. Prior b410 exceptional occurrence failures are unchanged.')
(B/'public_core_history.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
print('public Core2pairs/4typed replays pass;16applies; transformed capture stores base A, full history agrees')
