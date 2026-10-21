"""Twenty declared finite-game dynamic controls, fixed D3 material opponent.

Posthoc mechanism games on already exposed roots; no coefficient fit, independent
holdout, equal-wall claim or activation. Actual max_ply6 is unchanged in each game.
"""
from pathlib import Path
from dataclasses import replace
import argparse,json,time
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.ai.evaluation.semantic_attacks import SemanticAttackEvaluator
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.benchmark.runner import play_game,RunConfig
from generic_chess.ai.benchmark.profiles import PROFILES
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from scripts.price_regions import CONFIG,TreeLimit
from scripts.research_record import record_value,write_record


def run(square_path,rectangle_path,output):
    if output.exists():raise FileExistsError(output)
    inputs=[('source3x3',json.loads(square_path.read_text())),('emptyrow3x4',json.loads(rectangle_path.read_text()))]
    report=dict(scope=__doc__,declaration=dict(games=20,configs=['mobility2','existing_default(square only)'],scales=[1,1000],
        candidate_depth=2,fixed_opponent_depth=3,fixed_opponent_scale=1000,actual_rule_max_ply=6,q=0,
        seconds_per_query=1,nodes_per_query=4096,global_seconds=90,global_paid_nodes=200000),worlds=[])
    write_record(output,report);started=time.perf_counter();paid_nodes=0
    for label,source in inputs:
        c=compile_ruleset_for_execution(ruleset_from_dict(source['rule']));profile,_=build_semantic_opportunity_profile(c,CONFIG)
        world=dict(label=label,rule=source['rule'],games=[]);report['worlds'].append(world)
        def make(config,scale):
            p=replace(profile,board_value_by_type={'K':0,'H':scale,'B':scale},hand_value_by_base_type={'K':0,'H':0,'B':0},promotion_gain_by_type={'K':0,'H':0,'B':0})
            return AlphaBetaPlayer(c,evaluator_override=SemanticAttackEvaluator(c,p,config,backend='core'),
                use_disk_cache=False,use_tt=False,use_ordering=False,use_native_semantic_legality=False,tuning=SearchTuning(use_root_tactical=False))
        class Fixed:
            def __init__(self,config,scale,depth):self.inner=make(config,scale);self.depth=depth;self.session=None
            def choose_action(self,s,limits):
                nonlocal paid_nodes
                if time.perf_counter()-started>=90 or paid_nodes>=200000:raise TreeLimit('declared global fuse')
                self.session=s
                d=self.inner.choose_action(s,replace(limits,max_depth=self.depth,quiescence_max_depth=0,quiescence_hard_max_depth=0))
                paid_nodes+=d.nodes;return d
        for i,row in enumerate(source['roots']):
            rec=deserialize_game_record(json.dumps(row['record']));s=GameSession.replay(c,rec)
            if s.state.terminal_status.is_terminal:continue
            owner=s.state.position.side_to_move
            configs=[('mobility2',replace(CONFIG,dynamic_mobility_weight=2))]
            if label=='source3x3':configs.append(('existing_default',EvaluationConfig()))
            for name,config in configs:
                for scale in (1,1000):
                    candidate=Fixed(config,scale,2);foe=Fixed(CONFIG,1000,3);players=[foe,foe];players[owner]=candidate
                    outcome,events=play_game(c,rec.actions,f'{label}-root{i}',f'{name}-{scale}-{i}',owner,candidate,foe,
                        RunConfig(PROFILES['baseline'],PROFILES['baseline'],(),seconds=1,nodes=4096,max_plies=6))
                    final=candidate.session or foe.session
                    assert final is not None and GameSession.replay(c,final.to_record()).state==final.state
                    world['games'].append(dict(root=i,config=name,scale=scale,candidate_owner=owner,outcome=record_value(outcome),
                        events=record_value(events),terminal=record_value(final.state.terminal_status),record=json.loads(serialize_game_record(final.to_record()))))
                    write_record(output,report)
    report.update(actual_games=sum(len(w['games']) for w in report['worlds']),paid_nodes=paid_nodes,wall_seconds=time.perf_counter()-started)
    write_record(output,report)
    for w in report['worlds']:
        print(w['label'],[(g['root'],g['config'],g['scale'],g['outcome']['result'],g['terminal']['status']) for g in w['games']])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('square',type=Path);p.add_argument('rectangle',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();run(a.square,a.rectangle,a.output)
