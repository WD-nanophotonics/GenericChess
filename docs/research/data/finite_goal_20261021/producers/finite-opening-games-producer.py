"""Ten finite-opening utility controls; no fitting or independent-strength claim."""
from pathlib import Path
from dataclasses import replace
import json,time
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.ai.evaluation.semantic_attacks import SemanticAttackEvaluator
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.benchmark.runner import play_game,RunConfig
from generic_chess.ai.benchmark.profiles import PROFILES
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record
from scripts.price_regions import CONFIG
from scripts.research_record import record_value,write_record
output=Path('artifacts/price-regions-20261021/finite-opening-games.json')
if output.exists():raise FileExistsError(output)
worlds=[('original',json.loads(Path('artifacts/price-regions-20261021/goal-census.json').read_text())['rule']),
    ('rewritten',json.loads(Path('artifacts/price-regions-20261021/finite-anchor-rewrite.json').read_text())['rule'])]
models=[('material1000_D2',CONFIG,1000,2),('mobility2_material1000_D2',replace(CONFIG,dynamic_mobility_weight=2),1000,2),
    ('mobility2_material1_D2',replace(CONFIG,dynamic_mobility_weight=2),1,2),('default_material1_D2',EvaluationConfig(),1,2),('material1000_D3',CONFIG,1000,3)]
report=dict(scope=__doc__,declaration=dict(games=10,candidate_owner=0,foe='material1000_D3',q=0,tt=False,ordering=False,
    nodes=4096,seconds=1,actual_rule_and_runner_ply_cap=6),games=[])
write_record(output,report);start=time.perf_counter()
for world,definition in worlds:
    c=compile_ruleset_for_execution(ruleset_from_dict(definition));profile,_=build_semantic_opportunity_profile(c,CONFIG)
    class Fixed:
        def __init__(self,cfg,scale,depth):
            p=replace(profile,board_value_by_type={'K':0,'H':scale,'B':scale},hand_value_by_base_type={'K':0,'H':0,'B':0},promotion_gain_by_type={'K':0,'H':0,'B':0})
            self.inner=AlphaBetaPlayer(c,evaluator_override=SemanticAttackEvaluator(c,p,cfg,backend='core'),use_disk_cache=False,
                use_tt=False,use_ordering=False,use_native_semantic_legality=False,tuning=SearchTuning(use_root_tactical=False));self.depth=depth;self.session=None
        def choose_action(self,s,limits):
            self.session=s;return self.inner.choose_action(s,replace(limits,max_depth=self.depth,quiescence_max_depth=0,quiescence_hard_max_depth=0))
    for name,cfg,scale,depth in models:
        candidate=Fixed(cfg,scale,depth);foe=Fixed(CONFIG,1000,3)
        outcome,events=play_game(c,(),world,name,0,candidate,foe,RunConfig(PROFILES['baseline'],PROFILES['baseline'],(),seconds=1,nodes=4096,max_plies=6))
        final=candidate.session or foe.session;assert final.state.terminal_status.is_terminal and GameSession.replay(c,final.to_record()).state==final.state
        report['games'].append(dict(world=world,model=name,outcome=record_value(outcome),events=record_value(events),terminal=record_value(final.state.terminal_status),record=json.loads(serialize_game_record(final.to_record()))))
        write_record(output,report)
report['wall_seconds']=time.perf_counter()-start;write_record(output,report)
print([(g['world'],g['model'],g['outcome']['result'],sum(e['nodes'] for e in g['events'])) for g in report['games']])
