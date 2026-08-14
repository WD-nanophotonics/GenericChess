"""F20 H20A audit of the existing Native guarded-action path.

This harness is diagnostic only.  It never changes SearchPathRuntime or
AlphaBeta routing.  The extension is loaded from F20_NATIVE_EXTENSION so the
checkout's stale ABI artifact is not used.
"""

from __future__ import annotations

import importlib.util
import json
import os
import platform
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "f20_native_legality_kernel"
EXTENSION = Path(os.environ["F20_NATIVE_EXTENSION"])
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

spec = importlib.util.spec_from_file_location("generic_chess._native_core", EXTENSION)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load {EXTENSION}")
module = importlib.util.module_from_spec(spec)
sys.modules["generic_chess._native_core"] = module
spec.loader.exec_module(module)

from generic_chess.core.semantic_executor import _semantic_public_action, semantic_engine_for  # noqa: E402
from generic_chess.native.compiler import compile_native_semantic_rules  # noqa: E402
from generic_chess.native.mirror import _position_payload, pack_semantic_action  # noqa: E402
from generic_chess.native.semantic import (  # noqa: E402
    guarded_actions_audit,
    pack_position,
)
from scripts.audit_f4_runtime_cost import corpus_specs, make_session  # noqa: E402

FINGERPRINT = "5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345"


def write_json(name: str, value) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def native_state(session, native):
    return pack_position(native, _position_payload(session.compiled, native, session.state))


def python_packed_actions(session, native):
    engine = semantic_engine_for(session.compiled)
    rows = tuple(engine.iter_legal_action_bindings(session.state.position))
    public = tuple(_semantic_public_action(engine, action) for action, _binding in rows)
    return tuple(pack_semantic_action(native, session.state.position, action) for action in public), rows


def path_sessions(base_spec, max_depth=2, branch_limit=4):
    base = make_session(base_spec)
    out = [((), base)]

    def walk(prefix, session, depth):
        if depth >= max_depth:
            return
        actions = session.legal_actions()
        for action in actions[:branch_limit]:
            next_prefix = prefix + (str(action),)
            child = make_session(base_spec)
            for text in next_prefix:
                chosen = next(item for item in child.legal_actions() if str(item) == text)
                child.submit(chosen)
            out.append((next_prefix, child))
            walk(next_prefix, child, depth + 1)

    walk((), base, 0)
    return out


def timed(fn, repetitions=80):
    for _ in range(20):
        fn()
    samples = []
    for _ in range(5):
        started = time.perf_counter()
        for _ in range(repetitions):
            fn()
        samples.append((time.perf_counter() - started) * 1_000_000 / repetitions)
    return {
        "repetitions": repetitions,
        "median_us": statistics.median(samples),
        "p90_us": max(samples),
        "samples_us": samples,
    }


