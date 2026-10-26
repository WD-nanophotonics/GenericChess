"""Bounded cold quiet-order consumer observation under common D4 maps.

No Player/search, TT or evaluation profile is constructed; captures would fail
closed. This observes MoveOrderer tie-breaking, not strength or final actions.
"""
from datetime import datetime,timezone
from pathlib import Path
from types import SimpleNamespace
import argparse,json,hashlib

from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece,PieceType
from generic_chess.rules.schema import RuleSet,ruleset_to_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.ai.alphabeta.ordering import MoveOrderer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from scripts.leaper_prospective_geometry import D4,vector,square,joint_key,stable
from scripts.research_record import record_value
from tools.local_agent.common import write_json


def definition(matrix,two_actors=False):
    n=4;board=[None]*16
    moves={"K":tuple((x,y) for x in (-1,0,1) for y in (-1,0,1) if (x,y)!=(0,0)),
           "A":((-1,0),(1,0)),"B":((0,-1),(0,1))}
    types=tuple(PieceType(name,name,tuple(LeapAtom(vector(v,matrix)) for v in vv),is_anchor=name=="K")
                for name,vv in moves.items())
    coords=((0,0,"K"),(1,0,"A"),(8,0,"B"),(15,1,"K"))
    if two_actors: coords=coords+((6,0,"A"),)
    for source,owner,name in coords:
        board[square(source,n,matrix)]=Piece(owner,name,name)
    return RuleSet(board_size=n,piece_types=types,
        initial_position=tuple(tuple(board[y*n:y*n+n]) for y in range(n)),
        capture_disposition="remove_from_game",drop_allowed={"A":((False,)*16,)*2,"B":((False,)*16,)*2},
        max_ply=128,repetition_limit=4)


def projection(action):
    return (action.from_square.file+4*action.from_square.rank,
            action.to_square.file+4*action.to_square.rank)


def no_capture(*args):
    raise AssertionError("frozen observation must remain quiet-only")


def run(output,two_actors=False):
    if output.exists():raise ValueError("no refill")
    rows=[];base=None
    for matrix in D4:
        rr=definition(matrix,two_actors);ss=GameSession(compile_legacy_ruleset_for_semantic_execution(rr))
        legal=ss.legal_actions()
        assert all(ss.state.position.board[a.to_square.file+4*a.to_square.rank] is None for a in legal)
        ordered=MoveOrderer().order(ss.state,list(legal),SimpleNamespace(capture_order_value=no_capture),
                                   1,None,None,SearchTuning())
        actual=tuple(projection(a) for a in ordered)
        if base is None:base=actual
        expected=tuple((square(a,4,matrix),square(b,4,matrix)) for a,b in base)
        assert set(actual)==set(expected)
        rows.append({"matrix":matrix,"ruleset":ruleset_to_dict(rr,include_metadata=True),
                     "record":record_value(ss.to_record()),"ordered_actions":record_value(ordered),
                     "actual_physical_order":actual,"mapped_original_order":expected,
                     "same_legal_frontier":True,"order_equivariant":actual==expected,
                     "first_ordered_equivariant":actual[0]==expected[0]})
    result={"at":datetime.now(timezone.utc).isoformat(),"rows":rows,
            "slots":8,"two_actors":two_actors,"frontier_set_parity":sum(r["same_legal_frontier"] for r in rows),
            "ordered_parity":sum(r["order_equivariant"] for r in rows),
            "first_ordered_parity":sum(r["first_ordered_equivariant"] for r in rows),
            "claim":"coldquietMoveOrderer only, not finalPlayer/fallback/strength or deploymenttiming",
            "source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "Player":0,"solver":0,"games":0}
    write_json(output,result);print(stable({k:v for k,v in result.items() if k!="rows"}));return result


if __name__=="__main__":
    p=argparse.ArgumentParser(__doc__);p.add_argument("--output",type=Path,required=True)
    p.add_argument("--two-actors",action="store_true")
    a=p.parse_args();run(a.output,a.two_actors)
