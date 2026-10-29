"""Offline reader for the exhausted two-slot AUX metamorphic result.

Never imports/calls Player or reconstructs a new search result.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path

def encoded(v):
    return json.dumps(v,sort_keys=True,separators=(",",":")).encode()

def validate(frozen: bytes, result: dict, dispatch: dict):
    f=json.loads(frozen)
    h=hashlib.sha256(frozen).hexdigest()
    assert f["lifetime_Player_call_cap"]==2 and f["slots"]==["original","globally-renamed"]
    assert result["frozen_sha256"]==dispatch["frozen_sha256"]==h
    assert result["source"]==dispatch["source"]==f["source"]
    assert dispatch["status"]=="DISPATCHED_ONCE" and dispatch["slots"]==2
    assert result["status"]=="COMPLETE" and result["actual_Player_calls"]==2
    assert result["post_decision_PV_submit_calls"]==2
    assert len(result["calls"])==2
    pf=result["preflight"]
    assert pf["root_actions"]==17 and len(pf["argmax_rows"])==17
    assert pf["all_D1_values"]==[2000]*17
    assert pf["two_ply_prefixes"]==65 and pf["paired_edges"]==64
    assert pf["actual_Session_submit_calls"]==222
    old={encoded(r["action"]):r for r in pf["argmax_rows"]}
    new={encoded(r["mapped_action"]):r for r in pf["argmax_rows"]}
    assert len(old)==len(new)==17 and all(r["raw_root_view"]==2000 for r in old.values())
    for slot,call,domain in zip(f["slots"],result["calls"],(old,new)):
        assert call["slot"]==slot
        d=call["decision"]
        assert encoded(d["action"]) in domain
        assert d["score"]==2000 and d["result_source"]=="main_iteration"
        assert d["completed_depth"]==1 and d["result_ordinary_qdepth"]==0
        assert d["nodes"]==18 and d["qnodes"]==0 and d["evaluation_calls"]==17
        assert d["tt_probes"]==d["tt_hits"]==d["root_scan_nodes"]==d["native_legality_calls"]==0
        assert d["runtime_depth_balanced"] and d["runtime_pushes"]==d["runtime_pops"]==17
        assert d["principal_variation"]==[d["action"]]
        assert 0<=call["whole_compile_constructor_choose_pack_wall"]<=3
    a,b=[x["decision"]["action"]for x in result["calls"]]
    expected=old[encoded(a)]["mapped_action"]
    maps=encoded(expected)==encoded(b)
    assert result["expected_mapped_old_action"]==expected
    assert result["literal_selected_action_maps"] is maps
    assert result["whole_experiment_wall"]<=f["whole_experiment_seconds"]==120
    return {"actual_Player_calls":2,"literal_selected_action_maps":maps,
            "both_in_mapped_D1_argmax":True,"argmax_size":17,
            "quality_or_speed_gain_established":False,
            "legacy_remaining_slots_field":result.get("remaining_slots"),
            "legacy_remaining_slots_field_is_stale":result.get("remaining_slots")=="NOT_RUN"}
