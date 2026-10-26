"""Source/geometry-only analysis of the CLOSED failed literal catalogue.

Does not replay Core or fill missing child payloads/frontiers. The bound ignores
king safety and other legal filters; a positive bound is NOT legal availability.
"""
from collections import Counter,defaultdict
from pathlib import Path
from datetime import datetime,timezone
import argparse,gzip,hashlib,json

from generic_chess.core.movement import LeapAtom
from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
from scripts.leaper_prospective_geometry import effective,stable
from tools.local_agent.common import write_json


def run(input_file,output):
    if output.exists():raise ValueError("new derivation required")
    rows=json.loads(gzip.decompress(input_file.read_bytes()))
    resultrows=[];groups=defaultdict(list)
    for row in rows:
        rr=ruleset_from_dict(row["RuleSet"])
        assert compute_fingerprint(rr)==row["fingerprint"]==row["record"]["ruleset_fingerprint"]
        assert rr.capture_disposition=="remove_from_game" and not rr.semantic_actions
        assert not rr.promotion_allowed and not any(any(z) for masks in rr.drop_allowed.values() for z in masks)
        assert row["record"]["actions"]==[]
        n=rr.board_size;board=tuple(z for rank in rr.initial_position for z in rank)
        types={t.type_id:t for t in rr.piece_types}
        possibilities=defaultdict(set)
        for index,piece in enumerate(board):
            if piece is None or piece.owner!=0 or types[piece.current_type_id].is_anchor:continue
            for atom in types[piece.current_type_id].movement_atoms:
                assert isinstance(atom,LeapAtom)
                x=index%n+atom.offset[0];y=index//n+atom.offset[1]
                if 0<=x<n and 0<=y<n:
                    victim=board[x+n*y]
                    if victim is None or victim.owner!=0:
                        possibilities[piece.current_type_id].add((index,x+n*y))
        r={"board":n,"case":row["case"],"layout":row["layout"],"fingerprint":row["fingerprint"],
           "root_record_bound":True,"retained_child_payloads":0,"complete_Core_frontier":False,
           "observed_error":row["error_type"]+": "+row["error"],
           "owner0_geometric_upper_by_type":{k:len(possibilities[k]) for k in ("A","B")},
           "owner0_ordinary_geometric_upper":sum(map(len,possibilities.values())),
           "ordinary_geometry_nonempty":bool(effective(n,[a.offset for a in types["A"].movement_atoms])
                                             or effective(n,[a.offset for a in types["B"].movement_atoms])),
           "legal_count":"UNKNOWN; positive bound is not observedlegal availability",
           "WDL":"UNKNOWN"}
        resultrows.append(r);groups[stable(row["typed_geometry_key"])].append(r)
    result={"at":datetime.now(timezone.utc).isoformat(),"rows":resultrows,
            "source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "input_sha256":hashlib.sha256(input_file.read_bytes()).hexdigest(),
            "scheduled_slots":36,"complete_bound_root_records":len(resultrows),
            "complete_measured_frontiers":0,"recorder_failure_slots":len(resultrows),
            "geometric_upper_zero":sum(r["owner0_ordinary_geometric_upper"]==0 for r in resultrows),
            "nonempty_type_geometry_but_zero_opening_upper":[r for r in resultrows
                if r["ordinary_geometry_nonempty"] and r["owner0_ordinary_geometric_upper"]==0],
            "movement_groups":len(groups),
            "same_movement_groups_with_different_setup_upper":sum(
                len({r["owner0_ordinary_geometric_upper"] for r in group})>1 for group in groups.values()),
            "no_measured_frontier_recovery":True,"new_Core_queries":0,
            "Player":0,"solver":0,"games":0,
            "population":"handdeclared structural developmentcontrols; not currentgamegenerator or heldoutstrengthdata"}
    write_json(output,result)
    print(stable({k:v for k,v in result.items() if k not in ("rows","nonempty_type_geometry_but_zero_opening_upper")}))
    print("nonempty geometry but upper0",[(r["board"],r["case"],r["layout"]) for r in result["nonempty_type_geometry_but_zero_opening_upper"]])
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser(__doc__);p.add_argument("--input",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True);a=p.parse_args();run(a.input,a.output)
