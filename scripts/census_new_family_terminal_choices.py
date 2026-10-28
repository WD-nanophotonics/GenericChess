"""Bounded one-step Core terminal census on NEW actually played histories.

No Player/search/solver or additional played game. Every fixed source decision
is retained; only one-step legal children are generated, never continuations.
"""
import argparse,json,time
from collections import Counter
from pathlib import Path
from generic_chess.core.transition import legal_successors
from generic_chess.core.attacks import is_in_check
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from scripts.verify_published_new_family_games import load,digest,record_hash,diagnostic_action
from scripts.research_record import record_value,write_record

def census(source,output,max_seconds=900,max_parents=1763,max_edges=200000):
 start=time.perf_counter();rows=load(source/'inputs.json.gz')['rows'];roots={r['id']:r for r in rows};games=load(source/'results/games.json.gz')
 output.mkdir(parents=True,exist_ok=True);cache={};occurrences=[];edges=0;done=True;stop=None
 for g in games:
  r=roots[g['case_id']];c=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(r['RuleSet']));engine=semantic_engine_for(c);s=GameSession.replay(c,deserialize_game_record(json.dumps(r['record'])))
  for q in g['queries']:
   k=record_hash(s);assert k==q['record_before_sha256'];chosen=diagnostic_action(q['decision']['action'],r['fingerprint'])
   if k not in cache:
    if time.perf_counter()-start>=max_seconds or len(cache)>=max_parents:done=False;stop='PARENT_TIME_OR_COUNT_CAP';break
    legal=s.legal_actions()
    if edges+len(legal)>max_edges:done=False;stop='EDGE_CAP_BEFORE_FULL_PARENT';break
    succ=legal_successors(s.state,c);assert len(succ)==len(legal) and {a for a,_ in succ}==set(legal)
    terminal=[];counts=Counter();selected=None
    for a,ch in succ:
     edges+=1;t=ch.terminal_status;v=None if not t.is_terminal else 0 if t.winner is None else 1 if t.winner==s.state.position.side_to_move else -1
     counts['UNKNOWN_ONGOING' if v is None else str(v)]+=1
     if v is not None:terminal.append(dict(action=record_value(a),terminal=record_value(t),actor_WDL=v,child_state_sha256=digest(json.dumps(record_value(ch),sort_keys=True,separators=(',',':')).encode())))
    check=engine.in_check(s.state.position,s.state.position.side_to_move) if engine else is_in_check(s.state.position,s.state.position.side_to_move,c)
    cache[k]=dict(case=g['case_id'],family=g['family'],representative_game=g['game_id'],representative_qid=q['query_id'],ply=s.state.ply_count,actor=s.state.position.side_to_move,in_check=check,legal_count=len(legal),anchor_count=sum(a.actor_type_id=='K' for a in legal),child_counts=dict(counts),terminal_actions=terminal)
   row=cache[k];tok=record_value(chosen);fact=next((x for x in row['terminal_actions'] if x['action']==tok),None)
   known=[x['actor_WDL'] for x in row['terminal_actions']];bestlo=max(known,default=-1);besthi=1 if row['child_counts'].get('UNKNOWN_ONGOING',0) else max(known)
   selected_bounds=[fact['actor_WDL']]*2 if fact else [-1,1]
   regret=[max(0,bestlo-selected_bounds[1]),besthi-selected_bounds[0]]
   if row['legal_count']==1:regret=[0,0]
   occurrences.append(dict(game=g['game_id'],case=g['case_id'],qid=q['query_id'],context=k,on=q['on'],actor=row['actor'],ply=row['ply'],selected=tok,root_bounds=[bestlo,besthi],selected_bounds=selected_bounds,regret_bounds=regret))
   s.submit(chosen);assert record_hash(s)==q['record_after_sha256']
  write_record(output/'progress.json',dict(game=g['game_id'],distinct_parents=len(cache),occurrences=len(occurrences),generated_Core_children=edges,wall=time.perf_counter()-start))
  if not done:break
 result=dict(status='COMPLETE' if done else 'PARTIAL',stop=stop,planned_decisions=1763,processed_decisions=len(occurrences),distinct_parents=len(cache),generated_Core_children=edges,wall=time.perf_counter()-start,limits=dict(seconds=max_seconds,parents=max_parents,edges=max_edges),contexts=cache,occurrences=occurrences,scope='ONE step only on fixed new complete played histories; no player/solver/game or deeper missing-state expansion. Actual terminal facts versus ongoing UNKNOWN; original cohort never refilled.')
 write_record(output/'census.json',result);return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=census(a.source,a.output);print(json.dumps({k:v for k,v in r.items() if k not in ('contexts','occurrences')},indent=2))
