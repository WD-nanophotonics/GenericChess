"""Exact D2 coverage-weight regions on the seven exposed finite-game roots.

Describes whole prespecified mu in[0,1000], never selects or fits coefficients.
Optimal-set WDL bounds are distinct from deterministic tie choices and game utility.
"""
from pathlib import Path
from dataclasses import replace
from fractions import Fraction
import argparse,json,time
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.ai.evaluation.semantic_attacks import SemanticAttackEvaluator
from generic_chess.ai.limits import SearchLimits
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.price_regions import CONFIG,Budget,build_tree,partition,response
from scripts.research_record import record_value,write_record


def run(square,rectangle,output):
    if output.exists():raise FileExistsError(output)
    result=dict(scope=__doc__,declaration=dict(weight_interval=[0,1000],table_H_B=1,hand=0,depth=2,
        fixed_escape=[0,5],rectangle_fixed_escape=[0],public_weights=[0,1,2,5,10,1000],
        nodes=100000,seconds=90,public_seconds=5,q=0,tt=False,ordering=False),roots=[])
    write_record(output,result);budget=Budget(90,100000);start=time.perf_counter()
    for world,path in (('source3x3',square),('emptyrow3x4',rectangle)):
        source=json.loads(path.read_text());c=compile_ruleset_for_execution(ruleset_from_dict(source['rule']))
        p,_=build_semantic_opportunity_profile(c,CONFIG)
        p=replace(p,board_value_by_type={'K':0,'H':1,'B':1},hand_value_by_base_type={'K':0,'H':0,'B':0},promotion_gain_by_type={'K':0,'H':0,'B':0})
        for i,row in enumerate(source['roots']):
            s=GameSession.replay(c,deserialize_game_record(json.dumps(row['record'])))
            if s.state.terminal_status.is_terminal:continue
            truth={a['action']:a['wdl'] for a in row['true_actions']};owner=s.state.position.side_to_move
            for escape in ([0,5] if world=='source3x3' else [0]):
                cfg=replace(CONFIG,anchor_escape_weight=escape)
                base=SemanticAttackEvaluator(c,p,cfg,backend='core');mob=SemanticAttackEvaluator(c,p,replace(cfg,dynamic_mobility_weight=1),backend='core')
                def features(state,root):
                    sign=1 if state.position.side_to_move==root else -1
                    b=base.evaluate(state)*sign;a=mob.evaluate(state)*sign-b
                    return a,b
                forms=set();tree=build_tree(s.state,c,2,owner,budget,forms,leaf_features=features)
                regions=partition(tree,forms,Fraction(0),Fraction(1000))
                for region in regions:
                    values=[truth[a] for a in region['actions']]
                    region.update(optimal_wdl_min=min(values),optimal_wdl_max=max(values))
                dest=dict(world=world,root=i,escape=escape,root_best_wdl=max(truth.values()),leaf_forms=sorted(forms),regions=regions,public=[])
                result['roots'].append(dest)
                for mu in result['declaration']['public_weights']:
                    ev=SemanticAttackEvaluator(c,p,replace(cfg,dynamic_mobility_weight=mu),backend='core')
                    pl=AlphaBetaPlayer(c,evaluator_override=ev,use_disk_cache=False,use_tt=False,use_ordering=False,
                        use_native_semantic_legality=False,tuning=SearchTuning(use_root_tactical=False))
                    before=s.state;d=pl.choose_action(s,SearchLimits(max_depth=2,max_nodes=100000,max_time_seconds=5,
                        quiescence_max_depth=0,quiescence_hard_max_depth=0));score,acts=response(tree,Fraction(mu))
                    assert d.completed_depth==2 and d.score==score and str(d.action) in acts and s.state==before
                    dest['public'].append(dict(mu=mu,decision=record_value(d),action=str(d.action),selected_wdl=truth[str(d.action)]))
                write_record(output,result)
    result.update(tree_nodes=budget.edges,wall_seconds=time.perf_counter()-start);write_record(output,result)
    for row in result['roots']:
        good=[(r['kind'],r['lo'],r['hi'],r['optimal_wdl_min'],r['optimal_wdl_max']) for r in row['regions'] if r['optimal_wdl_max']==1]
        print(row['world'],row['root'],'escape',row['escape'],'winning-possible regions',good)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('square',type=Path);p.add_argument('rectangle',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();run(a.square,a.rectangle,a.output)
