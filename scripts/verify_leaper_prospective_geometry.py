"""Independent arithmetic/data review of the prospective Leap research.

Consumes saved observations only. Does not run Core, Player, source capsules,
a solver, an evaluator or any closed query.
"""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
from copy import deepcopy
import argparse,gzip,hashlib,json

from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
from scripts.leaper_geometry_sampling_weights import analytic_histogram
from scripts.leaper_two_direction_components import analytic_scc
from tools.local_agent.common import write_json


def get(piece,name):
    return piece[name] if isinstance(piece,dict) else getattr(piece,name)


def normalized(piece):
    return None if piece is None else {name:get(piece,name) for name in
        ("owner","base_type_id","current_type_id","promoted")}


def static_arithmetic(rr,board,side,values,cfg):
    n=rr.board_size;types={t.type_id:t for t in rr.piece_types}
    assert not any(t.is_promotable for t in rr.piece_types)
    assert all(all(hasattr(a,"offset") for a in t.movement_atoms) for t in rr.piece_types)
    attacks=[set(),set()];anchors={}
    material=0
    for i,p in enumerate(board):
        if p is None:continue
        owner=get(p,"owner");tid=get(p,"current_type_id");sign=1 if owner==0 else -1
        material+=sign*values[tid]
        if types[tid].is_anchor:anchors[owner]=i
        for a in types[tid].movement_atoms:
            x=i%n+sign*a.offset[0];y=i//n+sign*a.offset[1]
            if 0<=x<n and 0<=y<n:attacks[owner].add(x+n*y)
    escapes=[]
    for owner in (0,1):
        i=anchors[owner];sign=1 if owner==0 else -1;targets=set()
        for a in types[get(board[i],"current_type_id")].movement_atoms:
            assert max(map(abs,a.offset))<=1
            x=i%n+sign*a.offset[0];y=i//n+sign*a.offset[1]
            if 0<=x<n and 0<=y<n:targets.add(x+n*y)
        escapes.append(sum(board[t] is None and t not in attacks[1-owner] for t in targets))
    score=material+cfg["dynamic_mobility_weight"]*(len(attacks[0])-len(attacks[1]))
    score+=cfg["anchor_escape_weight"]*(escapes[0]-escapes[1])
    score-=cfg["anchor_escape_weight"]*10*int(anchors[0] in attacks[1])
    score+=cfg["anchor_escape_weight"]*10*int(anchors[1] in attacks[0])
    return score if side==0 else -score


def check_evaluations(data,reference):
    assert len(data["rows"])==len(reference["rows"])==8
    count=0
    for row,ref in zip(data["rows"],reference["rows"]):
        rr=ruleset_from_dict(ref["ruleset"]);fp=compute_fingerprint(rr)
        assert row["record"]["ruleset_fingerprint"]==fp
        assert row["board_values"]=={"K":0,"A":1000,"B":1000}
        board=tuple(p for rank in rr.initial_position for p in rank)
        assert static_arithmetic(rr,board,0,row["board_values"],data["config"])==row["static_score_stm"]
        count+=1
        for c in row["children"]:
            state=c["child"];pos=state["position"];assert state["ply_count"]==1
            assert pos["side_to_move"]==1 and pos["ruleset_fingerprint"]==fp
            assert all(not h["counts"] for h in pos["hands"]) and len(state["history"])==2
            assert sum(x[1] for x in state["repetition_counts"])==2
            source,target=c["physical_action"]
            expected=list(map(normalized,board));mover=expected[source];expected[source]=None
            assert expected[target] is None # The frozen control is quiet-only.
            expected[target]=mover
            assert expected==pos["board"]
            calc=static_arithmetic(rr,pos["board"],1,row["board_values"],data["config"])
            assert calc==c["score_child_stm"] and -calc==c["score_parent_mover"]
            count+=1
    return count


