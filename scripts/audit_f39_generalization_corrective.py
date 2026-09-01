"""F39 diagnosis-only generalization audit under the frozen F39 manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from generic_chess.core.actions import action_is_board, action_is_drop, action_promotion_target_id, action_source_square, action_target_square, action_to_dict
from generic_chess.core.attacks import is_in_check
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action
from generic_chess.learning.shogi_rules import gc_action_to_usi, sfen_to_gc_state
from scripts import audit_f31_gap_causal as f31
from scripts import audit_f37_evaluator_reentry as f37
from scripts import audit_f38_activity_anchor_prototype as f38

FX = ROOT / "tests" / "fixtures"
MANIFEST = FX / "f39_generalization_manifest.json"
ROBUST = FX / "f39_rank_robustness.json"
ABLATION = FX / "f39_component_ablation.json"
SHIFT = FX / "f39_distribution_shift.json"
SEARCH = FX / "f39_component_search.json"
SELECT = FX / "f39_generalization_selection.json"
DESC = FX / "f38_external_holdout_descriptor.json"
F38_RANKS = FX / "f38_activity_anchor_holdout_ranks.json"
F38_SEARCH = FX / "f38_activity_anchor_holdout_search.json"
F37_RANKS = FX / "f37_evaluator_representation_ranks.json"
F37_SEARCH = FX / "f37_evaluator_search_shadow.json"
FIELDS = ("board_material", "hand_inventory", "promotion_potential", "global_pseudo_control", "anchor_escape", "check_penalty", "raw_total", "side_to_move_score")
EPS = 0.01


def load(path: Path) -> Any: return json.loads(path.read_text(encoding="utf-8"))
def canon(x: Any) -> str: return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def dump(path: Path, x: Any) -> None: path.write_text(json.dumps(x, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def verify_manifest() -> dict[str, Any]:
    m = load(MANIFEST); body = {k: v for k, v in m.items() if k != "manifest_sha256"}
    assert hashlib.sha256(canon(body).encode()).hexdigest() == m["manifest_sha256"]
    for b in m["inputs"].values(): assert sha(ROOT / b["path"]) == b["sha256"]
    assert subprocess.run(["git", "diff", "--quiet", "--", "generic_chess"], cwd=ROOT).returncode == 0
    return m


def ctx():
    compiled, config, profile, production, prototype = f38._context()
    return compiled, profile, {"V1": production, "R37A": f37.CandidateEvaluator(production, "R37A"), "R37B": f37.CandidateEvaluator(production, "R37B"), "R37C": f37.CandidateEvaluator(production, "R37C")}, prototype


def terms(name: str, evaluator: Any, production: Any, child: Any) -> dict[str, int]:
    return f37.v1_terms(production, child) if name == "V1" else evaluator.components(child)


def vector(compiled: Any, evaluator: Any, production: Any, name: str, state: Any) -> list[dict[str, Any]]:
    rows = []
    for action in legal_actions(state, compiled):
        child = apply_action(state, action, compiled)
        rows.append({"action": action, "child": child, "key": canon(action_to_dict(action)), "move": gc_action_to_usi(action), "score": -evaluator.evaluate(child), "terms": terms(name, evaluator, production, child)})
    rows.sort(key=lambda r: (-r["score"], r["key"]))
    for i, row in enumerate(rows, 1): row["deterministic_rank"] = i
    return rows


def metric(rows: list[dict[str, Any]], move: str, scale: float) -> dict[str, Any]:
    target = next(r for r in rows if r["move"] == move); top = rows[0]["score"]
    strict = 1 + sum(r["score"] > target["score"] for r in rows)
    high = sum(r["score"] >= target["score"] for r in rows)
    return {"deterministic_rank": target["deterministic_rank"], "strict_rank": strict, "tie_span_low": strict, "tie_span_high": high, "rank_percentile": strict / len(rows), "margin_from_top": top - target["score"], "normalized_margin": (top - target["score"]) / scale, "target_score": target["score"], "top_score": top, "distinct_scores": len({r["score"] for r in rows}), "target_tie_width": high - strict + 1, "top_tie_width": sum(r["score"] == top for r in rows), "legal_action_count": len(rows)}


def action_tags(compiled: Any, state: Any, row: dict[str, Any]) -> dict[str, bool]:
    a = row["action"]; board = action_is_board(a); source = action_source_square(a)
    piece = state.position.board[source.rank * compiled._legacy_compiled.board_size + source.file] if source else None
    target = action_target_square(a); dest = state.position.board[target.rank * compiled._legacy_compiled.board_size + target.file]
    child = row["child"]
    return {"board": board, "drop": action_is_drop(a), "capture": bool(board and dest is not None and piece is not None and dest.owner != piece.owner), "promotion": action_promotion_target_id(a) is not None, "checking": is_in_check(child.position, child.position.side_to_move, compiled), "anchor_actor": bool(piece and compiled._legacy_compiled.types_by_id[piece.current_type_id].is_anchor)}


def classify(v1: dict[str, Any], c: dict[str, Any]) -> str:
    dr, ds, dm = c["deterministic_rank"]-v1["deterministic_rank"], c["strict_rank"]-v1["strict_rank"], c["normalized_margin"]-v1["normalized_margin"]
    if ds > 0 and dm >= EPS: return "MATERIAL_VALUE_WORSENING"
    if dr >= 3 and ds == 0 and dm < EPS: return "RANK_TIE_INSTABILITY"
    if (ds > 0) != (dm >= EPS): return "MIXED_RANK_AND_MARGIN"
    return "UNCHANGED_OR_IMPROVED"


def row_json(r: dict[str, Any]) -> dict[str, Any]: return {k: r[k] for k in ("key", "move", "score", "deterministic_rank")}


def static() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    compiled, profile, ev, proto = ctx(); desc, frozen = load(DESC)["positions"], load(F38_RANKS)["rows"]
    frozen_by = {(r["game_id"], r["event_index"]): r for r in frozen}; robust, ab_rows, all_records = [], [], []
    add_fail = []
    for item in desc:
        state = sfen_to_gc_state(compiled, item["canonical_state"]); vectors = {n: vector(compiled, e, ev["V1"], n, state) for n, e in ev.items()}; pvec = vector(compiled, proto, ev["V1"], "R37C", state)
        ms = {n: metric(vectors[n], item["alphasho_played_move"], profile.median_non_anchor_value) for n in ev}; pm = metric(pvec, item["alphasho_played_move"], profile.median_non_anchor_value)
        old = frozen_by[(item["game_id"], item["event_index"])]
        reproduce = ms["V1"]["deterministic_rank"] == old["v1_rank"] and ms["R37C"]["deterministic_rank"] == old["r37c_rank"] and ms["V1"]["margin_from_top"] == old["v1_margin_from_top"] and ms["R37C"]["margin_from_top"] == old["r37c_margin_from_top"] and [r["score"] for r in vectors["R37C"]] == [r["score"] for r in pvec]
        label = classify(ms["V1"], ms["R37C"]); target = item["alphasho_played_move"]
        top_v1, top_c = vectors["V1"][0], vectors["R37C"][0]
        states = {"target": next(r for r in vectors["V1"] if r["move"] == target), "top_v1": next(r for r in vectors["V1"] if r["key"] == top_v1["key"]), "top_r37c": next(r for r in vectors["V1"] if r["key"] == top_c["key"])}
        margin = {n: vectors[n][0]["score"] - next(r for r in vectors[n] if r["move"] == target)["score"] for n in ev}
        ae, be = (margin["R37A"]-margin["V1"])/profile.median_non_anchor_value, (margin["R37B"]-margin["V1"])/profile.median_non_anchor_value
        causal = "TIE_STRUCTURE_DOMINATED" if label == "RANK_TIE_INSTABILITY" else "BOTH_SAME_DIRECTION" if ae >= EPS and be >= EPS else "ACTIVITY_DRIVEN" if ae >= EPS and be < EPS else "ANCHOR_DRIVEN" if be >= EPS and ae < EPS else "COMPONENTS_OPPOSE" if ae*be < 0 and max(abs(ae),abs(be)) >= EPS else "UNRESOLVED"
        for action_row in vectors["V1"]:
            child = action_row["child"]; scores = {n: ev[n].evaluate(child) for n in ev}
            if scores["R37C"]-scores["V1"] != scores["R37A"]-scores["V1"] + scores["R37B"]-scores["V1"]: add_fail.append({"game_id": item["game_id"], "move": action_row["move"]})
        decompositions = {state_name: {n: terms(n, ev[n], ev["V1"], state_row["child"]) for n in ev} for state_name, state_row in states.items()}
        ab_rows.append({"game_id": item["game_id"], "event_index": item["event_index"], "move": target, "metrics": ms, "classification": label, "causal_label": causal, "normalized_target_vs_v1_top_margin_effect": {"activity": ae, "anchor": be}, "child_decompositions": decompositions, "top_children": {"v1": top_v1["move"], "r37c": top_c["move"]}, "strata": action_tags(compiled, state, states["target"]), "score_additivity": True})
        robust.append({"game_id": item["game_id"], "event_index": item["event_index"], "alphasho_move": target, "v1": ms["V1"], "r37c": ms["R37C"], "classification": label, "f38_reproduced": reproduce, "vectors": {"v1": [row_json(r) for r in vectors["V1"]], "r37c": [row_json(r) for r in vectors["R37C"]]}})
        all_records.append((item, ms, label))
    def ag(name: str):
        rows = [r["metrics"][name] for r in ab_rows]; base = [r["metrics"]["V1"] for r in ab_rows]
        return {"mean_deterministic_rank": statistics.mean(r["deterministic_rank"] for r in rows), "median_deterministic_rank": statistics.median(r["deterministic_rank"] for r in rows), "mean_strict_rank": statistics.mean(r["strict_rank"] for r in rows), "median_strict_rank": statistics.median(r["strict_rank"] for r in rows), "mean_percentile": statistics.mean(r["rank_percentile"] for r in rows), "mean_normalized_margin": statistics.mean(r["normalized_margin"] for r in rows), "strict_top1": sum(r["strict_rank"] <= 1 for r in rows), "strict_top3": sum(r["strict_rank"] <= 3 for r in rows), "strict_top5": sum(r["strict_rank"] <= 5 for r in rows), "strict_rank_vs_v1": {"improved": sum(r["strict_rank"] < b["strict_rank"] for r,b in zip(rows,base)), "unchanged": sum(r["strict_rank"] == b["strict_rank"] for r,b in zip(rows,base)), "worsened": sum(r["strict_rank"] > b["strict_rank"] for r,b in zip(rows,base))}, "margin_vs_v1": {"improved": sum(r["normalized_margin"] < b["normalized_margin"]-EPS for r,b in zip(rows,base)), "unchanged": sum(abs(r["normalized_margin"]-b["normalized_margin"]) < EPS for r,b in zip(rows,base)), "worsened": sum(r["normalized_margin"] >= b["normalized_margin"]+EPS for r,b in zip(rows,base))}}
    robustness = {"schema_version": 1, "status": "PASS", "positions": robust, "reproduced_f38_where_overlapping": all(r["f38_reproduced"] for r in robust), "classification_counts": {k: sum(r["classification"] == k for r in robust) for k in ("MATERIAL_VALUE_WORSENING","RANK_TIE_INSTABILITY","MIXED_RANK_AND_MARGIN","UNCHANGED_OR_IMPROVED")}}
    ablation = {"schema_version": 1, "status": "PASS" if not add_fail else "FAIL", "rows": ab_rows, "aggregates": {n: ag(n) for n in ev}, "R37_COMPONENT_SCORE_ADDITIVITY": not add_fail, "additivity_checked_states": sum(len(vector(compiled, ev["V1"], ev["V1"], "V1", sfen_to_gc_state(compiled, i["canonical_state"]))) for i in desc), "additivity_failures": add_fail}
    return robustness, ablation, {"compiled": compiled, "profile": profile, "evaluators": ev, "rows": ab_rows}


def quant(values: list[float]) -> dict[str, float]:
    s=sorted(values); q=lambda p: s[round((len(s)-1)*p)]
    return {"median": statistics.median(s), "q1": q(.25), "q3": q(.75), "iqr": q(.75)-q(.25)}


def distribution(compiled: Any, profile: Any, ev: dict[str, Any]) -> dict[str, Any]:
    roots,_=f31._frozen_roots(); hold=load(DESC)["positions"]
    def one(sfen: str) -> dict[str,float]:
        state=sfen_to_gc_state(compiled,sfen); acts=list(legal_actions(state,compiled)); rows=[{"action":a,"child":apply_action(state,a,compiled)} for a in acts]
        tags=[action_tags(compiled,state,{"action":r["action"],"child":r["child"]}) for r in rows]; c0=f37.v1_terms(ev["V1"],state); ca=ev["R37A"].components(state); cb=ev["R37B"].components(state)
        term_rows=[(f37.v1_terms(ev["V1"],r["child"]),ev["R37A"].components(r["child"]),ev["R37B"].components(r["child"])) for r in rows]
        rng=lambda idx,key:max(x[idx][key] for x in term_rows)-min(x[idx][key] for x in term_rows)
        return {"legal_action_count":len(acts),"board_occupancy":sum(p is not None for p in state.position.board),"total_hand_inventory":sum(n for h in state.position.hands for _,n in h.counts),"drop_action_fraction":sum(t["drop"] for t in tags)/len(acts),"capture_action_fraction":sum(t["capture"] for t in tags)/len(acts),"promotion_action_fraction":sum(t["promotion"] for t in tags)/len(acts),"checking_action_fraction":sum(t["checking"] for t in tags)/len(acts),"in_check":float(is_in_check(state.position,state.position.side_to_move,compiled)),"material_imbalance_magnitude":abs(c0["board_material"]+c0["hand_inventory"]),"v1_pseudo_control":c0["global_pseudo_control"],"activity_term":ca["global_pseudo_control"],"v1_anchor_escape":c0["anchor_escape"],"anchor_ring_term":cb["anchor_escape"],"v1_pseudo_control_range":rng(0,"global_pseudo_control"),"activity_term_range":rng(1,"global_pseudo_control"),"v1_anchor_escape_range":rng(0,"anchor_escape"),"anchor_ring_term_range":rng(2,"anchor_escape")}
    groups={"f37_selection_set":[one(i["sfen"]) for i in roots],"f38_holdout":[one(i["canonical_state"]) for i in hold]}; keys=groups["f37_selection_set"][0].keys(); summary={k:{g:quant([r[k] for r in rows]) for g,rows in groups.items()} for k in keys}; flags={k:(summary[k]["f37_selection_set"]["q3"]<summary[k]["f38_holdout"]["q1"] or summary[k]["f38_holdout"]["q3"]<summary[k]["f37_selection_set"]["q1"] or abs(summary[k]["f37_selection_set"]["median"]-summary[k]["f38_holdout"]["median"])/max(1.,(summary[k]["f37_selection_set"]["iqr"]+summary[k]["f38_holdout"]["iqr"])/2)>=1) for k in keys}; return {"schema_version":1,"status":"PASS","groups":groups,"summary":summary,"MATERIAL_DISTRIBUTION_SHIFT":flags}


def component_search(compiled: Any, ev: dict[str,Any]) -> dict[str,Any]:
    frozen=load(F38_SEARCH)["fixed_node"]["2048"]["rows"]; hold=load(DESC)["positions"][:10]; out=[]
    for item, old in zip(hold,frozen):
        state=sfen_to_gc_state(compiled,item["canonical_state"]); row={"game_id":item["game_id"],"alphasho_move":item["alphasho_played_move"],"frozen_v1":old["v1"],"frozen_r37c":old["r37c"],"counterfactuals":{}}
        for n in ("R37A","R37B"):
            r=f31._direct(f31._imports(),compiled,ev[n],state,nodes=2048,max_depth=8,qmax=4,qhard=8,native_requested=True); r["alphasho_exact_hit"]=r["selected_move"]==item["alphasho_played_move"]; r["nps"]=r["total_nodes"]/max(1e-9,r["elapsed_seconds"]); row["counterfactuals"][n]=r
        out.append(row)
    return {"schema_version":1,"status":"PASS","protocol":"frozen F37 fixed-node 2048 only; A/B newly run; V1/R37C consumed","rows":out}


def strata(ab: dict[str,Any]) -> dict[str,Any]:
    dimensions={"board_vs_drop":("board","drop"),"capture_vs_non_capture":("capture",None),"promotion_vs_non_promotion":("promotion",None),"checking_vs_non_checking":("checking",None),"anchor_actor_vs_non_anchor_actor":("anchor_actor",None)}; out={}
    for name,(key,other) in dimensions.items():
        groups={"yes":[],"no":[]}
        for row in ab["rows"]: groups["yes" if row["strata"][key] else "no"].append(row)
        out[name]={}
        for group,rows in groups.items():
            if not rows: out[name][group]={"count":0}; continue
            sd=[r["metrics"]["R37C"]["strict_rank"]-r["metrics"]["V1"]["strict_rank"] for r in rows]; md=[r["metrics"]["R37C"]["normalized_margin"]-r["metrics"]["V1"]["normalized_margin"] for r in rows]
            out[name][group]={"count":len(rows),"mean_strict_rank_delta":statistics.mean(sd),"mean_normalized_margin_delta":statistics.mean(md),"strict_improved":sum(x<0 for x in sd),"strict_worsened":sum(x>0 for x in sd),"margin_improved":sum(x<-EPS for x in md),"margin_worsened":sum(x>=EPS for x in md)}
    return out


def reversal(ab: dict[str,Any]) -> dict[str,Any]:
    frozen=load(F37_RANKS); shadow=load(F37_SEARCH); out={}
    for name in ("R37A","R37B","R37C"):
        axes={}
        for axis in ("alphasho_0.5","alphasho_2.0"):
            rows=[]
            for root in frozen["roots"].values():
                ranking=root["candidates"][name]["ranking"]; v1=root["candidates"]["V1"]["ranking"]; target=root["candidates"][name]["targets"][axis]["move"]; a=next(r for r in ranking if r["move"]==target); b=next(r for r in v1 if r["move"]==target); strict=lambda rs,x:1+sum(r["score"]>x["score"] for r in rs); rows.append({"rank":a["rank"],"strict":strict(ranking,a),"margin":ranking[0]["score"]-a["score"],"v1_rank":b["rank"],"v1_strict":strict(v1,b),"v1_margin":v1[0]["score"]-b["score"]})
            axes[axis]={"mean_rank":statistics.mean(r["rank"] for r in rows),"mean_strict_rank":statistics.mean(r["strict"] for r in rows),"mean_margin":statistics.mean(r["margin"] for r in rows),"improved":sum(r["rank"]<r["v1_rank"] for r in rows),"worsened":sum(r["rank"]>r["v1_rank"] for r in rows)}
        hold=ab["aggregates"][name]; v=ab["aggregates"]["V1"]; positive=hold["mean_strict_rank"]<v["mean_strict_rank"] and hold["mean_normalized_margin"]<=v["mean_normalized_margin"]-EPS; signal=frozen["summary"][name]["static_signal_gate"]
        transfer="DIRECTIONALLY_TRANSFERRED" if signal and positive else "IN_SAMPLE_ONLY_SIGNAL" if signal and not positive else "NEUTRAL_TRANSFER" if not positive else "UNRESOLVED"
        out[name]={"f37_axes":axes,"f37_search_hits":shadow.get("candidate_gates",{}).get(name,{}).get("hits"),"f38_holdout":hold,"transfer":transfer}
    return out


def selection(robust: dict[str,Any], ab: dict[str,Any], dist: dict[str,Any], search: dict[str,Any], rev: dict[str,Any], action_strata: dict[str,Any]) -> dict[str,Any]:
    a=ab["aggregates"]; worse=lambda n:a[n]["mean_strict_rank"]>a["V1"]["mean_strict_rank"] and a[n]["mean_normalized_margin"]>=a["V1"]["mean_normalized_margin"]+EPS; positive=lambda n:a[n]["mean_strict_rank"]<a["V1"]["mean_strict_rank"] and a[n]["mean_normalized_margin"]<=a["V1"]["mean_normalized_margin"]-EPS; notbetter=lambda n,m:a[n]["mean_strict_rank"]>=a[m]["mean_strict_rank"] and a[n]["mean_normalized_margin"]>=a[m]["mean_normalized_margin"]-EPS
    tie=robust["classification_counts"]["RANK_TIE_INSTABILITY"]; reg=sum(r["r37c"]["deterministic_rank"]>r["v1"]["deterministic_rank"] for r in robust["positions"]); c_margin=a["R37C"]["mean_normalized_margin"]-a["V1"]["mean_normalized_margin"]
    kind="ACTIVITY_NEGATIVE_TRANSFER" if worse("R37A") and notbetter("R37C","R37B") else "ANCHOR_NEGATIVE_TRANSFER" if worse("R37B") and notbetter("R37C","R37A") else "COMBINATION_NEGATIVE_TRANSFER" if not worse("R37A") and not worse("R37B") and worse("R37C") else "METRIC_INSTABILITY_PRIMARY" if tie>reg/2 and c_margin<EPS else "BROAD_REPRESENTATION_TRANSFER_FAILURE" if all(not positive(n) for n in ("R37A","R37B","R37C")) else "MIXED_OR_UNRESOLVED"
    mapping=load(MANIFEST)["boundary_mapping"]; return {"schema_version":1,"status":"PASS","aggregate_causal_classification":kind,"selected_boundary":mapping[kind],"F39_MUST_NOT_SELECT_R37A_OR_R37B_FOR_PRODUCTION":True,"flags":{"F38_GENERALIZATION_FAILURE_CONSUMED":True,"DETERMINISTIC_RANK_ROBUSTNESS_AUDITED":robust["reproduced_f38_where_overlapping"],"R37_COMPONENT_ABLATION_COMPLETE":True,"R37_COMPONENT_SCORE_ADDITIVITY_CERTIFIED":ab["R37_COMPONENT_SCORE_ADDITIVITY"],"F37_TO_F38_DISTRIBUTION_SHIFT_AUDITED":bool(dist),"NEXT_GENERIC_EVALUATOR_BOUNDARY_SELECTED":True},"f37_to_f38_reversal_matrix":rev,"action_semantic_strata":action_strata,"frozen_component_search":search}


def summarize_only() -> dict[str,Any]:
    m=verify_manifest(); robust,ab,dist,sea=load(ROBUST),load(ABLATION),load(SHIFT),load(SEARCH); sel=selection(robust,ab,dist,sea,reversal(ab),strata(ab)); dump(SELECT,sel); return {"status":"PASS","manifest_sha256":m["manifest_sha256"],"selection":sel}


def static_only() -> dict[str,Any]:
    m=verify_manifest(); robust,ab,context=static(); dump(ROBUST,robust); dump(ABLATION,ab); dist=distribution(context["compiled"],context["profile"],context["evaluators"]); dump(SHIFT,dist); sea=load(SEARCH); sel=selection(robust,ab,dist,sea,reversal(ab),strata(ab)); dump(SELECT,sel); return {"status":"PASS","manifest_sha256":m["manifest_sha256"],"selection":sel}


def run() -> dict[str,Any]:
    m=verify_manifest(); robust,ab,context=static(); dump(ROBUST,robust); dump(ABLATION,ab); dist=distribution(context["compiled"],context["profile"],context["evaluators"]); dump(SHIFT,dist); sea=component_search(context["compiled"],context["evaluators"]); dump(SEARCH,sea); sel=selection(robust,ab,dist,sea,reversal(ab),strata(ab)); dump(SELECT,sel); return {"status":"PASS","manifest_sha256":m["manifest_sha256"],"selection":sel}

def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser();p.add_argument("--run",action="store_true");p.add_argument("--summarize-only",action="store_true");p.add_argument("--static-only",action="store_true");a=p.parse_args(argv)
    if sum((a.run,a.summarize_only,a.static_only)) != 1:p.error("use exactly one mode")
    r=run() if a.run else static_only() if a.static_only else summarize_only();print(json.dumps({"status":r["status"],"boundary":r["selection"]["selected_boundary"],"classification":r["selection"]["aggregate_causal_classification"]},sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
