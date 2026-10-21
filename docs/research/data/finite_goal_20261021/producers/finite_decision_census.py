"""Whole finite-game decision census under fixed, unfit existing evaluators.

All reachable history prefixes in one max_ply6 game and its verified equivalent
DSL encoding. Uniform-legal-path mass is not a learned/self-play distribution.
WDL after one selected action assumes optimal continuation, not actual self-play.
"""
from pathlib import Path
from fractions import Fraction
from dataclasses import replace
from collections import Counter
import argparse,json,time
from generic_chess.ai.alphabeta import search
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.ai.evaluation.semantic_attacks import SemanticAttackEvaluator
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.limits import SearchLimits
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.core.transition import legal_successors
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record
from scripts.price_regions import CONFIG,Budget,TreeLimit
from scripts.price_regions_goal import NoHeuristicFrontier
from scripts.research_record import record_value,write_record


def run(source_path,rewrite_path,output):
    if output.exists():raise FileExistsError(output)
    sources=[('original',json.loads(source_path.read_text())['rule']),('rewritten',json.loads(rewrite_path.read_text())['rule'])]
    models=[('material1000',CONFIG,1000),('mobility2_material1000',replace(CONFIG,dynamic_mobility_weight=2),1000),
        ('mobility2_material1',replace(CONFIG,dynamic_mobility_weight=2),1),('default_material1',EvaluationConfig(),1)]
    report=dict(scope=__doc__,declaration=dict(worlds=[w for w,_ in sources],depths=[2,3],models=[(n,record_value(c),s) for n,c,s in models],
        expected_ongoing_each=101,expected_complete_histories_each=206,reference_nodes=25000,reference_seconds=90,
        global_query_nodes=200000,global_seconds=90,query_nodes=100000,query_seconds=5,q=0,tt=False,ordering=False),worlds=[])
    write_record(output,report);start=time.perf_counter();reference_budget=Budget(90,25000);paid=0
    original=search.reference_minimax
    def limited(*args,**kwargs):reference_budget.check();return original(*args,**kwargs)
    search.reference_minimax=limited
    try:
        for world,definition in sources:
            c=compile_ruleset_for_execution(ruleset_from_dict(definition));profile,_=build_semantic_opportunity_profile(c,CONFIG)
            evaluators=[]
            for name,cfg,scale in models:
                p=replace(profile,board_value_by_type={'K':0,'H':scale,'B':scale},hand_value_by_base_type={'K':0,'H':0,'B':0},promotion_gain_by_type={'K':0,'H':0,'B':0})
                evaluators.append((name,SemanticAttackEvaluator(c,p,cfg,backend='core')))
            result=dict(world=world,rule=definition,terminal_leaves=0,rows=[]);report['worlds'].append(result)
            def visit(session,mass):
                nonlocal paid
                if time.perf_counter()-start>=90 or paid>=200000:raise TreeLimit('declared global decision-census fuse')
                if session.state.terminal_status.is_terminal:result['terminal_leaves']+=1;return
                before=session.state;pairs=sorted(legal_successors(before,c),key=lambda x:str(x[0]));truth={}
                for a,child in pairs:
                    score,_=limited(child,definition['max_ply']-child.ply_count,NoHeuristicFrontier(),c,1);score=-score
                    truth[str(a)]=(score>0)-(score<0)
                row=dict(ply=before.ply_count,mass=str(mass),owner=before.position.side_to_move,
                    record=json.loads(serialize_game_record(session.to_record())),true_actions=truth,best_wdl=max(truth.values()),checks=[])
                result['rows'].append(row)
                for name,ev in evaluators:
                    for depth in (2,3):
                        pl=AlphaBetaPlayer(c,evaluator_override=ev,use_disk_cache=False,use_tt=False,use_ordering=False,
                            use_native_semantic_legality=False,tuning=SearchTuning(use_root_tactical=False))
                        d=pl.choose_action(session,SearchLimits(max_depth=depth,max_nodes=100000,max_time_seconds=5,
                            quiescence_max_depth=0,quiescence_hard_max_depth=0));paid+=d.nodes
                        assert session.state==before and d.action in dict(pairs)
                        row['checks'].append(dict(model=name,depth=depth,selected_wdl=truth[str(d.action)],
                            regret=max(truth.values())-truth[str(d.action)],decision=record_value(d)))
                for a,_ in pairs:
                    child=GameSession.replay(c,session.to_record());child.submit(a);visit(child,mass/len(pairs))
            try:visit(GameSession(c),Fraction(1))
            except TreeLimit as exc:result['incomplete']=str(exc)
            write_record(output,report)
            if result.get('incomplete'):break
    finally:
        search.reference_minimax=original
        report.update(reference_nodes=reference_budget.edges,paid_query_nodes=paid,wall_seconds=time.perf_counter()-start)
        write_record(output,report)
    for w in report['worlds']:
        print(w['world'],len(w['rows']),w['terminal_leaves'],w.get('incomplete'))
        for name,_,_ in models:
            for depth in (2,3):
                checks=[(r,x) for r in w['rows'] for x in r['checks'] if x['model']==name and x['depth']==depth]
                count=sum(x['regret']>0 for _,x in checks);nodes=sum(x['decision']['nodes'] for _,x in checks)
                print(name,depth,'regret count',count,'nodes',nodes)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('rewrite',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();run(a.source,a.rewrite,a.output)
