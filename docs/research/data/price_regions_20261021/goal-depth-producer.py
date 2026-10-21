"""Posthoc depth mechanism, same full finite-game roots and fixed D3 opponent."""
from pathlib import Path
import json,time
from dataclasses import replace
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.benchmark.runner import play_game,RunConfig
from generic_chess.ai.benchmark.profiles import PROFILES
from scripts.price_regions import CONFIG
from scripts.research_record import record_value,write_record
source=json.loads(Path('artifacts/price-regions-20261021/goal-census.json').read_text())
compiled=compile_ruleset_for_execution(ruleset_from_dict(source['rule']))
profile,_=build_semantic_opportunity_profile(compiled,CONFIG)
profile=replace(profile,board_value_by_type={'K':0,'H':1000,'B':1000},
                hand_value_by_base_type={'K':0,'H':0,'B':0},promotion_gain_by_type={'K':0,'H':0,'B':0})

def player():
    return AlphaBetaPlayer(compiled,evaluator_override=Evaluator(compiled,profile,CONFIG),use_disk_cache=False,
        use_tt=False,use_ordering=False,use_native_semantic_legality=False,tuning=SearchTuning(use_root_tactical=False))

class Depth:
    def __init__(self,depth):self.player=player();self.depth=depth;self.session=None
    def choose_action(self,session,limits):
        self.session=session
        return self.player.choose_action(session,replace(limits,max_depth=self.depth,quiescence_max_depth=0,
            quiescence_hard_max_depth=0))

result=dict(posthoc=True,scope='Same exposed3x3 finite max_ply6 world; extra depth costs more work; no equal-resource strength or independent-family claim.',
            declaration=dict(games=6,candidate_depths=[2,3],fixed_foe_depth=3,nodes=4096,seconds=1,q=0,absolute_rule_and_runner_ply=6),roots=[])
for i,r in enumerate(source['roots']):
    if r['terminal']['status']!='ongoing':continue
    rec=deserialize_game_record(json.dumps(r['record']))
    session=GameSession.replay(compiled,rec)
    row=dict(index=i,mass=r['mass'],games=[]);result['roots'].append(row)
    for depth in (2,3):
        candidate=Depth(depth);foe=Depth(3)
        outcome,events=play_game(compiled,rec.actions,f'finite-root{i}',f'depth{depth}-{i}',0,candidate,foe,
            RunConfig(PROFILES['baseline'],PROFILES['baseline'],(),seconds=1,nodes=4096,max_plies=6))
        final=candidate.session or foe.session
        assert final is not None
        assert GameSession.replay(compiled,final.to_record()).state==final.state
        assert final.state.terminal_status.is_terminal
        row['games'].append(dict(depth=depth,outcome=record_value(outcome),events=record_value(events),
            terminal=record_value(final.state.terminal_status),record=json.loads(serialize_game_record(final.to_record()))))
write_record(Path('artifacts/price-regions-20261021/goal-depth-mechanism.json'),result)
print([(r['index'],[(g['depth'],g['outcome']['result'],g['terminal'],sum(e['nodes'] for e in g['events'])) for g in r['games']]) for r in result['roots']])
