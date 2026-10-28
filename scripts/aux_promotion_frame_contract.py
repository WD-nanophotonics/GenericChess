"""One literal game-isomorphic rotation test of rank-forward promotion value.

Not a general symmetry canonicalizer, new rules implementation or default fix.
"""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
from collections import Counter
import argparse,json,hashlib
from generic_chess.core.coordinates import Square,square_to_index,index_to_square
from generic_chess.core.pieces import Piece,PieceType
from generic_chess.core.movement import LeapAtom
from generic_chess.rules.schema import RuleSet,ruleset_to_dict,ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset,compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.core.identity import repetition_identity_key
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.evaluator import Evaluator
from scripts.research_record import record_value
def enc(v):return json.dumps(record_value(v),sort_keys=True,separators=(",",":")).encode()
def R(s):return Square(3-s.rank,s.file)
def definitions():
    n=4;atoms=tuple(LeapAtom((x,y))for x in(-1,0,1)for y in(-1,0,1)if(x,y)!=(0,0))
    K=PieceType("K","K",atoms,is_anchor=True)
    P=PieceType("P","P",(LeapAtom((0,1)),),is_promotable=True,promotion_target_ids=("G",))
    G=PieceType("G","G",atoms)
    board=[[None]*n for _ in range(n)]
    for owner,t,x,y in[(0,"K",0,0),(1,"K",3,3),(0,"P",1,1)]:board[y][x]=Piece(owner,t,t,False)
    off=(False,)*16
    a=RuleSet(board_size=4,piece_types=(K,P,G),initial_position=tuple(map(tuple,board)),
        drop_allowed={"P":(off,off),"G":(off,off)},
        promotion_allowed={"P":(frozenset({(Square(1,1),Square(1,2))}),frozenset({(Square(2,2),Square(2,1))}))},
        promotion_forced={"P":(frozenset(),frozenset())},
        capture_disposition="remove_from_game",max_ply=32,repetition_limit=4,stalemate_result="draw")
    rotated=[[None]*n for _ in range(n)]
    for y,row in enumerate(board):
        for x,p in enumerate(row):
            s=R(Square(x,y));rotated[s.rank][s.file]=p
    b=replace(a,piece_types=tuple(replace(t,movement_atoms=tuple(LeapAtom((-v.offset[1],v.offset[0]))for v in t.movement_atoms))for t in a.piece_types),
        initial_position=tuple(map(tuple,rotated)),
        promotion_allowed={t:tuple(frozenset((R(fr),R(to))for fr,to in pairs)for pairs in owners)for t,owners in a.promotion_allowed.items()},
        promotion_forced={t:tuple(frozenset(R(s)for s in squares)for squares in owners)for t,owners in a.promotion_forced.items()})
    return a,b
def freeze(path):
    a,b=definitions();v=dict(source="48749ec334c9eb42955a844f06e1d101bb2a02e2",
        literal_rules=[ruleset_to_dict(a),ruleset_to_dict(b)],position_map="R(x,y)=(3-y,x); owner unchanged; vector(-dy,dx), commutes with owner180 frame",
        max_depth=2,max_paired_edges=1000,
        predicted="Mapped full-game mechanics should agree; north rank-forward approach bonus may not be90degree covariant. This is an explicit desired-equivalence test, not an existing promised90degree product contract.")
    raw=enc(v);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():assert path.read_bytes()==raw
    else:
        with path.open("xb")as f:f.write(raw)
    return hashlib.sha256(raw).hexdigest()
