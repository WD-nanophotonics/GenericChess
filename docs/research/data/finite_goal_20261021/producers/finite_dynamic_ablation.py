"""Existing dynamic-feature ablations on exposed, already-solved finite roots.

No coefficients are fit/selected from WDL. The two fixed material scales expose
interaction units; rectangular anchor-escape scope is not silently broadened.
"""
from pathlib import Path
from dataclasses import replace
import argparse,json,time
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.search import reference_minimax
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.ai.evaluation.semantic_attacks import SemanticAttackEvaluator
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.limits import SearchLimits
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.price_regions import CONFIG
from scripts.research_record import record_value,write_record


def run(square_path,rectangle_path,output):
    if output.exists():raise FileExistsError(output)
    square=json.loads(square_path.read_text());rect=json.loads(rectangle_path.read_text())
    configs={'material':CONFIG,'mobility':replace(CONFIG,dynamic_mobility_weight=2),
        'escape':replace(CONFIG,anchor_escape_weight=5),'existing_default':EvaluationConfig()}
    report=dict(scope=__doc__,declaration=dict(worlds=['source3x3','emptyrow3x4'],material_scales=[1,1000],
        configs={k:record_value(v) for k,v in configs.items()},depth=2,q=0,tt=False,ordering=False,
        nodes=100000,seconds=5,expected_successful_queries=40,rectangle_escape='unsupported existing evaluator scope; no replacement or silent zero'),
        worlds=[],checks=[])
    write_record(output,report);start=time.perf_counter()
    for label,data in (('source3x3',square),('emptyrow3x4',rect)):
        c=compile_ruleset_for_execution(ruleset_from_dict(data['rule']));profile,_=build_semantic_opportunity_profile(c,CONFIG)
        roots=[]
        for i,row in enumerate(data['roots']):
            rec=deserialize_game_record(json.dumps(row['record']));s=GameSession.replay(c,rec)
            if s.state.terminal_status.is_terminal:continue
            truth={a['action']:a['wdl'] for a in row['true_actions'] if a['complete']}
            assert len(truth)==len(s.legal_actions())
            roots.append((i,s,truth))
        report['worlds'].append(dict(label=label,rule=data['rule'],source_records=[record_value(s.to_record()) for _,s,_ in roots]))
        for name,cfg in configs.items():
            if label=='emptyrow3x4' and name in ('escape','existing_default'):
                try:SemanticAttackEvaluator(c,profile,cfg,backend='core')
                except AttributeError as exc:
                    report['checks'].append(dict(world=label,config=name,status='unsupported',exception=type(exc).__name__,reason=str(exc)))
                else:raise AssertionError('Existing rectangular scope changed; reassess before claiming results')
                continue
            for scale in (1,1000):
                p=replace(profile,board_value_by_type={'K':0,'H':scale,'B':scale},
                    hand_value_by_base_type={'K':0,'H':0,'B':0},promotion_gain_by_type={'K':0,'H':0,'B':0})
                for index,s,truth in roots:
                    t=time.perf_counter();ev=SemanticAttackEvaluator(c,p,cfg,backend='core')
                    player=AlphaBetaPlayer(c,evaluator_override=ev,use_disk_cache=False,use_tt=False,use_ordering=False,
                        use_native_semantic_legality=False,tuning=SearchTuning(use_root_tactical=False))
                    before=s.state
                    d=player.choose_action(s,SearchLimits(max_depth=2,max_nodes=100000,max_time_seconds=5,
                        quiescence_max_depth=0,quiescence_hard_max_depth=0));cost=time.perf_counter()-t
                    assert d.completed_depth==2 and s.state==before
                    expected,first=reference_minimax(s.state,2,ev,c)
                    assert d.score==expected and d.action==first
                    replay=GameSession.replay(c,s.to_record())
                    for a in d.principal_variation:replay.submit(a)
                    report['checks'].append(dict(world=label,root=index,config=name,scale=scale,status='complete',
                        decision=record_value(d),action=str(d.action),selected_wdl=truth[str(d.action)],
                        best_wdl=max(truth.values()),construct_and_query_seconds=cost))
            write_record(output,report)
    report['wall_seconds']=time.perf_counter()-start;write_record(output,report)
    for w in ('source3x3','emptyrow3x4'):
        for conf in configs:
            for scale in (1,1000):
                selected=[(x['root'],x['selected_wdl']) for x in report['checks'] if x['world']==w and x['config']==conf and x.get('scale')==scale]
                if selected:print(w,conf,scale,selected)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('square',type=Path);p.add_argument('rectangle',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();run(a.square,a.rectangle,a.output)
