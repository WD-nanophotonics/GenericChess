import json
from dataclasses import replace
from pathlib import Path
from fractions import Fraction
from scripts.price_regions_mixed import fixture,CONFIG
from scripts.price_regions import build_tree,Budget,partition,response
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from scripts.research_record import write_record,record_value

source=json.loads(Path('artifacts/price-regions-20261021/mixed.json').read_text())
c=compile_ruleset_for_execution(fixture());profile,_=build_semantic_opportunity_profile(c,CONFIG)
base_board={'K':0,'R':500,'TP':1000};base_hand={'K':0,'R':450,'TP':900};zeros={t:0 for t in base_board}
material=Evaluator(c,replace(profile,board_value_by_type=base_board,hand_value_by_base_type=base_hand,promotion_gain_by_type=zeros),CONFIG)
full_config=EvaluationConfig()
dynamic=Evaluator(c,replace(profile,board_value_by_type=zeros,hand_value_by_base_type=zeros,promotion_gain_by_type=zeros),full_config)

def coeff(state,owner):
    sign=1 if state.position.side_to_move==owner else -1
    return (material.evaluate(state)*sign,dynamic.evaluate(state)*sign)

rows=[]
for root in source['roots']:
    s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])))
    forms=set();tree=build_tree(s.state,c,2,s.state.position.side_to_move,Budget(10,10000),forms,leaf_features=coeff)
    regions=partition(tree,forms,Fraction(1,50),Fraction(4));checks=[]
    for q in (1,2,5,10,25,50,100,200):
        scale=Fraction(q,50)
        board={t:int(v*scale) for t,v in base_board.items()};hand={t:int(v*scale) for t,v in base_hand.items()}
        assert all(v*scale==board[t] for t,v in base_board.items())
        assert all(v*scale==hand[t] for t,v in base_hand.items())
        p=replace(profile,board_value_by_type=board,hand_value_by_base_type=hand,promotion_gain_by_type=zeros)
        ev=Evaluator(c,p,full_config)
        player=AlphaBetaPlayer(c,evaluator_override=ev,use_disk_cache=False,use_tt=False,use_ordering=False,
            use_native_semantic_legality=False,tuning=SearchTuning(use_root_tactical=False))
        before=s.state;d=player.choose_action(s,SearchLimits(max_depth=2,max_nodes=100000,max_time_seconds=3,
            quiescence_max_depth=0,quiescence_hard_max_depth=0))
        expected,actions=response(tree,scale)
        assert d.completed_depth==2 and d.score==expected and str(d.action) in actions
        assert before==s.state
        checks.append(dict(scale=str(scale),board=board,hand=hand,expected_score=str(expected),decision=record_value(d)))
    rows.append(dict(ply=root['ply'],record=root['record'],leaf_coefficients=sorted(forms),regions=regions,checks=checks))
write_record(Path('artifacts/price-regions-20261021/fixed-dynamic-scale.json'),
    dict(scope='Posthoc same exposed8x8 fixture; fixed current legacy dynamic weights2/5/3, promotion gains0. Scale only material, preserve all ratios and rule/history. Not all-active scaling, utility or a default change.',rows=rows))
print([(r['ply'],len({tuple(x['actions']) for x in r['regions']}),[(c['scale'],c['decision']['score'],c['decision']['action']['pattern_id']) for c in r['checks']]) for r in rows])
