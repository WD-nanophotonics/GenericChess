"""Finite material regions on the existing mixed-semantic lifecycle fixture.

This is a development mechanism check, never a new learner or solver. The same
full Core tree supplies two leaf projections: hand BASE values present/omitted.
"""
from dataclasses import replace
from fractions import Fraction
import json,time
from pathlib import Path

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import legal_successors
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_to_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record
from scripts.price_regions import build_tree,Budget,partition,response
from scripts.research_record import write_record,record_value
from tests.rule_semantics_ir_fixtures import weird_rulesets

CONFIG=EvaluationConfig(dynamic_mobility_weight=0,anchor_escape_weight=0,promotion_potential_weight=0)


def fixture():
    fixtures=weird_rulesets()
    board=[[None]*8 for _ in range(8)]
    for owner,tid,f,r in ((0,'K',4,0),(1,'K',7,7),(0,'R',0,0),(0,'R',0,1),
                         (0,'R',0,2),(0,'R',1,1),(1,'R',1,3),(1,'R',1,4)):
        board[r][f]=Piece(owner,tid,tid)
    return replace(fixtures[2],initial_position=tuple(map(tuple,board)),
        semantic_actions=(fixtures[1].semantic_actions[0],fixtures[2].semantic_actions[0]),
        drop_allowed={'R':((True,)*64,)*2,'TP':((False,)*64,)*2})


def counts(state,root):
    values=[0,0,0,0]
    for piece in state.position.board:
        if piece is not None and piece.current_type_id in ('R','TP'):
            values[int(piece.current_type_id=='TP')]+=1 if piece.owner==root else -1
    for owner,hand in enumerate(state.position.hands):
        for tid,count in hand.counts:
            if tid in ('R','TP'):
                values[2+int(tid=='TP')]+=count*(1 if owner==root else -1)
    return tuple(values)


def project(tree,hand,forms):
    if tree[0]=='leaf':
        v=tree[1]
        form=v if len(v)==2 else (1000*v[0]+hand*v[2],1000*v[1]+hand*v[3])
        forms.add(form)
        return ('leaf',form)
    return (tree[0],tuple((a,project(child,hand,forms)) for a,child in tree[1]))


def run(output):
    if output.exists():raise FileExistsError(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    rule=fixture();compiled=compile_ruleset_for_execution(rule);session=GameSession(compiled)
    profile,_=build_semantic_opportunity_profile(compiled,CONFIG)
    report=dict(question='Does the same exact finite-tree price-region method retain promotion, hand BASE and aux expiry?',
        scope='One existing authored 8x8 lifecycle fixture, exposed; not all generated rules or WDL.',
        rule=ruleset_to_dict(rule),protocol=dict(roots=[4,5,6],depth=2,tree_seconds=90,tree_nodes=30000,
            r_over_tp=['1/8','4'],hand_ratios=[0,.9],q=0,tt=False,ordering=False,public_seconds=5),roots=[])
    write_record(output,report)
    route=(((1,1),(1,3),False),((7,7),(6,7),False),((1,3),(1,4),False),
           ((6,7),(5,7),False),((0,0),(1,1),True),((5,7),(4,7),False))
    budget=Budget(90,30000);start=time.perf_counter()
    for ply in range(7):
        if ply in (4,5,6):
            before=session.state;rec=session.to_record()
            assert GameSession.replay(compiled,rec).state==before
            row=dict(ply=ply,record=json.loads(serialize_game_record(rec)),
                     features=counts(before,before.position.side_to_move),aux=record_value(before.position.aux_state),
                     history_entries=len(before.history),projections=[])
            report['roots'].append(row)
            raw=set();n=budget.edges;t=time.perf_counter()
            tree=build_tree(before,compiled,2,before.position.side_to_move,budget,raw,leaf_features=counts)
            row.update(tree_nodes=budget.edges-n,tree_seconds=time.perf_counter()-t,raw_leaf_features=sorted(raw))
            for hand in (0,900):
                forms=set();projected=project(tree,hand,forms)
                p=dict(hand_per_1000=hand,partition=partition(projected,forms),checks=[])
                row['projections'].append(p)
                for r in (250,500,1000,2000,4000):
                    table={'K':0,'R':r,'TP':1000}
                    htable={'K':0,'R':r*hand//1000,'TP':hand}
                    ev=Evaluator(compiled,replace(profile,board_value_by_type=table,hand_value_by_base_type=htable,
                        promotion_gain_by_type={'K':0,'R':0,'TP':0}),CONFIG)
                    player=AlphaBetaPlayer(compiled,evaluator_override=ev,use_disk_cache=False,use_tt=False,
                        use_ordering=False,use_native_semantic_legality=False,tuning=SearchTuning(use_root_tactical=False))
                    d=player.choose_action(session,SearchLimits(max_depth=2,max_nodes=100000,max_time_seconds=5,
                        quiescence_max_depth=0,quiescence_hard_max_depth=0))
                    value,actions=response(projected,Fraction(r,1000))
                    complete=d.completed_depth==2
                    if complete:
                        assert d.score==value and str(d.action) in actions,(d.score,value,d.action,actions)
                    replay=GameSession.replay(compiled,rec)
                    for a in d.principal_variation:replay.submit(a)
                    assert session.state==before and session.to_record()==rec
                    p['checks'].append(dict(r=r,tp=1000,complete=complete,expected_score=str(value),
                        expected_actions=actions,decision=record_value(d),pv_final=record_value(replay.state.position)))
                write_record(output,report)
        if ply==6:break
        source,target,semantic=route[ply]
        action,=[a for a in session.legal_actions() if hasattr(a,'from_square')
            and (a.from_square.file,a.from_square.rank)==source
            and (a.to_square.file,a.to_square.rank)==target
            and a.pattern_id.startswith('sem_')==semantic]
        session.submit(action)
    report.update(wall_seconds=time.perf_counter()-start,tree_nodes=budget.edges)
    write_record(output,report)
    print({'roots':len(report['roots']),'nodes':budget.edges,'seconds':report['wall_seconds']})


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path)
    run(p.parse_args().output)
