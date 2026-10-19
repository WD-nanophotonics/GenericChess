import json, random, time
from pathlib import Path
from unittest.mock import patch
from dataclasses import asdict

from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from generic_chess.core.movegen import legal_actions
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
import generic_chess.ai.evaluation.profile as profile_module
from generic_chess.ai.benchmark.runner import RunConfig, play_game, summarize
from generic_chess.ai.benchmark.profiles import BenchmarkProfile

OUT=Path(__file__).with_suffix('.out')
OUT.mkdir(parents=True,exist_ok=True)
PLAN={"question":"With both arms using corrected promotion-potential geometry, does the generic-v3 semantic Western P profile outperform the exact old generic-v2 atom-only price profile in a fresh paired finite-game sample?",
"ruleset":"canonical Western Chess","fresh_prefix_seeds":list(range(301,309)),"prefix_plies":12,"games_per_prefix":2,"max_additional_plies":128,
"search":{"max_depth":3,"max_nodes_total":4096,"quiescence_max_depth":0,"quiescence_hard_max_depth":0,"tt":False,"ordering":False,"root_tactical":False},
"candidate":"generic-v3 P board=361 hand=325; semantic profile","control":"exact generic-v2 profile rebuilt from legacy declared atoms; P board=1 hand=1","shared_dynamic_evaluator":"corrected profile_movement_atoms projection for both arms",
"pairing":"same fresh prefix, both candidate colors","unknown_policy":"ongoing at capped additional ply remains unresolved; no refill",
"max_elapsed_seconds":3000,"started_unix":time.time()}
(OUT/'plan.json').write_text(json.dumps(PLAN,indent=2)+'\n',encoding='utf-8')
compiled=compile_ruleset_for_execution(build_western_chess_ruleset())
candidate_config=EvaluationConfig(); candidate_profile=profile_module.build_ruleset_profile(compiled,candidate_config)
legacy_types={pt.type_id:pt for pt in compiled.piece_types}
control_config=EvaluationConfig(evaluator_version='generic-v2')
with patch.object(profile_module,'profile_movement_atoms',lambda c,tid: tuple(legacy_types[tid].movement_atoms)):
 control_profile=profile_module.build_ruleset_profile(compiled,control_config)
assert candidate_profile.board_value_by_type['P']==361 and candidate_profile.hand_value_by_base_type['P']==325
assert control_profile.board_value_by_type['P']==1 and control_profile.hand_value_by_base_type['P']==1
class FixedBudgetPlayer(AlphaBetaPlayer):
 def choose_action(self,session,limits,**kwargs):
  fixed=SearchLimits(max_depth=3,max_nodes=4096,quiescence_max_depth=0,quiescence_hard_max_depth=0)
  return super().choose_action(session,fixed,**kwargs)
tuning=SearchTuning(use_root_tactical=False)
candidate_bp=BenchmarkProfile('semantic_P_v3',tuning); control_bp=BenchmarkProfile('legacy_P_v2',tuning)
runconfig=RunConfig(control=control_bp,candidate=candidate_bp,suite=(),seconds=None,nodes=4096,max_plies=0)
games=[]; completed=set(); start=time.monotonic()
with (OUT/'events.jsonl').open('w',encoding='utf-8') as events_fh, (OUT/'games.jsonl').open('w',encoding='utf-8') as games_fh:
 for seed in PLAN['fresh_prefix_seeds']:
  root=GameSession(compiled); rng=random.Random(seed); opening=[]
  for _ in range(12):
   if root.result.status is not SessionStatus.ONGOING: break
   acts=sorted(legal_actions(root.state,compiled),key=str)
   if not acts: break
   action=rng.choice(acts); opening.append(action); root.submit(action)
  if len(opening)!=12:
   raise RuntimeError(f'prefix construction incomplete seed={seed}, plies={len(opening)}')
  for color in (0,1):
   if time.monotonic()-start>=PLAN['max_elapsed_seconds']:
    break
   candidate=FixedBudgetPlayer(compiled,evaluator_override=Evaluator(compiled,candidate_profile,candidate_config),use_disk_cache=False,use_tt=False,use_ordering=False,tuning=tuning,use_native_semantic_legality=False)
   control=FixedBudgetPlayer(compiled,evaluator_override=Evaluator(compiled,control_profile,control_config),use_disk_cache=False,use_tt=False,use_ordering=False,tuning=tuning,use_native_semantic_legality=False)
   key=f'western_seed{seed}_candidate_color{color}'
   gameconfig=RunConfig(control=control_bp,candidate=candidate_bp,suite=(),seconds=None,nodes=4096,max_plies=len(opening)+128)
   outcome,events=play_game(compiled,tuple(opening),f'western_seed{seed}',key,color,candidate,control,gameconfig)
   games.append(outcome); completed.add(key)
   games_fh.write(json.dumps(asdict(outcome),sort_keys=True)+'\n'); games_fh.flush()
   for event in events:
    events_fh.write(json.dumps(asdict(event),sort_keys=True)+'\n')
   events_fh.flush()
  if time.monotonic()-start>=PLAN['max_elapsed_seconds']: break
summary=summarize(games)
summary['planned_games']=16; summary['unstarted_games']=16-len(completed)
summary['elapsed_seconds']=time.monotonic()-start
summary['candidate_reward_bounds']={"lower":(summary['candidate_wins']-summary['candidate_losses']-summary['unresolved'])/16,
 "upper":(summary['candidate_wins']-summary['candidate_losses']+summary['unresolved'])/16}
summary['profile_values']={"candidate_P_board":candidate_profile.board_value_by_type['P'],"candidate_P_hand":candidate_profile.hand_value_by_base_type['P'],"control_P_board":control_profile.board_value_by_type['P'],"control_P_hand":control_profile.hand_value_by_base_type['P']}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,separators=(',',':')))
print(f'ACTUAL_ELAPSED_SECONDS={summary["elapsed_seconds"]:.3f}')
