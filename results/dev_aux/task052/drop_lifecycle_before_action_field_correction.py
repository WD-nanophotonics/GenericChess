"""Public captured-base drop lifecycle, finite frozen private shared candidate."""
import ast,hashlib,json,time
from pathlib import Path
B=Path(__file__).parent;fixture=B.parent/'task048/public_core_history.py';prefix=[]
for n in ast.parse(fixture.read_text()).body:
 if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='saved' for t in n.targets):break
 prefix.append(n)
env={'__file__':str(fixture)};exec(compile(ast.Module(body=prefix,type_ignores=[]),'<declarations only>','exec'),env)
d=env['env'];raw=d['_semantic_ruleset']((d['_king_type'](),d['A'],d['BT'],d['C']),(d['action'],),n=4,rows=tuple(tuple(d['board'][i:i+4]) for i in range(0,16,4)),drop_all_true=('A',))
base=d['compile_semantic_ruleset'](raw);S=env['S'];p=env['p'];saved=S._transition;rows=[];started=time.monotonic()
try:
 for carrier in ('compat','pure'):
  c=base if carrier=='compat' else env['CompiledSemanticRuleset'](ir=base.ir,support=base.support)
  pid=next(x.pattern_id for x in c.ir.patterns if x.name=='change_type');p.prepare(c);hits=[]
  for pattern_id,(pattern,fn) in list(p.plans.items()):
   def hit(*args,_pid=pattern_id,_fn=fn,**kw):hits.append(_pid);return _fn(*args,**kw)
   p.plans[pattern_id]=(pattern,hit)
  arms=[]
  for fn in (p.baseline,p.candidate):
   env['env']['stopped']();assert time.monotonic()-started<120
   S._transition=fn;state=env['initial_state'](c);trace=[];actions=[];drop_pid=None
   for step in (1,2,3,4):
    before=repr(state);frontier=env['legal_actions'](state,c)
    if step==1:chosen=[a for a in frontier if getattr(a,'pattern_id',None)==pid and a.from_square==env['Square'](1,1) and a.to_square==env['Square'](1,2)]
    elif step==2:chosen=[a for a in frontier if getattr(a,'actor_type_id',None)=='C' and getattr(a,'from_square',None)==env['Square'](2,2) and a.to_square==env['Square'](1,2)]
    elif step==3:chosen=[a for a in frontier if getattr(a,'actor_type_id',None)=='K' and getattr(a,'from_square',None)==env['Square'](0,0) and a.to_square==env['Square'](0,1)]
    else:chosen=[a for a in frontier if env['action_to_dict'](a)['kind']=='semantic_drop' and a.type_id=='A' and a.to_square==env['Square'](1,1)]
    assert len(chosen)==1,(step,chosen);action=chosen[0];prior=len(hits)
    child=env['apply_action'](state,action,c);assert repr(state)==before
    if step==2:assert dict(child.position.hands[1].counts).get('A')==1
    if step==4:
     drop_pid=action.pattern_id;piece=child.position.board[5]
     assert (piece.owner,piece.base_type_id,piece.current_type_id,piece.promoted)==(1,'A','A',False)
     assert dict(child.position.hands[1].counts).get('A',0)==0
     if fn is p.candidate:assert drop_pid in hits[prior:]
    actions.append(env['action_to_dict'](action));trace.append(dict(step=step,action=actions[-1],child=repr(child)))
    state=child
   assert len(state.history)==5 and [h.actor for h in state.history]==[-1,0,1,0,1]
   replay=env['initial_state'](c)
   for item in actions:replay=env['apply_action'](replay,env['action_from_dict'](item),c)
   assert replay==state;arms.append(dict(trace=trace,final=repr(state),full_parents_unchanged=True,typed_replay_same_complete_state=True))
  assert arms[0]==arms[1];rows.append(dict(carrier=carrier,result=arms[0],candidate_drop_pattern=drop_pid,candidate_drop_calls=hits.count(drop_pid),candidate_total_calls=len(hits)))
finally:S._transition=saved
out=dict(complete=True,fixture_source_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),rows=rows,scope='2public4ply pairs/4typed replays32applies;public drop masks enabled at compilation;no search or timing')
(B/'drop_lifecycle.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
print('public drop lifecycle2pairs/4typed replays32applies pass')
