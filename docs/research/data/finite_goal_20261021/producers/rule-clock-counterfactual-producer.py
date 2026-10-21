"""Prospective actual-rule clock counterfactual, never extending old outcomes.

Keep each physical prefix/movement/aux rule, change ONLY max_ply to5/7/8. All
reference frontiers must be actual terminals; one shared150000node/90sec fuse.
"""
from pathlib import Path
from dataclasses import replace
import json,time
from generic_chess.rules.schema import ruleset_from_dict,ruleset_to_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.core.transition import legal_successors
from generic_chess.ai.alphabeta import search
from scripts.price_regions import CONFIG,Budget,TreeLimit,build_tree,response,partition
from scripts.price_regions_goal import NoHeuristicFrontier
from scripts.research_record import record_value,write_record
base=Path('artifacts/price-regions-20261021');sources=[('source3x3',json.loads((base/'goal-census.json').read_text())),('emptyrow3x4',json.loads((base/'empty-row-census.json').read_text()))]
out=base/'rule-clock-counterfactual.json'
if out.exists():raise FileExistsError(out)
result=dict(scope=__doc__,declaration=dict(new_max_ply=[5,7,8],source_max_ply=6,matched_prefixes_each=4,reference_nodes=150000,reference_seconds=90,
    d2_tree_nodes=30000,d2_tree_seconds=90,goal='Find actual goal aliasing or retained scoped no-change; no extra cap after results, WDL imputation, learner or solver.'),worlds=[])
write_record(out,result);refbudget=Budget(90,150000);treebudget=Budget(90,30000);start=time.perf_counter();original=search.reference_minimax

def limited(*args,**kwargs):refbudget.check();return original(*args,**kwargs)
search.reference_minimax=limited
try:
 for label,source in sources:
  oldrule=ruleset_from_dict(source['rule']);oldc=compile_ruleset_for_execution(oldrule)
  for maxply in result['declaration']['new_max_ply']:
   rule=replace(oldrule,max_ply=maxply);c=compile_ruleset_for_execution(rule);world=dict(label=label,max_ply=maxply,rule=ruleset_to_dict(rule),roots=[]);result['worlds'].append(world)
   for index,row in enumerate(source['roots']):
    old=GameSession.replay(oldc,deserialize_game_record(json.dumps(row['record'])));s=GameSession(c)
    for a in old.to_record().actions:s.submit(a)
    assert replace(old.state.position,ruleset_fingerprint=c.ruleset_fingerprint)==s.state.position
    assert old.state.ply_count==s.state.ply_count and len(old.state.history)==len(s.state.history)
    dest=dict(index=index,record=json.loads(serialize_game_record(s.to_record())),status=record_value(s.state.terminal_status),true_actions=[]);world['roots'].append(dest)
    if s.state.terminal_status.is_terminal:continue
    oldtree=build_tree(old.state,oldc,2,old.state.position.side_to_move,treebudget,set())
    tree=build_tree(s.state,c,2,s.state.position.side_to_move,treebudget,set());dest['identical_full_D2_material_tree']=tree==oldtree
    # Test equality of the complete finite tree, not only a chosen scalar score.
    assert tree==oldtree
    for a,child in sorted(legal_successors(s.state,c),key=lambda x:str(x[0])):
     try:
      score,_=limited(child,maxply-child.ply_count,NoHeuristicFrontier(),c,1);score=-score
      dest['true_actions'].append(dict(action=str(a),complete=True,wdl=(score>0)-(score<0),score=score))
     except TreeLimit as exc:
      dest['true_actions'].append(dict(action=str(a),complete=False,wdl=None,reason=str(exc)));dest['incomplete']=True;break
    dest['old_goal_values']={a['action']:a['wdl'] for a in row['true_actions']}
    if not dest.get('incomplete'):
     dest['new_goal_values']={a['action']:a['wdl'] for a in dest['true_actions']};dest['goal_values_changed']=dest['new_goal_values']!=dest['old_goal_values']
    write_record(out,result)
    if dest.get('incomplete'):break
   if world['roots'] and world['roots'][-1].get('incomplete'):break
  if result['worlds'][-1]['roots'][-1].get('incomplete'):break
finally:
 search.reference_minimax=original;result.update(reference_nodes=refbudget.edges,tree_nodes=treebudget.edges,wall_seconds=time.perf_counter()-start);write_record(out,result)
print('nodes',refbudget.edges,'trees',treebudget.edges,'seconds',result['wall_seconds'])
for w in result['worlds']:print(w['label'],w['max_ply'],[(r['index'],r.get('goal_values_changed'),max(r.get('old_goal_values',{}).values(),default=None),max(r.get('new_goal_values',{}).values(),default=None),r.get('incomplete')) for r in w['roots']])
