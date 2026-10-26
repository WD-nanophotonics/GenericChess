"""A fixed ordinary-Leap input catalogue: Core one-ply only, never solving.

Retain all scheduled slots and compiler refusals. This is NOT a Player benchmark.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime,timezone
from itertools import product
import argparse,gzip,hashlib,json,time
from pathlib import Path

from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece,PieceType
from generic_chess.core.transition import legal_successors
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import RuleSet,ruleset_to_dict,compute_fingerprint
from generic_chess.session.session import GameSession
from scripts.research_record import record_value
from scripts.leaper_prospective_geometry import joint_key,effective,descriptor,stable
from tools.local_agent.common import write_json


def definition(n,aa,bb,layout):
    kk=tuple((x,y) for x in (-1,0,1) for y in (-1,0,1) if (x,y)!=(0,0))
    types=tuple(PieceType(name,name,tuple(LeapAtom(tuple(v)) for v in moves),is_anchor=name=="K")
                for name,moves in (("K",kk),("A",aa),("B",bb)))
    coords=([(0,0,0,"K"),(1,0,0,"A"),(0,1,0,"B"),
             (n-1,n-1,1,"K"),(n-2,n-1,1,"A"),(n-1,n-2,1,"B")]
            if layout=="edge_mirrored" else
            [(0,0,0,"K"),(1,1,0,"A"),(2,0,0,"B"),
             (n-1,n-1,1,"K"),(n-2,n-2,1,"A"),(n-3,n-1,1,"B")])
    board=[None]*(n*n)
    for x,y,owner,name in coords:
        if board[x+n*y] is not None: raise ValueError("overlapping frozen setup")
        board[x+n*y]=Piece(owner,name,name)
    return RuleSet(board_size=n,piece_types=types,
        initial_position=tuple(tuple(board[y*n:y*n+n]) for y in range(n)),
        capture_disposition="remove_from_game",
        drop_allowed={name:((False,)*(n*n),)*2 for name in ("A","B")},
        max_ply=128,repetition_limit=4)


def child_observation(action,child):
    raw={"action":record_value(action),"child":record_value(child)}
    return {**raw,"terminal":record_value(child.terminal_status),
            "ply_count":child.ply_count,"history_length":len(child.history)}


def run(plan_file,output):
    if output.exists():raise ValueError("new output required; no refill")
    plan=json.loads(plan_file.read_text());output.mkdir(parents=True)
    start=datetime.now(timezone.utc).isoformat();tick=time.perf_counter()
    rows=[];attempts=0;edgecount=0;cap=False;recorder_failed=False
    for n,i,layout in product(plan["boards"],range(6),plan["layouts"]):
        aa,bb=plan["pairs"][i];name=plan["case_order"][i]
        rr=definition(n,aa,bb,layout)
        row={"board":n,"case":name,"layout":layout,"RuleSet":ruleset_to_dict(rr,include_metadata=True),
             "fingerprint":compute_fingerprint(rr),
             "typed_geometry_key":joint_key(n,{"A":aa,"B":bb}),
             "A_effective":effective(n,aa),"B_effective":effective(n,bb),
             "A_descriptor":descriptor(n,aa),"B_descriptor":descriptor(n,bb),
             "quality":"UNKNOWN; no Player or game; geometry is not playability"}
        if recorder_failed or time.perf_counter()-tick>=300 or edgecount>=512:
            row["status"]="NOT_RUN_AFTER_RECORDER_ERROR" if recorder_failed else "NOT_RUN_CAP";cap=True;rows.append(row);continue
        attempts+=1
        try:
            compiled=compile_legacy_ruleset_for_semantic_execution(rr)
            ss=GameSession(compiled)
            row.update(status="CORE_ROOT_BOUND",record=record_value(ss.to_record()),
                       initial_terminal=record_value(ss.state.terminal_status))
            childrows=[];actions=Counter()
            for action,child in legal_successors(ss.state,compiled):
                if edgecount>=512 or time.perf_counter()-tick>=300:
                    row["status"]="INCOMPLETE_ONEPLY_CAP";cap=True;break
                edgecount+=1
                index=action.from_square.file+n*action.from_square.rank
                actor=ss.state.position.board[index]
                actions[actor.current_type_id]+=1
                observed=child_observation(action,child)
                # Preserve the actual return before additional analysis/aggregation.
                write_json(output/"latest-Core-return.json",observed)
                childrows.append(observed)
            row.update(legal_counts_by_type=dict(actions),children=childrows)
        except Exception as exc:
            row.update(status="RECORDER_FAILED" if "record" in row else "REFUSED_OR_FAILED",
                       error_type=type(exc).__name__,error=str(exc))
            if "record" in row: recorder_failed=True
        rows.append(row)
        write_json(output/"progress.json",{"slots":len(rows),"compile_attempts":attempts,"Core_successor_returns":edgecount,
                                          "latest_status":row["status"]})
    with gzip.GzipFile(filename=str(output/"records.json.gz"),mode="wb",mtime=0) as f:
        f.write(stable(rows).encode())
    summary={"status":("CLOSED_WITH_MISSING" if cap else "CLOSED_WITH_FAILURES" if any(r["status"]!="CORE_ROOT_BOUND" for r in rows) else "COMPLETE_FROZEN_CATALOG"),
        "started_at":start,"ended_at":datetime.now(timezone.utc).isoformat(),
        "seconds":time.perf_counter()-tick,"slots":len(rows),"compile_attempts":attempts,
        "statuses":dict(Counter(r["status"] for r in rows)),
        "Core_successor_returns":edgecount,
        "zero_ordinary_move_roots":sum(r.get("status")=="CORE_ROOT_BOUND" and
            sum(v for k,v in r.get("legal_counts_by_type",{}).items() if k!="K")==0 for r in rows),
        "full_fingerprints":len({r["fingerprint"] for r in rows}),
        "typed_geometry_groups":len({stable(r["typed_geometry_key"]) for r in rows}),
        "Player":0,"solver":0,"games":0,"quality":"UNKNOWN; no outcome-selected exclusion/resampling",
        "source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "plan_sha256":hashlib.sha256(plan_file.read_bytes()).hexdigest(),
        "records_sha256":hashlib.sha256((output/"records.json.gz").read_bytes()).hexdigest()}
    write_json(output/"summary.json",summary);print(stable(summary));return summary


if __name__=="__main__":
    p=argparse.ArgumentParser(__doc__);p.add_argument("--plan",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True);a=p.parse_args();run(a.plan,a.output)
