"""One actual Core counterexample to forgetting identical mover type labels.

No engine search, solved WDL label, price fitting or production change.
"""
from __future__ import annotations
from dataclasses import replace
from collections import Counter
from pathlib import Path
import argparse, json, hashlib
from generic_chess.rules.schema import RuleSet,ruleset_to_dict,ruleset_from_dict
from generic_chess.core.coordinates import Square
from generic_chess.core.pieces import Piece,PieceType
from generic_chess.core.movement import LeapAtom
from generic_chess.core.identity import repetition_identity_key
from generic_chess.rules.compiler import compile_ruleset,compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from scripts.research_record import record_value
SOURCE="d91928c548d3a69c83260adfd4198447c69125a4"
def enc(v):return json.dumps(record_value(v),sort_keys=True,separators=(",",":")).encode()
def definitions():
    n=6;atoms=tuple(LeapAtom((x,y)) for x in (-1,0,1) for y in (-1,0,1) if (x,y)!=(0,0))
    K=PieceType("K","K",atoms,is_anchor=True);A=PieceType("A","A",atoms);B=PieceType("B","B",atoms)
    board=[[None]*n for _ in range(n)]
    for owner,t,f,r in [(0,"K",0,0),(1,"K",5,5),(0,"A",2,2),(0,"A",3,2)]:board[r][f]=Piece(owner,t,t,False)
    off=(False,)*(n*n)
    source=RuleSet(board_size=n,piece_types=(K,A),initial_position=tuple(map(tuple,board)),
        drop_allowed={"A":(off,off)},promotion_allowed={},promotion_forced={},
        capture_disposition="remove_from_game",repetition_limit=4,max_ply=64,stalemate_result="draw")
    board[2][3]=Piece(0,"B","B",False)
    colored=replace(source,piece_types=(K,A,B),initial_position=tuple(map(tuple,board)),drop_allowed={"A":(off,off),"B":(off,off)})
    # Four own actions exchange the two ordinary actors using two empty cells.
    # Opponent shuttles its distant anchor after every own action.
    own=[((2,2),(2,3)),((3,2),(2,2)),((2,3),(3,3)),((3,3),(3,2))]
    path=[]
    for _ in range(3):
        for i,a in enumerate(own):
            path.append(a)
            path.append(((5,5),(4,5)) if i%2==0 else ((4,5),(5,5)))
    return source,colored,path
def freeze(path):
    a,b,trace=definitions()
    v=dict(source=SOURCE,literal_rules=dict(source=ruleset_to_dict(a),colored=ruleset_to_dict(b)),
        coordinate_path=trace,
        predicted="Position-level forgetting B->A preserves ordinary actions, but is not injective on repetition identity. Expect a repetition-status difference, not an invariant-game price claim.",
        boundary="Exactly two initial ordinary actors, no promotion/drop/create/aux/claims/pass. Type-label split changes no movement tables; prefix only, no minimax solution.",
        max_submitted_plies_per_rule_route=24)
    raw=enc(v);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():assert path.read_bytes()==raw
    else:
        with path.open("xb") as f:f.write(raw)
    return hashlib.sha256(raw).hexdigest()
def normalized_board(position):
    return tuple(None if p is None else (p.owner,"A" if p.base_type_id=="B" else p.base_type_id,"A" if p.current_type_id=="B" else p.current_type_id,p.promoted) for p in position.board)
def visible_action(a):
    return (a.from_square.file,a.from_square.rank,a.to_square.file,a.to_square.rank,a.promotion_target_id)
