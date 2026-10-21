"""Independent alpha-beta checks of four clock-alias reference roots.

Native request means legal-generation provider only, not Native search. Rectangle
checks remain explicit Core; no native execution is claimed for unsupported shape.
"""
from pathlib import Path
from dataclasses import replace
import json,time
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from scripts.price_regions import CONFIG
from scripts.research_record import write_record,record_value
base=Path('artifacts/price-regions-20261021');source=json.loads((base/'rule-clock-counterfactual.json').read_text());output=base/'rule-clock-public-validation.json'
if output.exists():raise FileExistsError(output)
plan=[('source3x3',2),('source3x3',3),('emptyrow3x4',0),('emptyrow3x4',3)]
report=dict(scope=__doc__,declaration=dict(max_ply=7,roots=plan,public_nodes=50000,public_seconds=5,q=0,tt=False,ordering=False),checks=[])
write_record(output,report);start=time.perf_counter()
for label,index in plan:
 world=next(x for x in source['worlds'] if x['label']==label and x['max_ply']==7);row=next(x for x in world['roots'] if x['index']==index)
 c=compile_ruleset_for_execution(ruleset_from_dict(world['rule']));s=GameSession.replay(c,deserialize_game_record(json.dumps(row['record'])))
 p,_=build_semantic_opportunity_profile(c,CONFIG);p=replace(p,board_value_by_type={'K':0,'H':1000,'B':1000},hand_value_by_base_type={'K':0,'H':0,'B':0},promotion_gain_by_type={'K':0,'H':0,'B':0})
 expected=max(a['score'] for a in row['true_actions']);truth={a['action']:a['wdl'] for a in row['true_actions']};depth=7-s.state.ply_count
 for native in ([False,True] if label=='source3x3' else [False]):
  pl=AlphaBetaPlayer(c,evaluator_override=Evaluator(c,p,CONFIG),use_disk_cache=False,use_tt=False,use_ordering=False,
   use_native_semantic_legality=native,tuning=SearchTuning(use_root_tactical=False));before=s.state
  d=pl.choose_action(s,SearchLimits(max_depth=depth,max_nodes=50000,max_time_seconds=5,quiescence_max_depth=0,quiescence_hard_max_depth=0))
  assert s.state==before and d.score==expected and truth[str(d.action)]==max(truth.values())
  pv=GameSession.replay(c,s.to_record())
  for a in d.principal_variation:pv.submit(a)
  assert pv.state.terminal_status.is_terminal
  report['checks'].append(dict(world=label,root=index,requested_native_legality=native,native_provider_created=pl.native_legality_provider is not None,
   requested_depth=depth,expected_reference_score=expected,selected_wdl=truth[str(d.action)],decision=record_value(d),action=str(d.action),pv_terminal=record_value(pv.state.terminal_status)))
report['wall_seconds']=time.perf_counter()-start;write_record(output,report)
print([(x['world'],x['root'],x['requested_native_legality'],x['decision']['completed_depth'],x['selected_wdl'],x['decision']['native_legality_calls'],x['decision']['native_legality_fallbacks']) for x in report['checks']])
