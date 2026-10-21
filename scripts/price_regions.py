"""Exposed blocked-leg material decision regions; no learning or strength claim.

Build each Core tree once, retaining its real history. Affine leaf values permit
an exact one-parameter action partition of this fixed finite tree, not game WDL.
Raw observations belong under ignored artifacts; publish a concise result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
import random
import time

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.search import terminal_score
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.transition import legal_successors
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_to_dict
from generic_chess.session.serialization import serialize_game_record
from generic_chess.rules.schema import (
    RuleSet, RuleSemanticAction, RuleGeometrySpec, RuleActionEffect,
    RuleSquareRef, RuleStateGuard, RuleSpatialSelector, RuleTypeRef, RuleInvariant,
)
from generic_chess.session.session import GameSession
from scripts.research_record import record_value, write_record

CONFIG = EvaluationConfig(dynamic_mobility_weight=0, anchor_escape_weight=0,
                          promotion_potential_weight=0)
HORSE = ((2,1),(2,-1),(-2,1),(-2,-1),(1,2),(-1,2),(1,-2),(-1,-2))
LOW, HIGH = Fraction(1,8), Fraction(4)


def definition(seed, guarded=True):
    king = PieceType('K','K',tuple(LeapAtom((x,y)) for x in (-1,0,1)
                                  for y in (-1,0,1) if x or y),is_anchor=True)
    types = (king, PieceType('H','H',()), PieceType('B','B',
             tuple(RayAtom(d) for d in ((1,0),(-1,0),(0,1),(0,-1)))))
    rng = random.Random(seed)
    slots = rng.sample(list(range(1,15)), 6)
    board = [None]*16
    board[0], board[15] = Piece(0,'K','K'), Piece(1,'K','K')
    for slot,(owner,tid) in zip(slots,((0,'H'),(0,'H'),(0,'B'),(1,'H'),(1,'H'),(1,'B'))):
        board[slot] = Piece(owner,tid,tid)
    actions=[]
    for j,offset in enumerate(HORSE):
        leg = (offset[0]//2,0) if abs(offset[0])==2 else (0,offset[1]//2)
        ref = RuleSquareRef('offset_from_source',offset=leg)
        guard = RuleStateGuard(aggregation='count',owner='any',type_ref=RuleTypeRef('any'),
            compare_field='base',promoted='any',location='board',
            spatial=RuleSpatialSelector('exact',refs=(ref,)),comparison='eq',value=0)
        for relation in ('empty','enemy'):
            effects=() if relation=='empty' else (RuleActionEffect('remove',
                square_ref=RuleSquareRef('target'),piece_owner='opponent'),)
            actions.append(RuleSemanticAction(name=f'h{j}_{relation}',type_ids=('H',),
                geometry=RuleGeometrySpec('leap',offset=offset),target_relation=relation,
                composition='augment',state_guards=(guard,) if guarded else (),
                effects=effects+(RuleActionEffect('move',from_ref=RuleSquareRef('source'),
                    to_ref=RuleSquareRef('target')),),invariants=(RuleInvariant('own_anchor_safe'),)))
    return RuleSet(board_size=4,piece_types=types,
        initial_position=tuple(tuple(board[4*r:4*r+4]) for r in range(4)),
        drop_allowed={t:((False,)*16,)*2 for t in ('H','B')},
        semantic_actions=tuple(actions),max_ply=128,repetition_limit=4)


class TreeLimit(RuntimeError): pass


class Budget:
    def __init__(self, seconds, edges):
        self.deadline=time.perf_counter()+seconds
        self.maximum=edges
        self.edges=0
    def check(self):
        if self.edges>=self.maximum or time.perf_counter()>=self.deadline:
            raise TreeLimit('complete-tree cost fuse; no partial score')
        self.edges+=1


def feature(state, root):
    counts={'H':0,'B':0}
    for piece in state.position.board:
        if piece is not None and piece.current_type_id in counts:
            counts[piece.current_type_id] += 1 if piece.owner==root else -1
    # These authored rules have no executable drops: captured custody is inert.
    return (1000*counts['H'],1000*counts['B'])


def build_tree(state,compiled,depth,root,budget,forms,ply=0,leaf_features=feature):
    budget.check()
    if state.terminal_status.is_terminal:
        value=terminal_score(state.terminal_status,state.position.side_to_move,ply)
        form=(0,value if state.position.side_to_move==root else -value)
        forms.add(form)
        return ('leaf',form)
    if depth==0:
        form=leaf_features(state,root)
        forms.add(form)
        return ('leaf',form)
    children=tuple((str(a),build_tree(c,compiled,depth-1,root,budget,forms,ply+1,leaf_features))
                   for a,c in sorted(legal_successors(state,compiled),key=lambda z:str(z[0])))
    if not children: raise AssertionError('ongoing state without successors')
    return ('max' if state.position.side_to_move==root else 'min',children)


def tree_value(node,x,scale=Fraction(1)):
    if node[0]=='leaf':
        a,b=node[1]
        return b if abs(b)>=900000000 else (a*x+b)*scale
    values=[tree_value(child,x,scale) for _,child in node[1]]
    return (max if node[0]=='max' else min)(values)


def response(tree,x,scale=Fraction(1)):
    values={a:tree_value(child,x,scale) for a,child in tree[1]}
    best=max(values.values())
    return best,tuple(a for a,v in values.items() if v==best)


def partition(tree,forms,low=LOW,high=HIGH):
    # Every internal value is one leaf form. No order can change between any
    # pairwise leaf crossing; extra breakpoints are harmless and visible.
    cuts={low,high}
    for a,b in forms:
        for c,d in forms:
            if a!=c:
                x=Fraction(d-b,a-c)
                if low<x<high:cuts.add(x)
    cuts=sorted(cuts)
    rows=[]
    for i,x in enumerate(cuts):
        score,actions=response(tree,x)
        rows.append(dict(kind='point',lo=str(x),hi=str(x),score=str(score),actions=actions))
        if i+1<len(cuts):
            mid=(x+cuts[i+1])/2
            _,actions=response(tree,mid)
            rows.append(dict(kind='open',lo=str(x),hi=str(cuts[i+1]),actions=actions))
    return rows


def public_check(session,profile,h,b,tree,seconds,depth=2):
    selected=replace(profile,board_value_by_type={'K':0,'H':h,'B':b},
                     hand_value_by_base_type={'K':0,'H':0,'B':0},
                     promotion_gain_by_type={'K':0,'H':0,'B':0})
    player=AlphaBetaPlayer(session.compiled,evaluator_override=Evaluator(session.compiled,selected,CONFIG),
        use_disk_cache=False,use_tt=False,use_ordering=False,use_native_semantic_legality=False,
        tuning=SearchTuning(use_root_tactical=False))
    before=session.to_record()
    state_before=session.state
    witnesses_before=session._search_witnesses
    decision=player.choose_action(session,SearchLimits(max_depth=depth,max_nodes=100000,
        max_time_seconds=seconds,quiescence_max_depth=0,quiescence_hard_max_depth=0))
    if (before!=session.to_record() or state_before!=session.state
            or witnesses_before!=session._search_witnesses):
        raise AssertionError('search mutated record/state/history witnesses')
    score,actions=response(tree,Fraction(h,b),Fraction(b,1000))
    # Scale static material only; Core terminal scores keep their mate distance.
    complete=decision.completed_depth==depth
    if complete:
        if decision.score!=score or str(decision.action) not in actions:
            raise AssertionError((decision.score,score,str(decision.action),actions))
    return dict(h=h,b=b,complete=complete,reference_score=str(score),
                reference_actions=actions,decision=record_value(decision))


def run(output, depth=2, seeds=tuple(range(732001,732009))):
    if output.exists():raise FileExistsError(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    start=time.perf_counter()
    report=dict(question='Do blocked-leg prices cross complete D2 action regions?',
        scope='8 authored exposed 4x4 layouts; no promotion/drop/aux actions; full history retained, no generic-domain or WDL claim',
        producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        protocol=dict(seeds=list(seeds),prefixes=[0,4,8],depth=depth,
                      global_seconds=180,global_tree_nodes=100000,public_seconds=3,
                      h_over_b=[str(LOW),str(HIGH)],q=0,tt=False,ordering=False),cases=[])
    write_record(output,report)
    budget=Budget(180,100000)
    for seed in report['protocol']['seeds']:
        row=dict(seed=seed,roots=[]);report['cases'].append(row)
        try:
            rules=definition(seed)
            compiled=compile_ruleset_for_execution(rules)
            profile,scope=build_semantic_opportunity_profile(compiled,CONFIG)
            unguarded=compile_ruleset_for_execution(definition(seed,False))
            control,control_scope=build_semantic_opportunity_profile(unguarded,CONFIG)
            row.update(rule=ruleset_to_dict(rules),fingerprint=compiled.ruleset_fingerprint,
                profile=dict(profile.board_value_by_type),unguarded_profile=dict(control.board_value_by_type),
                h_over_b=str(Fraction(profile.board_value_by_type['H'],profile.board_value_by_type['B'])),
                raw={t:r['raw'] for t,r in scope['types'].items()},
                unguarded_raw={t:r['raw'] for t,r in control_scope['types'].items()},
                hand_policy=scope['hand_policy'])
            session=GameSession(compiled)
            rng=random.Random(seed+100000)
            for ply in range(9):
                if ply in (0,4,8):
                    root=dict(ply=ply,record=json.loads(serialize_game_record(session.to_record())),
                              terminal=record_value(session.state.terminal_status))
                    row['roots'].append(root)
                    if not session.state.terminal_status.is_terminal:
                        t=time.perf_counter();forms=set();n=budget.edges
                        tree=build_tree(session.state,compiled,depth,session.state.position.side_to_move,budget,forms)
                        root.update(tree_nodes=budget.edges-n,tree_seconds=time.perf_counter()-t,
                            leaf_forms=sorted(forms),partition=partition(tree,forms))
                        for label,p in [('guarded',profile),('unguarded',control)]:
                            ratio=Fraction(p.board_value_by_type['H'],p.board_value_by_type['B'])
                            score,acts=response(tree,ratio)
                            root[label]=dict(ratio=str(ratio),score=str(score),actions=acts)
                        root['checks']=[public_check(session,profile,h,1000,tree,3,depth)
                                        for h in (125,500,1000,2000,4000)]
                    write_record(output,report)
                if ply==8 or session.state.terminal_status.is_terminal:break
                actions=sorted(session.legal_actions(),key=str)
                session.submit(rng.choice(actions))
        except TreeLimit as exc:
            row['incomplete']=str(exc);break
        except (ValueError,RuntimeError) as exc:
            row['failure']=f'{type(exc).__name__}: {exc}'
        write_record(output,report)
    report.update(wall_seconds=time.perf_counter()-start,tree_nodes=budget.edges,producer_finished=True)
    write_record(output,report)
    print({'cases':len(report['cases']),'tree_nodes':budget.edges,'seconds':report['wall_seconds']})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    parser.add_argument('--depth',type=int,default=2,choices=(2,3))
    parser.add_argument('--seeds',type=int,nargs='+',default=list(range(732001,732009)))
    args=parser.parse_args()
    run(args.output,args.depth,tuple(args.seeds))
