from __future__ import annotations
import hashlib, json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
if Path.cwd().resolve() != ROOT:
    raise RuntimeError(f"RUN_FROM_REPOSITORY_ROOT:{ROOT}")
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import MAX_STATIC_EVAL, _median, build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_from_dict, action_to_dict
from generic_chess.generation.config import GeneratorConfig
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from scripts.research_record import record_value, write_record

HERE = Path(__file__).resolve().parent
DATA = ROOT / "docs/research/data/static_5x5_price_20261020"
PLAN = json.loads((HERE / "plan.json").read_text(encoding="utf-8"))
OUT = HERE / "result.json"
START = time.monotonic()
CAP = 150.0

def digest(v):
    b = json.dumps(record_value(v), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(b).hexdigest()

def opening_action(item):
    if "kind" in item:
        return action_from_dict(item)
    data = dict(item)
    target = data.pop("to_square")
    data["to"] = [target["file"], target["rank"]]
    if "from_square" in data:
        origin = data.pop("from_square")
        data["from"] = [origin["file"], origin["rank"]]
        data["kind"] = "semantic_board"
    elif "base_type_id" in data:
        data["kind"] = "semantic_drop"
    else:
        raise ValueError(f"UNRECOGNIZED_SAVED_ACTION:{item}")
    return action_from_dict(data)
def stop_check():
    if time.monotonic() - START >= CAP:
        raise TimeoutError("FIXED_GLOBAL_150S_CAP")
    for name in ("rollout", "advisor", "slack"):
        o = json.loads((ROOT / ".local_agent" / f"{name}.json").read_text(encoding="utf-8"))
        if o.get("stopped") or o.get("user_paused"):
            raise InterruptedError(f"EXPLICIT_{name.upper()}_STOP")

def values(compiled, profile, unique):
    pps = profile.piece_profiles
    ordinary = [pt for pt in compiled.piece_types if not pt.is_anchor]
    raw = {pt.type_id: float(pps[pt.type_id].raw_capability_score) for pt in ordinary}
    sample = raw
    if unique:
        representatives = {}
        for pt in ordinary:
            signature = pps[pt.type_id].movement_signature
            representatives.setdefault(signature, raw[pt.type_id])
        sample = {str(i): v for i, v in enumerate(representatives.values())}
    med = _median(list(sample.values())) if sample else 0.0
    cfg = EvaluationConfig()
    board, hand = {}, {}
    byid = {pt.type_id: pt for pt in compiled.piece_types}
    for pt in compiled.piece_types:
        t = pt.type_id
        if pt.is_anchor:
            board[t] = hand[t] = 0.0
        else:
            bv = 1 if med <= 0 else max(1, min(int(round(cfg.normal_piece_median_value * raw[t] / med)), MAX_STATIC_EVAL))
            hv = min(int(round(bv * cfg.hand_weight)), MAX_STATIC_EVAL)
            board[t] = bv / 1000.0
            hand[t] = hv / 1000.0
    return board, hand, med

def checkpoint(compiled, board, hand, label):
    return LearnableMaterialCheckpoint(
        ruleset_fingerprint=compiled.ruleset_fingerprint,
        evaluation_profile_version=f"primary-static-5x5-signature-median-{label}",
        board_weights=board,
        hand_weights=hand,
        material_scale=256,
        value_scale=10.0,
        reference_median=1.0,
    )

def main():
    stop_check()
    plan_sha = hashlib.sha256((HERE / "plan.json").read_bytes()).hexdigest()
    roots_path = DATA / "roots.json"
    roots_sha = hashlib.sha256(roots_path.read_bytes()).hexdigest()
    assert roots_sha == PLAN["inputs"]["roots_manifest_sha256"]
    roots = [r for r in json.loads(roots_path.read_text(encoding="utf-8")) if r["root_id"] in PLAN["inputs"]["root_ids"]]
    assert [r["root_id"] for r in roots] == PLAN["inputs"]["root_ids"]
    profile_path = DATA / "profile-521005.json"
    profile_sha = hashlib.sha256(profile_path.read_bytes()).hexdigest()
    assert profile_sha == PLAN["inputs"]["profile_sha256"]
    ruleset = deserialize_ruleset((DATA / "rule-521005.json").read_text(encoding="utf-8"))
    compiled = compile_legacy_ruleset_for_semantic_execution(ruleset)
    native = compile_native_semantic_rules(compiled)
    profile = build_ruleset_profile(compiled, EvaluationConfig())
    saved = json.loads(profile_path.read_text(encoding="utf-8"))
    assert profile.board_value_by_type == saved["board"]
    assert profile.hand_value_by_base_type == saved["hand"]
    normal = values(compiled, profile, False)
    unique = values(compiled, profile, True)
    checkpoints = {
        "current_all_type_median": checkpoint(compiled, normal[0], normal[1], "all-type"),
        "counterfactual_one_per_exact_signature": checkpoint(compiled, unique[0], unique[1], "unique-signature"),
    }
    assert round(normal[2], 9) == 3.023645996
    assert round(unique[2], 9) == 2.804477276
    limits = SearchLimits(max_depth=4, max_nodes=4096, max_time_seconds=30.0,
                          quiescence_max_depth=0, quiescence_hard_max_depth=0)
    out = {
        "schema": "primary-signature-median-choice-521005-v1",
        "status": "RUNNING",
        "plan_sha256": plan_sha,
        "inputs": {"profile_sha256": profile_sha, "roots_manifest_sha256": roots_sha},
        "rule_id": "521005",
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "normal_raw_median": normal[2],
        "unique_signature_raw_median": unique[2],
        "profiles": {},
        "roots": [],
        "started_monotonic": START,
    }
    for arm, (board, hand, med) in (
        ("current_all_type_median", normal),
        ("counterfactual_one_per_exact_signature", unique),
    ):
        out["profiles"][arm] = {"raw_median": med, "board": board, "hand": hand}
    write_record(OUT, out)
    for root in roots:
        stop_check()
        session = GameSession(compiled)
        for item in root["opening"]:
            session.submit(opening_action(item))
        root_hash = digest(session.state)
        assert root_hash == root["root_sha256"], (root["root_id"], root_hash, root["root_sha256"])
        before = (session.state, session.history, session.to_record(), session._search_witnesses)
        row = {"root_id": root["root_id"], "root_sha256": root_hash, "opening_plies": len(root["opening"]), "arms": {}}
        for arm, (board, hand, _) in (
            ("current_all_type_median", normal),
            ("counterfactual_one_per_exact_signature", unique),
        ):
            stop_check()
            cp = checkpoints[arm]
            engine = SemanticSearchEngine(compiled, native, checkpoint=cp, tt_megabytes=0)
            tick = time.perf_counter()
            result = engine.search(session, limits, root_window_pruning=False)
            elapsed = time.perf_counter() - tick
            assert before == (session.state, session.history, session.to_record(), session._search_witnesses)
            assert result.action is None or result.action in session.legal_actions()
            row["arms"][arm] = {
                "action": None if result.action is None else action_to_dict(result.action),
                "pv": [action_to_dict(a) for a in result.principal_variation],
                "score": result.score, "completed_depth": result.completed_depth,
                "nodes": result.nodes, "qnodes": result.qnodes,
                "termination_reason": result.termination_reason,
                "used_fallback": result.used_fallback,
                "tt_probes": result.tt_probes, "tt_hits": result.tt_hits,
                "checkpoint_id": cp.checkpoint_id,
                "quantized_board": cp.semantic_quantized_board(tuple(t.type_id for t in compiled.piece_types)),
                "quantized_hand": cp.semantic_quantized_hand(tuple(t.type_id for t in compiled.piece_types)),
                "elapsed_seconds": elapsed,
            }
            out["roots"].append(row) if arm == "counterfactual_one_per_exact_signature" else None
            out["status"] = "RUNNING"
            write_record(OUT, out)
        row["action_equal"] = row["arms"]["current_all_type_median"]["action"] == row["arms"]["counterfactual_one_per_exact_signature"]["action"]
        row["pv_equal"] = row["arms"]["current_all_type_median"]["pv"] == row["arms"]["counterfactual_one_per_exact_signature"]["pv"]
        row["nodes_equal"] = row["arms"]["current_all_type_median"]["nodes"] == row["arms"]["counterfactual_one_per_exact_signature"]["nodes"]
        row["depth_equal"] = row["arms"]["current_all_type_median"]["completed_depth"] == row["arms"]["counterfactual_one_per_exact_signature"]["completed_depth"]
        out["roots"][-1] = row
        write_record(OUT, out)
    comparisons = {
        "action_changes": sum(not r["action_equal"] for r in out["roots"]),
        "pv_changes": sum(not r["pv_equal"] for r in out["roots"]),
        "node_matches": sum(r["nodes_equal"] for r in out["roots"]),
        "depth_matches": sum(r["depth_equal"] for r in out["roots"]),
        "root_count": len(out["roots"]),
        "elapsed_wall_seconds": time.monotonic() - START,
    }
    out["comparison"] = comparisons
    out["status"] = "COMPLETE"
    write_record(OUT, out)
    print(json.dumps({"status": out["status"], "comparison": comparisons, "roots": [
        {"id": r["root_id"], "action_equal": r["action_equal"], "pv_equal": r["pv_equal"],
         "depth": [r["arms"]["current_all_type_median"]["completed_depth"], r["arms"]["counterfactual_one_per_exact_signature"]["completed_depth"]],
         "nodes": [r["arms"]["current_all_type_median"]["nodes"], r["arms"]["counterfactual_one_per_exact_signature"]["nodes"]]}
        for r in out["roots"]]}, separators=(",", ":")))

if __name__ == "__main__":
    main()