def main() -> None:
    semantic_specs = [row for row in corpus_specs() if row["kind"] == "semantic"]
    rows = []
    timing_rows = []
    totals = {
        "candidate_count": 0,
        "s3_trial_count": 0,
        "s4_count": 0,
        "nested_reply_count": 0,
        "child_canonical_key_computations": 0,
        "history_appends": 0,
        "attack_check_calls": 0,
    }
    for spec_row in semantic_specs:
        for prefix, session in path_sessions(spec_row):
            compiled = session.compiled
            if compiled.ruleset_fingerprint != FINGERPRINT:
                raise RuntimeError("RULESET_FINGERPRINT_MISMATCH")
            native = compile_native_semantic_rules(compiled)
            position = native_state(session, native)
            expected, py_rows = python_packed_actions(session, native)
            audit = guarded_actions_audit(native, position)
            actual = tuple(audit["actions"])
            mismatch = {
                "count": int(len(actual) != len(expected)),
                "order": int(actual != expected),
                "first_difference": next(
                    (i for i, pair in enumerate(zip(actual, expected)) if pair[0] != pair[1]),
                    None,
                ),
            }
            row = {
                "case_id": spec_row["id"],
                "prefix": list(prefix),
                "ply": int(session.state.ply_count),
                "python_legal_count": len(expected),
                "native_guarded_count": len(actual),
                "canonical_order_mismatch": mismatch,
                "counters": {key: int(audit[key]) for key in audit if key != "actions"},
            }
            rows.append(row)
            for key in totals:
                totals[key] += int(audit[key])
            if not prefix:
                timing_rows.append({
                    "case_id": spec_row["id"],
                    "python_packed_actions": expected,
                    "native_guarded_actions": actual,
                    "native_guarded_actions_audit": timed(lambda: guarded_actions_audit(native, position)),
                })

    all_order_mismatches = sum(row["canonical_order_mismatch"]["order"] for row in rows)
    all_count_mismatches = sum(row["canonical_order_mismatch"]["count"] for row in rows)
    write_json("baseline.json", {
        "status": "PASS",
        "baseline": {
            "origin/sandbox": "f2992ce07272a0b8ccee87ddf7a5595e67e1f8ed",
            "origin/master": "4f1d03a308f5fd04a01bbd980c7411888ea1ed9d",
            "origin/chat": "d6b0d5720efe23019a7a2b4cce72e05beee2e6c4",
        },
        "fingerprint": FINGERPRINT,
        "extension": str(EXTENSION),
    })
    write_json("environment.json", {
        "python": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "extension_bytes": EXTENSION.stat().st_size,
        "harness": "scripts/audit_f20_h20a.py",
    })
    write_json("python_legality_authority.json", {
        "authority": "SemanticEngine.iter_legal_action_bindings",
        "public_projection": "_semantic_public_action",
        "binding_bridge": "SemanticEngine._make_binding_from_action",
        "production_routing_changed": False,
        "status": "FROZEN",
    })
    write_json("native_guarded_baseline.json", {
        "api": "generic_chess.native.semantic.guarded_actions",
        "audit_api": "generic_chess.native.semantic.guarded_actions_audit",
        "rows": rows,
        "summary": {
            "rows": len(rows),
            "count_mismatches": all_count_mismatches,
            "order_mismatches": all_order_mismatches,
            "totals": totals,
            "child_key_history_work_observed": totals["child_canonical_key_computations"] > 0 and totals["history_appends"] > 0,
        },
        "status": "PASS" if not all_count_mismatches and not all_order_mismatches else "FAIL",
    })
    write_json("child_key_history_counters.json", {
        "implementation": "current exact-history guarded_actions",
        "totals": totals,
        "candidate_child_canonical_key_computations": totals["child_canonical_key_computations"],
        "candidate_child_history_appends": totals["history_appends"],
        "nested_reply_child_canonical_key_computations": "included in candidate_child_canonical_key_computations",
        "status": "BASELINE_LEAK_CONFIRMED" if totals["child_canonical_key_computations"] else "NO_LEAK_OBSERVED",
    })
    write_json("transient_legality_design.json", {
        "status": "H20A_CANDIDATE_PENDING",
        "family": "TRANSIENT S0-S4 LEGALITY KERNEL",
        "required_change": "reuse runtime transition with TRANSIENT_NONE history policy and return ordered packed legal actions only",
        "forbidden": ["child external canonical SHA", "history append", "terminal authority", "transient capsule escape"],
    })
    write_json("standard_shogi_legality_rows.jsonl", rows)
    (OUT / "standard_shogi_legality_rows.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
    )
    write_json("standard_shogi_legality_summary.json", {
        "rows": len(rows),
        "count_mismatches": all_count_mismatches,
        "order_mismatches": all_order_mismatches,
        "status": "PASS" if not all_count_mismatches and not all_order_mismatches else "FAIL",
    })
    write_json("packed_native_baseline_microbench.json", timing_rows)
    print(json.dumps({"rows": len(rows), "count_mismatches": all_count_mismatches, "order_mismatches": all_order_mismatches, "totals": totals}, sort_keys=True))


if __name__ == "__main__":
    main()
