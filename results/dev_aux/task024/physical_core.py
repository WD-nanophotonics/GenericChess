"""Physical semantic transitions versus selected frontier work, not timing."""
import ast,json,sys,time,collections
from pathlib import Path
B=Path(__file__).parent
tree=ast.parse((B.parent/'task017/hybrid_routes.py').read_text(encoding='utf-8'));prefix=[]
for node in tree.body:
 if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='rows' for t in node.targets):break
 prefix.append(node)
e={'__file__':str(B.parent/'task017/hybrid_routes.py')}
exec(compile(ast.Module(body=prefix,type_ignores=[]),'<declared setup only>','exec'),e)
S=e['SemanticEngine'];R=e['R'];P=e['P'];pm=e['pm'];native=e['native_module']
saved_transition=S._transition
compiled=e['compile_ruleset_for_execution'](e['replace'](e['build_builtin_ruleset']('standard_shogi'),max_ply=2))
pure=e['CompiledSemanticRuleset'](ir=compiled.ir,support=compiled.support)
rows=[];start=time.monotonic()
try:
 P.supports_position=e['ns']['supports_position'];R.legal_actions=e['frontier'];R.attach_stats=e['attach']
 for requested in (False,True):
  signatures=[]
  for measured in ((False,True) if not requested else (True,False)):
   e['stopped']();assert time.monotonic()-start<120
   e['events']=[];e['active_event']=None;e['runtimes']=[];captured=[];entries=collections.Counter();returns=collections.Counter();outside=collections.Counter()
   def transition(self,*args,**kw):
    caller=sys._getframe(1).f_code.co_name;entries[caller]+=1
    if e['active_event'] is None:outside[caller]+=1
    value=saved_transition(self,*args,**kw);returns[caller]+=1;return value
   S._transition=transition if measured else saved_transition
   native.semantic_transient_legal_actions=e['native'] if measured else e['native_original']
   S.iter_legal_action_bindings=e['core'] if measured else e['core_original']
   def factory():
    stats=e['SearchStatistics']();captured.append(stats);return stats
   pm.SearchStatistics=factory
   session=e['GameSession'](pure);before=session.state
   decision=e['AlphaBetaPlayer'](pure,evaluator_override=e['Material']('shogi'),use_disk_cache=False,use_tt=False,use_ordering=False,use_native_semantic_legality=requested,tuning=e['SearchTuning'](use_root_tactical=False)).choose_action(session,e['SearchLimits'](max_depth=2,max_nodes=2048,max_time_seconds=10,quiescence_max_depth=0,quiescence_hard_max_depth=0))
   assert session.state is before and decision.completed_depth==2
   rt,root=e['runtimes'][0];rt.assert_balanced();assert e['state'](rt)==root
   stats=e['clean'](e['record_value'](captured[0]));d=e['clean'](e['record_value'](decision))
   ignored={'C_entries','C_returns','Core_iterator_entries','Core_iterator_yields'}
   trace=[{k:v for k,v in ev.items() if k not in ignored} for ev in e['events']]
   signatures.append((d,stats,trace))
   if measured:assert entries==returns and outside['_push_impl']==rt.pushes and sum(entries.values())>=rt.pushes
   rows.append(dict(native_requested=requested,measured=measured,decision=d,stats=stats,core_transition_entries=dict(entries),core_transition_returns=dict(returns),outside_frontier_transition_entries=dict(outside),selected_Core_frontiers=sum(ev['Core_iterator_entries'] for ev in e['events']),actual_C_returns=sum(ev['C_returns'] for ev in e['events']),formal_pushes=rt.pushes,root_multiset_restored=True))
  assert signatures[0]==signatures[1]
finally:
 S._transition=saved_transition;S.iter_legal_action_bindings=e['core_original']
 native.semantic_transient_legal_actions=e['native_original'];R.legal_actions=e['frontier_original'];R.attach_stats=e['attach_original'];P.supports_position=e['support_original'];pm.SearchStatistics=e['factory_original']
out=dict(complete=True,scope='four changed-measurement non-time callers; physical Core semantic dispatch by caller, not C internal primitives',rows=rows)
(B/'physical_core.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
for r in rows:
 if r['measured']:print(r['native_requested'],r['core_transition_entries'],r['outside_frontier_transition_entries'],'Core-frontiers',r['selected_Core_frontiers'],'C',r['actual_C_returns'],'pushes',r['formal_pushes'])
