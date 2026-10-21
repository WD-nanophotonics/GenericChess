"""Matched-prefix empty-row counterfactual; existing reference, no new solver.

Four source histories are replayed in a NEW 3x4/max_ply6 game. They are not
samples from its natural opening distribution. Unfinished references stay UNKNOWN.
"""
import argparse,json,time
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from generic_chess.ai.alphabeta import search
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.benchmark.runner import play_game,RunConfig
from generic_chess.ai.benchmark.profiles import PROFILES
from generic_chess.core.transition import legal_successors
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from scripts.price_regions import CONFIG,Budget,TreeLimit,build_tree,partition,public_check
from scripts.price_regions_goal import NoHeuristicFrontier
from scripts.research_record import record_value,write_record


def run(plan_path,output):
    if output.exists():raise FileExistsError(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    plan=json.loads(plan_path.read_text())
    compiled=compile_ruleset_for_execution(ruleset_from_dict(plan['rule']))
    profile,_=build_semantic_opportunity_profile(compiled,CONFIG)
    profile=replace(profile,board_value_by_type={'K':0,'H':1000,'B':1000},
        hand_value_by_base_type={'K':0,'H':0,'B':0},promotion_gain_by_type={'K':0,'H':0,'B':0})
    report=dict(question=plan['question'],scope=plan['limitations'],rule=plan['rule'],
        declaration=dict(prefixes=4,reference_nodes=150000,reference_seconds=90,
            complete_tree_nodes=60000,complete_tree_seconds=90,public_seconds=3,
            price_H=[125,500,1000,2000,4000],price_B=1000,depths=[2,3],q=0,
            games=8,fixed_foe_depth=3,game_nodes=4096,game_seconds=1,actual_rule_max_ply=6),roots=[])
    write_record(output,report)
    total_start=time.perf_counter();ref_budget=Budget(90,150000);tree_budget=Budget(90,60000)
    original=search.reference_minimax
    def limited(*args,**kwargs):
        ref_budget.check();return original(*args,**kwargs)
    def player(h=1000):
        p=replace(profile,board_value_by_type={'K':0,'H':h,'B':1000})
        return AlphaBetaPlayer(compiled,evaluator_override=Evaluator(compiled,p,CONFIG),
            use_disk_cache=False,use_tt=False,use_ordering=False,use_native_semantic_legality=False,
            tuning=SearchTuning(use_root_tactical=False))
    class Depth:
        def __init__(self,depth):self.inner=player();self.depth=depth;self.session=None
        def choose_action(self,s,limits):
            self.session=s
            return self.inner.choose_action(s,replace(limits,max_depth=self.depth,
                quiescence_max_depth=0,quiescence_hard_max_depth=0))
    search.reference_minimax=limited
    try:
        for index,prefix in enumerate(plan['matched_prefixes']):
            old=deserialize_game_record(json.dumps(prefix['source_record']))
            root=GameSession(compiled)
            for action in old.actions:root.submit(action)
            assert root.state.ply_count==prefix['new_ply'] and len(root.legal_actions())==prefix['new_legal_actions']
            assert GameSession.replay(compiled,root.to_record()).state==root.state
            row=dict(index=index,record=json.loads(serialize_game_record(root.to_record())),
                status=record_value(root.state.terminal_status),side=root.state.position.side_to_move,
                true_actions=[],depth_regions=[],public=[],games=[])
            report['roots'].append(row);write_record(output,report)
            for action,child in sorted(legal_successors(root.state,compiled),key=lambda x:str(x[0])):
                n=ref_budget.edges;t=time.perf_counter()
                try:
                    score,_=limited(child,plan['rule']['max_ply']-child.ply_count,NoHeuristicFrontier(),compiled,1)
                    score=-score
                    row['true_actions'].append(dict(action=str(action),complete=True,score=score,
                        wdl=(score>0)-(score<0),nodes=ref_budget.edges-n,seconds=time.perf_counter()-t))
                except TreeLimit as exc:
                    row['true_actions'].append(dict(action=str(action),complete=False,wdl=None,reason=str(exc)))
                    row['incomplete']=True;break
            if row.get('incomplete'):write_record(output,report);break
            wdl={a['action']:a['wdl'] for a in row['true_actions']}
            for depth in (2,3):
                forms=set();tree=build_tree(root.state,compiled,depth,root.state.position.side_to_move,tree_budget,forms)
                row['depth_regions'].append(dict(depth=depth,forms=sorted(forms),regions=partition(tree,forms)))
                for h in report['declaration']['price_H']:
                    result=public_check(root,profile,h,1000,tree,3,depth)
                    action_values={json.dumps(record_value(a),sort_keys=True):wdl[str(a)]
                        for a,_ in legal_successors(root.state,compiled)}
                    result.update(depth=depth,selected_wdl=action_values.get(
                        json.dumps(result['decision']['action'],sort_keys=True)))
                    row['public'].append(result)
            for depth in (2,3):
                candidate=Depth(depth);foe=Depth(3);owner=root.state.position.side_to_move
                players=[foe,foe];players[owner]=candidate
                outcome,events=play_game(compiled,root.to_record().actions,f'empty-row-{index}',
                    f'd{depth}-{index}',owner,candidate,foe,RunConfig(PROFILES['baseline'],PROFILES['baseline'],(),
                        seconds=1,nodes=4096,max_plies=6))
                final=candidate.session or foe.session
                assert final is not None and final.state.terminal_status.is_terminal
                assert GameSession.replay(compiled,final.to_record()).state==final.state
                row['games'].append(dict(candidate_depth=depth,candidate_owner=owner,
                    outcome=record_value(outcome),events=record_value(events),
                    terminal=record_value(final.state.terminal_status),record=json.loads(serialize_game_record(final.to_record()))))
            write_record(output,report)
            print('root',index,'true',[a['wdl'] for a in row['true_actions']],
                'public',[(r['depth'],r['h'],r['selected_wdl']) for r in row['public']],flush=True)
    finally:
        search.reference_minimax=original
        report.update(reference_nodes=ref_budget.edges,tree_nodes=tree_budget.edges,wall_seconds=time.perf_counter()-total_start)
        write_record(output,report)
    print('finished',len(report['roots']),report['reference_nodes'],report['tree_nodes'],report['wall_seconds'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('output',type=Path)
    args=p.parse_args();run(args.plan,args.output)
