from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
if Path.cwd().resolve() != ROOT:
    raise RuntimeError(f"RUN_FROM_REPOSITORY_ROOT:{ROOT}")

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_from_dict, action_to_dict
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from scripts.research_record import record_value, write_record

HERE = Path(__file__).resolve().parent
BASE = ROOT / "docs/research/data/static_5x5_price_20261020"
PLAN = json.loads((HERE / "plan.json").read_text(encoding="utf-8"))
OUT = HERE / "result.json"
START = time.monotonic()
CAP = 150.0


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value) -> str:
    raw = json.dumps(record_value(value), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def saved_action(item):
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
        data = json.loads((ROOT / ".local_agent" / f"{name}.json").read_text(encoding="utf-8"))
        if data.get("stopped") or data.get("user_paused"):
            raise InterruptedError(f"EXPLICIT_{name.upper()}_STOP")


def checkpoint(compiled, board, hand, label):
    return LearnableMaterialCheckpoint(
        ruleset_fingerprint=compiled.ruleset_fingerprint,
        evaluation_profile_version=f"primary-raw-profile-scale-{label}",
        board_weights=board,
        hand_weights=hand,
        material_scale=256,
        value_scale=10.0,
        reference_median=1.0,
    )


def main():
    stop_check()
    plan_sha = sha(HERE / "plan.json")
    limits = SearchLimits(max_depth=4, max_nodes=4096, max_time_seconds=30.0,
                          quiescence_max_depth=0, quiescence_hard_max_depth=0)
    out = {
        "schema": PLAN["schema"], "status": "RUNNING", "plan_sha256": plan_sha,
        "conditions": PLAN["conditions"], "inputs": [], "roots": [],
        "started_monotonic": START,
    }
    write_record(OUT, out)
    for spec in PLAN["inputs"]:
        stop_check()
        rule_id = spec["rule_id"]
        subdir = BASE if rule_id == "521004" else BASE / "candidate96"
        profile_path = subdir / f"profile-{rule_id}.json"
        rule_path = subdir / f"rule-{rule_id}.json"
        roots_path = subdir / "roots.json"
        actual = {"profile_sha256": sha(profile_path), "rule_sha256": sha(rule_path),
                  "roots_manifest_sha256": sha(roots_path)}
        expected = {k: spec[k] for k in actual}
        assert actual == expected, (rule_id, actual, expected)
        roots = [r for r in json.loads(roots_path.read_text(encoding="utf-8"))
                 if r["root_id"] in spec["root_ids"]]
        assert [r["root_id"] for r in roots] == spec["root_ids"]
        rules = deserialize_ruleset(rule_path.read_text(encoding="utf-8"))
        compiled = compile_legacy_ruleset_for_semantic_execution(rules)
        native = compile_native_semantic_rules(compiled)
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        cfg = EvaluationConfig()
        current = {"board": {k: v / 1000.0 for k, v in profile["board"].items()},
                   "hand": {k: v / 1000.0 for k, v in profile["hand"].items()}}
        raw_board, raw_hand = {}, {}
        for piece in compiled.piece_types:
            tid = piece.type_id
            raw = float(profile["piece_profiles"][tid]["raw_capability_score"])
            raw_board[tid] = 0.0 if piece.is_anchor else raw
            raw_hand[tid] = 0.0 if piece.is_anchor else raw * cfg.hand_weight
        cps = {
            "saved_normalized_profile": checkpoint(compiled, current["board"], current["hand"], "normalized"),
            "raw_capability_scale": checkpoint(compiled, raw_board, raw_hand, "raw"),
        }
        profile_row = {"rule_id": rule_id, "ruleset_fingerprint": compiled.ruleset_fingerprint,
                       **actual, "normalized": current, "raw": {"board": raw_board, "hand": raw_hand},
                       "quantized": {name: {"board": cp.semantic_quantized_board(tuple(t.type_id for t in compiled.piece_types)),
                                             "hand": cp.semantic_quantized_hand(tuple(t.type_id for t in compiled.piece_types))}
                                     for name, cp in cps.items()},
                       "checkpoint_ids": {name: cp.checkpoint_id for name, cp in cps.items()}}
        out["inputs"].append(profile_row)
        write_record(OUT, out)
        for root in roots:
            stop_check()
            session = GameSession(compiled)
            for action in root["opening"]:
                session.submit(saved_action(action))
            root_hash = digest(session.state)
            assert root_hash == root["root_sha256"], (root["root_id"], root_hash, root["root_sha256"])
            before = (session.state, session.history, session.to_record(), session._search_witnesses)
            row = {"root_id": root["root_id"], "root_sha256": root_hash,
                   "opening_plies": len(root["opening"]), "arms": {}}
            out["roots"].append(row)
            write_record(OUT, out)
            for arm, cp in cps.items():
                stop_check()
                engine = SemanticSearchEngine(compiled, native, checkpoint=cp, tt_megabytes=0)
                result = engine.search(session, limits, root_window_pruning=False)
                assert before == (session.state, session.history, session.to_record(), session._search_witnesses)
                assert result.action is None or result.action in session.legal_actions()
                row["arms"][arm] = {"action": None if result.action is None else action_to_dict(result.action),
                                    "pv": [action_to_dict(a) for a in result.principal_variation],
                                    "score": result.score, "depth": result.completed_depth,
                                    "nodes": result.nodes, "qnodes": result.qnodes,
                                    "termination_reason": result.termination_reason,
                                    "checkpoint_id": cp.checkpoint_id}
                write_record(OUT, out)
            row["action_equal"] = row["arms"]["saved_normalized_profile"]["action"] == row["arms"]["raw_capability_scale"]["action"]
            row["pv_equal"] = row["arms"]["saved_normalized_profile"]["pv"] == row["arms"]["raw_capability_scale"]["pv"]
            write_record(OUT, out)
    out["comparison"] = {"root_count": len(out["roots"]),
                         "action_changes": sum(not r["action_equal"] for r in out["roots"]),
                         "pv_changes": sum(not r["pv_equal"] for r in out["roots"]),
                         "wall_seconds": time.monotonic() - START}
    out["status"] = "COMPLETE"
    write_record(OUT, out)
    print(json.dumps({"status": out["status"], "comparison": out["comparison"],
                      "roots": [{"id": r["root_id"], "action_equal": r["action_equal"],
                                 "pv_equal": r["pv_equal"],
                                 "depths": [r["arms"][a]["depth"] for a in ("saved_normalized_profile", "raw_capability_scale")],
                                 "nodes": [r["arms"][a]["nodes"] for a in ("saved_normalized_profile", "raw_capability_scale")]}
                                for r in out["roots"]]}, separators=(",", ":")))


if __name__ == "__main__":
    main()
