"""One exposed root: equal complete-D3 policy can have unequal budget completion.

The cap set is fixed from the already observed267/276-node pair; no new games,
price search or utility claim. Only literal completed-depth/result provenance.
"""
from pathlib import Path
from dataclasses import replace
import json,time
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.limits import SearchLimits
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.price_regions import CONFIG
from scripts.research_record import record_value,write_record


def run(source,output):
    if output.exists():raise FileExistsError(output)
    source=json.loads(source.read_text());case=next(c for c in source['cases'] if c['seed']==732005)
    c=compile_ruleset_for_execution(ruleset_from_dict(case['rule']));row=next(x for x in case['roots'] if x['ply']==0)
    root=GameSession.replay(c,deserialize_game_record(json.dumps(row['record'])));p,_=build_semantic_opportunity_profile(c,CONFIG)
    caps=[266,267,268,270,275,276,277]
    result=dict(scope=__doc__,declaration=dict(source_seed=732005,ply=0,caps=caps,tables=[[623,1377],[728,1272]],
        max_depth=3,q=0,tt=False,ordering=False,seconds=3,prior_complete_nodes=[267,276],queries=14),checks=[])
    write_record(output,result);start=time.perf_counter()
    for cap in caps:
        for h,b in result['declaration']['tables']:
            profile=replace(p,board_value_by_type={'K':0,'H':h,'B':b},hand_value_by_base_type={'K':0,'H':0,'B':0},promotion_gain_by_type={'K':0,'H':0,'B':0})
            pl=AlphaBetaPlayer(c,evaluator_override=Evaluator(c,profile,CONFIG),use_disk_cache=False,use_tt=False,
                use_ordering=False,use_native_semantic_legality=False,tuning=SearchTuning(use_root_tactical=False))
            before=root.state;d=pl.choose_action(root,SearchLimits(max_depth=3,max_nodes=cap,max_time_seconds=3,
                quiescence_max_depth=0,quiescence_hard_max_depth=0));assert root.state==before
            replay=GameSession.replay(c,root.to_record())
            for a in d.principal_variation:replay.submit(a)
            result['checks'].append(dict(cap=cap,h=h,b=b,decision=record_value(d),action=str(d.action),
                literal_pv_record=record_value(replay.to_record())))
    result['wall_seconds']=time.perf_counter()-start;write_record(output,result)
    print([(x['cap'],x['h'],x['decision']['nodes'],x['decision']['completed_depth'],x['action']) for x in result['checks']])

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();run(a.source,a.output)
