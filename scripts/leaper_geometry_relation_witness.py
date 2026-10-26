"""Two pure-Leap IR counterexamples to an UNLABELLED geometry-union key.

Both use the SAME fixed board. Only ordinary quiet/capture direction roles swap.
No dynamic guard, Ray, promotion/drop, solver, Player or game.
"""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
import argparse,hashlib,json

from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece,PieceType
from generic_chess.rules.schema import (
    RuleSet,RuleSemanticAction,RuleGeometrySpec,RuleReplaceSelector,
    RuleActionEffect,RuleSquareRef,RuleInvariant,ruleset_to_dict,
)
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.session.session import GameSession
from scripts.research_record import record_value
from scripts.leaper_prospective_geometry import edges,joint_key
from tools.local_agent.common import write_json


def definition(swap=False):
    kk=tuple(LeapAtom((x,y)) for x in (-1,0,1) for y in (-1,0,1) if (x,y)!=(0,0))
    types=(PieceType("K","K",kk,is_anchor=True),
           PieceType("C","C",(LeapAtom((1,0)),LeapAtom((0,1)))))
    board=[None]*16
    for index,owner,name in ((0,0,"K"),(5,0,"C"),(9,1,"C"),(15,1,"K")):
        board[index]=Piece(owner,name,name)
    actions=[]
    for relation,offset in (("empty",(0,1) if swap else (1,0)),
                            ("enemy",(1,0) if swap else (0,1))):
        effects=(() if relation=="empty" else (
            RuleActionEffect("remove",square_ref=RuleSquareRef("target"),
                             piece_owner="opponent",disposition="remove_from_game"),))
        effects+= (RuleActionEffect("move",from_ref=RuleSquareRef("source"),
                                    to_ref=RuleSquareRef("target")),)
        actions.append(RuleSemanticAction(
            name="quiet" if relation=="empty" else "capture",type_ids=("C",),
            geometry=RuleGeometrySpec(kind="leap",offset=offset),
            target_relation=relation,composition="replace_legacy",
            replace_selector=RuleReplaceSelector(type_ids=("C",),action_family="board",
                target_relation=relation,geometry_kind="leap",replace_all_matching=True),
            effects=effects,invariants=(RuleInvariant("own_anchor_safe"),)))
    return RuleSet(board_size=4,piece_types=types,
        initial_position=tuple(tuple(board[y*4:y*4+4]) for y in range(4)),
        capture_disposition="remove_from_game",drop_allowed={"C":((False,)*16,)*2},
        max_ply=128,repetition_limit=4,semantic_actions=tuple(actions))


def run(output):
    if output.exists():raise ValueError("no replacement of closed evidence")
    rows=[]
    for swap in (False,True):
        rr=definition(swap);ss=GameSession(compile_semantic_ruleset(rr))
        aa=ss.legal_actions()
        rows.append({"swap":swap,"ruleset":ruleset_to_dict(rr,include_metadata=True),
            "record":record_value(ss.to_record()),"state":record_value(ss.state),
            "actions":record_value(aa),
            "ordinary_actions":[record_value(a) for a in aa
                                if a.from_square.file==1 and a.from_square.rank==1]})
    assert [len(r["ordinary_actions"]) for r in rows]==[2,0]
    result={"at":datetime.now(timezone.utc).isoformat(),"rows":rows,
        "source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "empty_board_unlabelled_union_same":True,
        "full_fixed_board_legal_choices_differ":True,
        "scope":"negative admissibility witness; not ordinary move/capture-same-direction census",
        "Player":0,"solver":0,"games":0}
    write_json(output,result);print(json.dumps({"ordinary_counts":[2,0],"full_actions":[len(r["actions"]) for r in rows]}))
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser(__doc__);p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();run(a.output)
