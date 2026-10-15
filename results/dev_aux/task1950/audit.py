"""Independent public/literal replay and regret audit of ALL actual price divergences."""
from pathlib import Path
from collections import Counter
import json,time
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_proof_rnb_bridge import actor_state,uci
from scripts.generic_royal_actor import RoyalActor
O=Path('results/dev_aux/task1950')
def run():
 beg=time.perf_counter();pairs=json.loads(Path('results/dev_aux/task1946/result.json').read_text())['pairs'];rows=[json.loads(s) for s in Path('results/dev_aux/task1947/queries.jsonl').read_text().splitlines()];actor=RoyalActor(4);compiled={};leaves=edges=0
 for r in rows:
  pair=pairs[r['pair']];rule=pair['rules']
  if rule not in compiled:compiled[rule]=compile_ruleset_for_execution(deserialize_ruleset(Path(rule).read_text()))
  c=compiled[rule];root=GameSession.replay(c,deserialize_game_record(json.dumps(pair['common_record'])));assert r['role']==pair['role']==root.state.position.side_to_move
  assert not r['complete'] or {v['action'] for v in r['values']}=={uci(a) for a in root.legal_actions()}
  for vector,path in r['leaf_witnesses'].items():
   rr={**pair['common_record'],'actions':pair['common_record']['actions']+path};s=GameSession.replay(c,deserialize_game_record(json.dumps(rr)));assert s.result.status is SessionStatus.ONGOING;v=tuple(sum(1 if p.owner==r['role'] else -1 for p in s.state.position.board if p is not None and p.current_type_id==t) for t in ('R','N'));assert str(v)==vector
   raw=actor_state(root.state)
   for action in deserialize_game_record(json.dumps(rr)).actions[len(pair['common_record']['actions']):]:raw=dict(actor.moves(raw))[uci(action)]
   assert raw==actor_state(s.state);leaves+=1;edges+=len(path)
 index={(r['pair'],r['depth'],r['ratio']):r for r in rows};summary=[];details=[]
 for d in (4,6):
  count=Counter()
  for pair in pairs:
   aa,bb=index.get((pair['pair'],d,'1')),index.get((pair['pair'],d,'2'))
   if aa is None or bb is None or not aa['complete'] or not bb['complete']:count['incomplete']+=1;continue
   count['complete_pairs']+=1;x,y=[a['uci'] for a in pair['alternatives']];va={v['action']:v['score'] for v in aa['values']};vb={v['action']:v['score'] for v in bb['values']};gaps=(va[x]-va[y],vb[y]-vb[x]);regrets=dict(price1_action_at1=aa['best']-va[x],price2_action_at1=aa['best']-va[y],price1_action_at2=bb['best']-vb[x],price2_action_at2=bb['best']-vb[y]);bothoptimal=all(v==0 for v in regrets.values())
   if bothoptimal:count['both_native_choices_optimal_under_both_prices']+=1
   if set(aa['best_actions'])!=set(bb['best_actions']):count['optimal_set_changes']+=1
   if not set(aa['best_actions'])&set(bb['best_actions']):count['disjoint_optimal_sets']+=1
   if gaps[0]>0 and gaps[1]>0:count['coherent_strict_pair_preference_reversal']+=1
   if regrets['price1_action_at1']>0:count['native1_not_optimal_in_reference1']+=1
   if regrets['price2_action_at2']>0:count['native2_not_optimal_in_reference2']+=1
   details.append(dict(pair=pair['pair'],law=pair['law'],depth=d,regrets=regrets,pair_preference_gaps=gaps,old_native_actions=[x,y],best1=aa['best_actions'],best2=bb['best_actions']))
  summary.append(dict(depth=d,counts=dict(count)))
 out=dict(status='PASS_ALL_SAVED_RECORDS_AND_COMPLETE_REFERENCE_REGRETS',queries=len(rows),complete_queries=sum(r['complete'] for r in rows),independent_public_leaf_records=leaves,literal_path_edges=edges,summary=summary,details=details,seconds=time.perf_counter()-beg,scope='All87 firstcandidate NORMALprice divergences, selectedbyactioninequality not WDL. Exactpublichistory/candidateperspectivechecked, partialqueriesretained. CompletematerialD4/6 has NOq/selectivepruning, Native usesq/LMR/SEE/budgetedpartialtrees; reference regret is NOT realplayingstrength/wholeNativecorrectness. No newgames/training/price selection.')
 (O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:out[k] for k in ['status','queries','independent_public_leaf_records','literal_path_edges','summary','seconds']}))
if __name__=='__main__':run()
