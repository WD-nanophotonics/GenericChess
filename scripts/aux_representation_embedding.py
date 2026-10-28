"""Source-specific order embedding, not a new evaluator or game solver."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from fractions import Fraction
from scripts.aux_representation_contract import definitions
from generic_chess.rules.compiler import compile_ruleset,compile_legacy_ruleset_for_semantic_execution
from generic_chess.ai.evaluation.config import EvaluationConfig,MATE_SCORE,MAX_STATIC_EVAL
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.evaluator import Evaluator

def control():
    a,b,_=definitions();cfg=EvaluationConfig();routes={}
    assert a.board_size==b.board_size==4 and a.max_ply==b.max_ply==32
    assert a.capture_disposition==b.capture_disposition=="remove_from_game"
    assert a.repetition_policy==b.repetition_policy=="draw"
    for key,C in (("legacy",compile_ruleset),("semantic",compile_legacy_ruleset_for_semantic_execution)):
        ca,cb=C(a),C(b)
        pa,pb=build_ruleset_profile(ca,cfg),build_ruleset_profile(cb,cfg)
        assert pa.board_value_by_type["P"]==1000 and pb.board_value_by_type["P"]==569
        assert sum(p is not None and p.current_type_id=="P" for p in ca.initial_position.board)==1
        assert all(not h.counts for h in ca.initial_position.hands)
        assert not any(any(owner) for masks in ca.drop_allowed.values() for owner in masks)
        assert not a.semantic_actions and not b.semantic_actions
        assert all(not zone for zone in Evaluator(cb,pb,cfg)._zones.values())
        routes[key]=dict(old_P=pa.board_value_by_type["P"],new_P=pb.board_value_by_type["P"],config_hash=pa.config_hash)
    # Coarse true bounds on the actual default dynamic terms.
    mobility=a.board_size**2*abs(cfg.dynamic_mobility_weight)
    escape=8*abs(cfg.anchor_escape_weight)
    check=10*abs(cfg.anchor_escape_weight)
    D=mobility+escape+check
    assert (mobility,escape,check,D)==(32,40,50,122)
    old,new=1000,569;assert min(old,new)>2*D
    # A and B value supports on all structurally possible inventory counts,
    # overapproximating reachable dynamic values. Not actual states or WDL.
    values={c*old+d:c*new+d for c in (0,1) for d in range(-D,D+1)}
    assert len(values)==2*(2*D+1)
    for ply in range(a.max_ply+1):
        for sign in (-1,1):values[sign*(MATE_SCORE-ply)]=sign*(MATE_SCORE-ply)
    assert values[0]==0
    xs=sorted(values);ys=[values[x] for x in xs]
    assert all(x<y for x,y in zip(ys,ys[1:]))
    assert max(old+D,new+D)<MAX_STATIC_EVAL
    Tmin=MATE_SCORE-a.max_ply
    def f(x):
        if x<=D:return Fraction(x)
        if x<old-D:
            return Fraction(D)+Fraction((new-2*D)*(x-D),old-2*D)
        if x<=old+D:return Fraction(x-(old-new))
        if x<Tmin:
            return Fraction(new+D)+Fraction((Tmin-new-D)*(x-old-D),Tmin-old-D)
        return Fraction(x)
    assert all(f(x)==values[x] for x in xs)
    slopes=(Fraction(1),Fraction(new-2*D,old-2*D),Fraction(1),Fraction(Tmin-new-D,Tmin-old-D),Fraction(1))
    assert all(s>0 for s in slopes)
    return dict(source="d91928c548d3a69c83260adfd4198447c69125a4",
        routes=routes,dynamic_bound_components=dict(mobility=mobility,escape=escape,check=check,promotion=0,hands=0),
        absolute_dynamic_bound=D,old_nonterminal_bands=[[-D,D],[old-D,old+D]],
        new_nonterminal_bands=[[-D,D],[new-D,new+D]],
        minimum_terminal_win_magnitude=Tmin,finite_value_support_size=len(values),
        adjacent_strict_order_checks=len(values)-1,positive_piecewise_slopes=[str(x)for x in slopes],
        old_to_new_shift_if_P_present=-(old-new),
        theorem="On the SAME finite history-correct tree/frontier, seat0 terminal/static leaf values obey one common strictly increasing f. min/max commute with f, so all root optimal-action sets/ties are identical by induction. This exact pair cannot exhibit a changed complete fixed-frontier argmax merely from its1000->569P price.",
        premises="Exact one-P0 restricted pair from frozen c4278563, K0/K1 preserved, removal capture, no hand/drop/create, all P->X destinations structurally dead, same rules/history and exact paired frontier. No price fitting or new normalization.",
        limits="This is not true game value or evidence about actual equal-service retained decisions. Changing profile/setup work, ordering, score margins, selective search, qfrontier, cancellation or incompatible TT can change actual visited work/frontier. Actor-centric negamax must be interpreted via seat0 min/max; f need not be odd. No guarantee for the priorA/B/C pair, merged type labels, or other rules.")
def finite_static_control():
    """All inventory-compatible board placements, not asserted legal histories."""
    from itertools import permutations
    from dataclasses import replace
    from generic_chess.core.pieces import Piece
    from generic_chess.core.position import Position
    from types import SimpleNamespace
    from collections import Counter
    a,b,_=definitions();cfg=EvaluationConfig();result={}
    for route,C in (("legacy",compile_ruleset),("semantic",compile_legacy_ruleset_for_semantic_execution)):
        ca,cb=C(a),C(b);pa,pb=build_ruleset_profile(ca,cfg),build_ruleset_profile(cb,cfg)
        ea,eb=Evaluator(ca,pa,cfg),Evaluator(cb,pb,cfg)
        hist={0:Counter(),1:Counter()};n=0
        for k0,k1 in permutations(range(16),2):
            for ps in [-1]+[i for i in range(16)if i not in(k0,k1)]:
                board=[None]*16;board[k0]=Piece(0,"K","K",False);board[k1]=Piece(1,"K","K",False)
                count=int(ps>=0)
                if count:board[ps]=Piece(0,"P","P",False)
                for actor in (0,1):
                    xa=replace(ca.initial_position,board=tuple(board),side_to_move=actor)
                    xb=replace(cb.initial_position,board=tuple(board),side_to_move=actor)
                    va=ea.evaluate(SimpleNamespace(position=xa))*(1 if actor==0 else -1)
                    vb=eb.evaluate(SimpleNamespace(position=xb))*(1 if actor==0 else -1)
                    assert vb-va==-431*count
                    d=va-1000*count;assert -122<=d<=122
                    hist[count][d]+=1;n+=1
        assert n==7200
        result[route]=dict(static_position_inputs=n,actual_evaluator_calls=2*n,
            by_inventory={str(k):dict(inputs=sum(h.values()),minimum_dynamic=min(h),maximum_dynamic=max(h),distinct_dynamic_values=len(h))for k,h in hist.items()})
    return dict(routes=result,scope="All7200typed two-royal/optionalP board/actor assignments per compiler route, including unreachable/illegal positions. Pure evaluator calls via explicit position-only inputs; no Core action execution, terminal/WDL or search. Exhaustive finite envelope validation only; all-history game relation remains the separate structural argument.")
def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);p.add_argument("--enumerate-static",action="store_true");a=p.parse_args();v=finite_static_control() if a.enumerate_static else control()
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes((json.dumps(v,indent=2)+"\n").encode());print(json.dumps(v,indent=2))
if __name__=="__main__":main()