def run(frozen,output):
    f=json.loads(frozen.read_bytes());a,b=map(ruleset_from_dict,f["literal_rules"]);result={}
    for route,C in(("legacy",compile_ruleset),("semantic",compile_legacy_ruleset_for_semantic_execution)):
        ca,cb=C(a),C(b);cfg=EvaluationConfig();off=replace(cfg,promotion_potential_weight=0)
        pa,pb=build_ruleset_profile(ca,cfg),build_ruleset_profile(cb,cfg)
        assert dict(pa.board_value_by_type)==dict(pb.board_value_by_type)
        assert dict(pa.hand_value_by_base_type)==dict(pb.hand_value_by_base_type)
        assert dict(pa.promotion_gain_by_type)==dict(pb.promotion_gain_by_type)
        table_rows=0
        for t in ca.types_by_id:
            assert abs(pa.piece_profiles[t].raw_capability_score-pb.piece_profiles[t].raw_capability_score)<1e-12
            for owner in(0,1):
                for i in range(16):
                    j=square_to_index(R(index_to_square(i,4)),4)
                    assert {R(s)for s in ca.empty_mobility[t][owner][i]}==set(cb.empty_mobility[t][owner][j]);table_rows+=1
        pm={};gm={}
        if route=="semantic":
            ap={p.name:p for p in ca.ir.patterns if ca.ir.geometry[p.geometry_ids[0]].kind!="drop"}
            bp={p.name:p for p in cb.ir.patterns if cb.ir.geometry[p.geometry_ids[0]].kind!="drop"}
            assert set(ap)==set(bp)
            for name,p in ap.items():
                q=bp[name];x,y=record_value(p),record_value(q)
                for z in(x,y):z.pop("pattern_id");z.pop("geometry_ids")
                assert x==y
                pm[p.pattern_id]=q.pattern_id
                for ga,gb in zip(p.geometry_ids,q.geometry_ids):
                    xa,xb=record_value(ca.ir.geometry[ga]),record_value(cb.ir.geometry[gb])
                    xa["offset"]=[-xa["offset"][1],xa["offset"][0]]
                    xa["geometry_id"]=gb
                    xa["paths"]={owner:{str(square_to_index(R(index_to_square(int(src),4)),4)):
                        [square_to_index(R(index_to_square(dst,4)),4)for dst in destinations]
                        for src,destinations in rows.items()}for owner,rows in xa["paths"].items()}
                    assert xa==xb;gm[ga]=gb
        def mapped(action):
            args=dict(from_square=R(action.from_square),to_square=R(action.to_square))
            if route=="semantic":args.update(pattern_id=pm[action.pattern_id],geometry_id=gm[action.geometry_id])
            return replace(action,**args)
        ea,eb=Evaluator(ca,pa,cfg),Evaluator(cb,pb,cfg)
        za,zb=Evaluator(ca,build_ruleset_profile(ca,off),off),Evaluator(cb,build_ruleset_profile(cb,off),off)
        sa,sb=GameSession(ca),GameSession(cb)
        root=dict(old_value=ea.evaluate(sa.state),rotated_value=eb.evaluate(sb.state),
            old_promotion_OFF=za.evaluate(sa.state),rotated_promotion_OFF=zb.evaluate(sb.state),
            board_values=dict(pa.board_value_by_type),promotion_gains=dict(pa.promotion_gain_by_type),
            old_P_bonus=ea._promotion_bonus(sa.state.position.board[5],5),
            rotated_P_bonus=eb._promotion_bonus(sb.state.position.board[6],6))
        assert root["old_promotion_OFF"]==root["rotated_promotion_OFF"]
        assert root["old_value"]-root["rotated_value"]==root["old_P_bonus"]-root["rotated_P_bonus"]==1
        keys={};nodes=0;edges=0;replays=0
        def walk(x,y,depth):
            nonlocal nodes,edges,replays
            nodes+=1
            expected=[None]*16
            for i,p in enumerate(x.state.position.board):expected[square_to_index(R(index_to_square(i,4)),4)]=p
            assert tuple(expected)==y.state.position.board and x.state.position.hands==y.state.position.hands
            assert x.state.position.side_to_move==y.state.position.side_to_move and x.state.ply_count==y.state.ply_count
            assert x.state.terminal_status==y.state.terminal_status
            kx,ky=repetition_identity_key(x.state.position,ca),repetition_identity_key(y.state.position,cb)
            assert keys.setdefault(kx,ky)==ky and len(set(keys.values()))==len(keys)
            assert {keys[k]:v for k,v in x.state.repetition_counts}==dict(y.state.repetition_counts)
            aa,bb=x.legal_actions(),y.legal_actions()
            assert Counter(enc(mapped(z))for z in aa)==Counter(enc(z)for z in bb)
            if depth==f["max_depth"]:return
            for act in aa:
                assert edges<f["max_paired_edges"]
                xr,yr=x.to_record(),y.to_record()
                xx,yy=GameSession.replay(ca,xr),GameSession.replay(cb,yr);replays+=len(xr.actions)+len(yr.actions)
                xx.submit(act);yy.submit(mapped(act));edges+=1;walk(xx,yy,depth+1)
        walk(sa,sb,0)
        result[route]=dict(root=root,compiled_owner_type_source_rows=table_rows,
            finite_prefixes=nodes,paired_edges=edges,direct_edge_submissions=2*edges,prefix_replay_submissions=replays,
            actual_Session_submit_calls=2*edges+replays,pattern_map=pm,geometry_map=gm,
            finite_count_identity_bijection=len(keys),old_record=record_value(sa.to_record()),rotated_record=record_value(sb.to_record()))
    v=dict(source=f["source"],frozen_input_sha256=hashlib.sha256(frozen.read_bytes()).hexdigest(),routes=result,
        interpretation="Source's explicit rank-forward promotion heuristic is not90degree covariant on this exact otherwise mapped game. Rule coordinate convention calls north forward; no existing universal90degree evaluator promise is alleged. This is one additional required-policy distinction, not a profile-normalization mismatch, search bug, strength loss or permission for a patch.",
        proof_scope="No extra effects/claims/pass/drop/hands/setups. All Leap tables and explicitpromotionmasks transformed; R commutes withowner180frame; move/remove, mobilepromotion, royal safety and typedposition identity transport underbijectiveboardR andunchangedclock. Finite2ply controls are not a machine proof of every future rule. No canonicalizer, Player, search or learning run.")
    output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes((json.dumps(v,indent=2)+"\n").encode());return v
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("phase",choices=("freeze","run"));p.add_argument("--frozen",type=Path,required=True);p.add_argument("--output",type=Path);a=p.parse_args()
    if a.phase=="freeze":print(freeze(a.frozen))
    else:print(json.dumps(run(a.frozen,a.output),indent=2))
