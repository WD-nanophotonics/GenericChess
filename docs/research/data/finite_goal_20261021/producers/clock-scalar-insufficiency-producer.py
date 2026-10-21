"""Clock scalar alone cannot separate two equal material frontier actions."""
from pathlib import Path
import json
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.transition import legal_successors
from scripts.research_record import write_record,record_value
base=Path('artifacts/price-regions-20261021');source=json.loads((base/'rule-clock-counterfactual.json').read_text());w=next(w for w in source['worlds'] if w['label']=='emptyrow3x4' and w['max_ply']==7);row=next(r for r in w['roots'] if r['index']==3)
c=compile_ruleset_for_execution(ruleset_from_dict(w['rule']));root=GameSession.replay(c,deserialize_game_record(json.dumps(row['record'])));owner=root.state.position.side_to_move
out=base/'clock-scalar-insufficiency.json'
if out.exists():raise FileExistsError(out)
rows=[]
for action,child in sorted(legal_successors(root.state,c),key=lambda x:str(x[0])):
 replies=[]
 for reply,leaf in sorted(legal_successors(child,c),key=lambda x:str(x[0])):
  assert not leaf.terminal_status.is_terminal and leaf.ply_count==4
  v=tuple(sum((1 if p.owner==owner else -1) for p in leaf.position.board if p and p.current_type_id==tid) for tid in ('H','B'))
  replies.append(dict(action=str(reply),material_vector=v,absolute_ply=4,remaining_actual_rule_plies=3))
 rows.append(dict(action=str(action),actual_goal_wdl=row['new_goal_values'][str(action)],reply_features=replies,distinct_material_vectors=sorted(set(tuple(x['material_vector']) for x in replies))))
winning=next(x for x in rows if x['actual_goal_wdl']==1);other=next(x for x in rows if x['actual_goal_wdl']==0 and x['distinct_material_vectors']==winning['distinct_material_vectors'])
assert winning['distinct_material_vectors']==other['distinct_material_vectors']==[(1,1)]
write_record(out,dict(scope='One finite new3x4/max_ply7 root only, material boardH/B and any clock-only scalar/additive linear terms; allD2frontiers nonterminal at same absoluteply4.',
 record=row['record'],actions=rows,inseparable_pair=[winning['action'],other['action']],
 inference='Both action values are h+b+g(clock) for every h,b and clock-only additive g; even clock-conditioned h,b remain identical on this root. No such linear representation can make the winning action strictly better than this drawing action. This does not prove a generic learned evaluator impossible or prescribe tie breaking.',
 next_question='A small full-state/rule-context interaction may distinguish the actual board relation. Check scope and cost on existing data before any future learner task; no fit or default change here.'))
print('inseparable',winning['action'],other['action']);print([(x['action'],x['actual_goal_wdl'],x['distinct_material_vectors']) for x in rows])