def check_failed(rows,claim):
    assert len(rows)==36
    assert all("record" in r and r["record"]["actions"]==[] for r in rows)
    assert all(r.get("error_type")=="AttributeError" and "ply" in r.get("error","") for r in rows)
    assert not any("children" in r for r in rows)
    for r in rows:
        assert compute_fingerprint(ruleset_from_dict(r["RuleSet"]))==r["fingerprint"]==r["record"]["ruleset_fingerprint"]
    assert claim["complete_bound_root_records"]==36 and claim["complete_measured_frontiers"]==0
    assert claim["recorder_failure_slots"]==36 and claim["no_measured_frontier_recovery"] is True


def run(root,output):
    read=lambda name:json.loads((root/name).read_text(encoding="utf-8"))
    gz=lambda name:json.loads(gzip.decompress((root/name).read_bytes()))
    original=gz("census/rows.json.gz");corrected=gz("derived-corrected/rows-corrected.json.gz")
    assert sum(len(b["rows"]) for b in original)==21780
    formula=0;changed=0
    for before,after in zip(original,corrected):
        assert before["n"]==after["n"] and len(before["rows"])==len(after["rows"])==7260
        weights=Counter()
        for a,b in zip(before["rows"],after["rows"]):
            for field in ("raw","effective","spatial_key"):assert a[field]==b[field]
            assert tuple(b["descriptor"][3])==analytic_scc(before["n"],b["raw"])
            weights[json.dumps(b["spatial_key"],sort_keys=True)]+=1
            formula+=1;changed+=int(a["descriptor"]!=b["descriptor"])
        assert dict(Counter(weights.values()))==analytic_histogram(before["n"])
    failed=gz("literal-catalog/records.json.gz");claim=read("literal-catalog-source-analysis.json")
    check_failed(failed,claim)
    data=read("evaluator-component.json");reference=read("order-multiplicity.json")
    evals=check_evaluations(data,reference);assert evals==15
    positive=read("order-consumer.json");encoding=read("encoding-order-control.json")
    assert positive["frontier_set_parity"]==positive["ordered_parity"]==positive["first_ordered_parity"]==8
    assert reference["frontier_set_parity"]==reference["first_ordered_parity"]==8 and reference["ordered_parity"]==4
    assert encoding["same_physical_frontier"] and not encoding["physical_order_equal"] and not encoding["first_ordered_equal"]
    # Fresh in-memory negative reviews: no file mutation or new engine call.
    rejected=[]
    bad=deepcopy(data);bad["rows"][0]["children"][0]["score_child_stm"]*=-1
    try:check_evaluations(bad,reference)
    except AssertionError:rejected.append("child_score_perspective_flip")
    bad_claim=deepcopy(claim);bad_claim["complete_measured_frontiers"]=36
    try:check_failed(failed,bad_claim)
    except AssertionError:rejected.append("failed_slots_promoted_to_complete")
    try:check_failed(failed[:-1],claim)
    except AssertionError:rejected.append("drop_failed_slot")
    assert len(rejected)==3
    result={"at":datetime.now(timezone.utc).isoformat(),"status":"INDEPENDENT_SAVED_DATA_REVIEW_PASS",
            "same_raw_masks_verified":formula,"corrected_derived_descriptor_rows":changed,
            "analytic_SCC_matches":formula,"analytic_raw_class_histograms":3,
            "full_bound_failed_root_records":36,"complete_frontiers_recovered":0,
            "independent_DEFAULT_arithmetic_values":evals,"negative_claim_controls_rejected":rejected,
            "new_Core":0,"new_Evaluator":0,"new_Player":0,"new_solver":0,"new_games":0,
            "limitations":"Checks retained evidence consistency and restricted component arithmetic; not independent fullEngine/WDL/Player reproduction or strength proof"}
    write_json(output,result);print(json.dumps(result));return result


if __name__=="__main__":
    p=argparse.ArgumentParser(__doc__);p.add_argument("--data",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True);a=p.parse_args();run(a.data,a.output)