def run(frozen,output):
    f=json.loads(frozen.read_bytes());a,b=(ruleset_from_dict(f["literal_rules"][k]) for k in ("source","colored"))
    results={}
    for route,C in (("legacy",compile_ruleset),("semantic",compile_legacy_ruleset_for_semantic_execution)):
        ca,cb=C(a),C(b);sa,sb=GameSession(ca),GameSession(cb);cfg=EvaluationConfig()
        pa,pb=build_ruleset_profile(ca,cfg),build_ruleset_profile(cb,cfg);ea,eb=Evaluator(ca,pa,cfg),Evaluator(cb,pb,cfg)
        assert ca.empty_mobility["A"]==cb.empty_mobility["A"]==cb.empty_mobility["B"]
        assert pa.board_value_by_type["A"]==pb.board_value_by_type["A"]==pb.board_value_by_type["B"]==1000
        keymap={};trace=[];first_alias=None
        def observe():
            nonlocal first_alias
            x,y=sa.state,sb.state
            assert normalized_board(x.position)==normalized_board(y.position)
            assert x.position.hands==y.position.hands and x.position.side_to_move==y.position.side_to_move
            assert x.ply_count==y.ply_count and ea.evaluate(x)==eb.evaluate(y)
            kx,ky=repetition_identity_key(x.position,ca),repetition_identity_key(y.position,cb)
            old_targets={target for key,target in keymap.items() if target==kx}
            keymap[ky]=kx
            if old_targets and len([key for key,target in keymap.items() if target==kx])>1 and first_alias is None:
                first_alias=dict(ply=x.ply_count,source_key=kx,other_colored_keys=[key for key,target in keymap.items() if target==kx])
            pushed=Counter()
            for key,count in y.repetition_counts:pushed[keymap[key]]+=count
            assert dict(pushed)==dict(x.repetition_counts)
            assert x.ply_count==24 or Counter(visible_action(z) for z in sa.legal_actions())==Counter(visible_action(z) for z in sb.legal_actions())
            trace.append(dict(ply=x.ply_count,source_key=kx,colored_key=ky,
                source_current_count=dict(x.repetition_counts)[kx],colored_current_count=dict(y.repetition_counts)[ky],
                source_status=record_value(x.terminal_status),colored_status=record_value(y.terminal_status),
                raw_value=ea.evaluate(x),source_counts=record_value(x.repetition_counts),colored_counts=record_value(y.repetition_counts)))
        observe()
        for start,end in f["coordinate_path"]:
            for s in (sa,sb):
                act=next(z for z in s.legal_actions() if (z.from_square.file,z.from_square.rank)==tuple(start) and (z.to_square.file,z.to_square.rank)==tuple(end))
                s.submit(act)
            observe()
        assert first_alias is not None
        assert sa.state.terminal_status.is_terminal and sa.state.terminal_status.winner is None
        assert not sb.state.terminal_status.is_terminal
        results[route]=dict(trace=trace,first_many_to_one_identity=first_alias,
            source_final_record=record_value(sa.to_record()),colored_final_record=record_value(sb.to_record()),
            actual_Core_transitions=48,all_prefix_raw_values_equal=True,
            conclusion="Not semantically equivalent full-history games: source4fold draw atply24, coloredstillongoing. Same geometry/current projected actions and numeric profile do not imply compatible repetition adjudication.")
    v=dict(source=SOURCE,frozen_input_sha256=hashlib.sha256(frozen.read_bytes()).hexdigest(),routes=results,
        scope="One explicit24ply trace per route,96actualCoretransitions. Not a new game-strength campaign or WDL proof. A many-to-one position projection can preserve movement but cannot be assumed to preserve actual typed repetition counts. No TT/key sharing or product/profile change.")
    output.write_bytes((json.dumps(v,indent=2)+"\n").encode());return v
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("phase",choices=("freeze","run"));p.add_argument("--frozen",type=Path,required=True);p.add_argument("--output",type=Path);a=p.parse_args()
    if a.phase=="freeze":print(freeze(a.frozen))
    else:
        v=run(a.frozen,a.output)
        print(json.dumps({r:{k:x for k,x in d.items() if k not in ("trace","source_final_record","colored_final_record")} for r,d in v["routes"].items()},indent=2))
