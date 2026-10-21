"""Exhaustive two-ply-prefix mechanism census in one authored finite 3x3 game.

Use the existing reference_minimax unchanged except a process-local entry cost
fuse. Its nonterminal horizon evaluator raises: a completed WDL requires every
frontier to be an actual terminal under the explicit max_ply=6 rule.
"""
from dataclasses import replace
from fractions import Fraction
import json,time
from pathlib import Path

from generic_chess.ai.alphabeta import search
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import legal_successors
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_to_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record
from scripts.price_regions import definition,build_tree,Budget,partition,response,CONFIG,TreeLimit
from scripts.research_record import write_record,record_value


class NoHeuristicFrontier:
    def evaluate(self,state):
        raise AssertionError('An ongoing heuristic frontier is not exact WDL')


def run(output):
    if output.exists():raise FileExistsError(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    board=[[None]*3 for _ in range(3)]
    for owner,tid,f,r in ((0,'K',0,0),(1,'K',2,2),(0,'H',2,0),(0,'B',1,0)):
        board[r][f]=Piece(owner,tid,tid)
    rule=replace(definition(732005),board_size=3,initial_position=tuple(map(tuple,board)),
        drop_allowed={t:((False,)*9,)*2 for t in ('H','B')},max_ply=6)
    compiled=compile_ruleset_for_execution(rule)
    profile,scope=build_semantic_opportunity_profile(compiled,CONFIG)
    report=dict(question='Can complete D2 material-policy regions cross actual finite-game WDL on all legal2ply prefixes?',
        scope='One newly authored3x3 guarded-movement world with actual rule max_ply6; no promotion/drop/aux, no all-domain or learned strength claim.',
        rule=ruleset_to_dict(rule),declaration=dict(prefix_depth=2,depth=2,
            reference='Existing reference_minimax to max_ply; nonterminal frontier refused',
            global_reference_nodes=150000,global_reference_seconds=90,tree_nodes=30000,tree_seconds=60,
            public_seconds=3,q=0,tt=False,ordering=False,price_H=[125,500,1000,2000,4000],price_B=1000,
            decision='Complete p2/p3 census or retained UNKNOWN; no refill, extension, training or new solver.'),
        profile=dict(profile.board_value_by_type),roots=[])
    write_record(output,report)
    session=GameSession(compiled)
    paths=[]
    for a,child in sorted(legal_successors(session.state,compiled),key=lambda t:str(t[0])):
        if child.terminal_status.is_terminal:
            paths.append(((a,),Fraction(1,len(session.legal_actions()))))
            continue
        replies=sorted(legal_successors(child,compiled),key=lambda t:str(t[0]))
        for b,_ in replies:
            paths.append(((a,b),Fraction(1,len(session.legal_actions())*len(replies))))
    assert sum((p for _,p in paths),Fraction(0))==1
    reference_budget=Budget(90,150000);tree_budget=Budget(60,30000)
    old=search.reference_minimax
    def limited(*args,**kwargs):
        reference_budget.check()
        return old(*args,**kwargs)
    search.reference_minimax=limited
    started=time.perf_counter()
    try:
        for prefix,mass in paths:
            root=GameSession(compiled)
            for a in prefix:root.submit(a)
            row=dict(record=json.loads(serialize_game_record(root.to_record())),mass=str(mass),
                     terminal=record_value(root.state.terminal_status))
            report['roots'].append(row)
            if root.state.terminal_status.is_terminal:
                write_record(output,report);continue
            forms=set()
            tree=build_tree(root.state,compiled,2,root.state.position.side_to_move,tree_budget,forms)
            row.update(partition=partition(tree,forms),true_actions=[],public=[])
            for action,child in sorted(legal_successors(root.state,compiled),key=lambda t:str(t[0])):
                n=reference_budget.edges;t=time.perf_counter()
                try:
                    score,_=limited(child,compiled.max_ply-child.ply_count,NoHeuristicFrontier(),compiled,1)
                    root_score=-score
                    row['true_actions'].append(dict(action=str(action),complete=True,wdl=(root_score>0)-(root_score<0),
                        score=root_score,nodes=reference_budget.edges-n,seconds=time.perf_counter()-t))
                except TreeLimit as exc:
                    row['true_actions'].append(dict(action=str(action),complete=False,wdl=None,reason=str(exc)))
                    row['reference_incomplete']=True
                    break
            for h in report['declaration']['price_H']:
                p=replace(profile,board_value_by_type={'K':0,'H':h,'B':1000},
                    hand_value_by_base_type={'K':0,'H':0,'B':0},promotion_gain_by_type={'K':0,'H':0,'B':0})
                player=AlphaBetaPlayer(compiled,evaluator_override=Evaluator(compiled,p,CONFIG),use_disk_cache=False,
                    use_tt=False,use_ordering=False,use_native_semantic_legality=False,tuning=SearchTuning(use_root_tactical=False))
                before=root.state
                d=player.choose_action(root,SearchLimits(max_depth=2,max_nodes=100000,max_time_seconds=3,
                    quiescence_max_depth=0,quiescence_hard_max_depth=0))
                expected,acts=response(tree,Fraction(h,1000))
                assert d.completed_depth==2 and d.score==expected and str(d.action) in acts
                assert root.state==before
                values={a['action']:a['wdl'] for a in row['true_actions'] if a['complete']}
                row['public'].append(dict(H=h,decision=record_value(d),selected_wdl=values.get(str(d.action))))
            assert GameSession.replay(compiled,root.to_record()).state==root.state
            write_record(output,report)
            if row.get('reference_incomplete'):break
    finally:
        search.reference_minimax=old
        report.update(wall_seconds=time.perf_counter()-started,reference_nodes=reference_budget.edges,
                      tree_nodes=tree_budget.edges,planned_prefixes=len(paths),actual_prefixes=len(report['roots']))
        write_record(output,report)
    print({k:report[k] for k in ('planned_prefixes','actual_prefixes','reference_nodes','tree_nodes','wall_seconds')})


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path)
    run(p.parse_args().output)
