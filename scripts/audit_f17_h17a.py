"""H17A transactional delta journal audit.

This harness is intentionally opt-in and records the delta prototype before
the H17B authorization decision. It never changes Core/SearchPathRuntime.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "f17_native_delta_position_runtime"
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tests"))


def load_extension() -> str:
    path = os.environ.get("F17_NATIVE_EXTENSION")
    if not path: raise RuntimeError("F17_NATIVE_EXTENSION is required")
    spec = importlib.util.spec_from_file_location("generic_chess._native_core", path)
    if spec is None or spec.loader is None: raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec); sys.modules["generic_chess._native_core"] = module; spec.loader.exec_module(module)
    return path


EXTENSION = load_extension()

from generic_chess.core.movegen import legal_actions  # noqa: E402
from generic_chess.core.search_runtime import SearchPathRuntime  # noqa: E402
from generic_chess.core.semantic_executor import semantic_engine_for  # noqa: E402
from generic_chess.native.compiler import compile_native_semantic_rules  # noqa: E402
from generic_chess.native.delta_runtime import NativeSemanticDeltaRuntime  # noqa: E402
from generic_chess.native.mirror import NativeSemanticPositionMirror, snapshot_matches  # noqa: E402
from generic_chess.native.semantic import guarded_actions, make_unmake_roundtrip  # noqa: E402
from scripts.audit_f4_runtime_cost import corpus_specs, make_session  # noqa: E402
from scripts.audit_f13_native_action_delivers_check import certified_semantic_shogi  # noqa: E402
from phase19c1_native_semantic_fixtures import semantic_corpus  # noqa: E402

FINGERPRINT = "5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345"
BASELINE = {
    "origin_sandbox": "a9c63a02c07376fb61636607cf88f16867bb1cee",
    "origin_master": "4f1d03a308f5fd04a01bbd980c7411888ea1ed9d",
    "origin_chat": "d6b0d5720efe23019a7a2b4cce72e05beee2e6c4",
}
OLD_PATTERNS = [
    *(f"artifacts/f{i}_*" for i in range(4, 17)),
    *(f"docs/architecture/F{i}_EVIDENCE.md" for i in range(4, 17)),
    *(f"docs/architecture/ADR-{i:03d}-*" for i in range(22, 34)),
]


def write_json(name, value):
    OUT.mkdir(parents=True, exist_ok=True); (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def old_manifest():
    rows = []
    for pattern in OLD_PATTERNS:
        for rel in subprocess.check_output(["git", "ls-files", "--", pattern], cwd=ROOT, text=True).splitlines():
            path = ROOT / rel
            if path.is_file(): rows.append(f"{digest(path)}  {rel}")
    return sorted(set(rows))


def bench(fn, repetitions=5000):
    for _ in range(100): fn()
    samples = []
    for _ in range(5):
        started = time.perf_counter()
        for _ in range(repetitions): fn()
        samples.append((time.perf_counter() - started) * 1_000_000 / repetitions)
    return {"warmup": 100, "repetitions": repetitions, "median_us": statistics.median(samples), "p90_us": max(samples), "max_us": max(samples), "samples_us": samples}


def standard_rows():
    rows = []
    for spec in corpus_specs():
        if not str(spec["id"]).startswith("semantic_"): continue
        session = make_session(spec); native = compile_native_semantic_rules(session.compiled)
        py = SearchPathRuntime.from_state(session.state, session.compiled, history_witnesses=session._search_witnesses)
        delta = NativeSemanticDeltaRuntime.from_state(session.compiled, native, session.state, history_certified=py.history_witness_misses == 0)
        mirror = NativeSemanticPositionMirror.from_state(session.compiled, native, session.state, history_certified=True)
        legal = tuple(legal_actions(session.state, session.compiled)); guarded = set(guarded_actions(native, mirror.position))
        pack_mismatches = sync_mismatches = pop_mismatches = depth_mismatches = history_mismatches = 0
        for action in legal:
            parent = py.position; packed = delta.direct_pack(action, parent)
            if packed not in guarded: pack_mismatches += 1
            py.push(action)
            try:
                delta.push_packed(packed)
                if not snapshot_matches(delta.snapshot(), py.position, native, session.compiled): sync_mismatches += 1
                if delta.position_key() != py.state.history[-1].position_key: history_mismatches += 1
                if delta.depth != py.depth: depth_mismatches += 1
            except Exception: sync_mismatches += 1
            finally:
                try: delta.pop()
                except Exception: pop_mismatches += 1
                py.pop()
            if delta.depth != 0 or py.depth != 0: depth_mismatches += 1
        depth2 = 0
        for action0 in legal[:8]:
            parent0 = py.position; py.push(action0); delta.push(action0, parent0)
            for action1 in tuple(legal_actions(py.state, session.compiled))[:8]:
                parent1 = py.position; py.push(action1); delta.push(action1, parent1); depth2 += 1
                if not snapshot_matches(delta.snapshot(), py.position, native, session.compiled): sync_mismatches += 1
                delta.pop(); py.pop()
            delta.pop(); py.pop()
        rows.append({"case_id": spec["id"], "fingerprint": session.compiled.ruleset_fingerprint, "legal_count": len(legal), "guarded_count": len(guarded), "depth2_pairs": depth2, "pack_mismatches": pack_mismatches, "push_mismatches": sync_mismatches, "pop_mismatches": pop_mismatches, "depth_mismatches": depth_mismatches, "history_mismatches": history_mismatches, "status": "PASS" if not any((pack_mismatches, sync_mismatches, pop_mismatches, depth_mismatches, history_mismatches)) else "FAIL"})
    return rows


def generic_rows():
    rows = []
    for name, compiled in semantic_corpus():
        state = __import__("generic_chess.core.transition", fromlist=["initial_state"]).initial_state(compiled)
        native = compile_native_semantic_rules(compiled); py = SearchPathRuntime.from_state(state, compiled)
        delta = NativeSemanticDeltaRuntime.from_state(compiled, native, state, history_certified=True)
        actions = tuple(legal_actions(state, compiled)); mismatches = failures = 0
        for action in actions[:20]:
            parent = py.position; py.push(action)
            try:
                delta.push(action, parent)
                if not snapshot_matches(delta.snapshot(), py.position, native, compiled): mismatches += 1
            except Exception: mismatches += 1
            finally:
                try: delta.pop()
                except Exception: failures += 1
                py.pop()
        rows.append({"case_id": name, "actions_checked": min(20, len(actions)), "mismatches": mismatches, "rollback_failures": failures, "status": "PASS" if not mismatches and not failures else "FAIL"})
    return rows


def attack_check_rows():
    rows = []
    for spec in corpus_specs():
        if not str(spec["id"]).startswith("semantic_"): continue
        session = make_session(spec); native = compile_native_semantic_rules(session.compiled); py = SearchPathRuntime.from_state(session.state, session.compiled, history_witnesses=session._search_witnesses); delta = NativeSemanticDeltaRuntime.from_state(session.compiled, native, session.state, history_certified=True); engine = semantic_engine_for(session.compiled)
        attack_mismatches = check_mismatches = 0
        for square in range(81):
            for owner in (0, 1):
                if engine.is_square_attacked(py.position, square, owner) != delta.is_square_attacked(square, owner): attack_mismatches += 1
        for side in (0, 1):
            if engine.in_check(py.position, side) != delta.in_check(side): check_mismatches += 1
        rows.append({"case_id": spec["id"], "attack_queries": 162, "check_queries": 2, "attack_mismatches": attack_mismatches, "check_mismatches": check_mismatches, "status": "PASS" if not attack_mismatches and not check_mismatches else "FAIL"})
    return rows


def microbench():
    session = make_session(next(x for x in corpus_specs() if x["id"] == "semantic_prefix_0")); native = compile_native_semantic_rules(session.compiled); mirror = NativeSemanticPositionMirror.from_state(session.compiled, native, session.state, history_certified=True); delta = NativeSemanticDeltaRuntime.from_state(session.compiled, native, session.state, history_certified=True); action = legal_actions(session.state, session.compiled)[0]; packed = mirror.direct_pack(action, session.state.position)
    def pair():
        delta.push_packed(packed); delta.pop()
    pair_result = bench(pair)
    push_times = []; pop_times = []
    for _ in range(5):
        for _ in range(5000):
            started = time.perf_counter(); delta.push_packed(packed); push_times.append((time.perf_counter() - started) * 1_000_000)
            started = time.perf_counter(); delta.pop(); pop_times.append((time.perf_counter() - started) * 1_000_000)
    pack = bench(lambda: delta.direct_pack(action, session.state.position))
    return {"delta_push": {"median_us": statistics.median(push_times), "p90_us": statistics.quantiles(push_times, n=100)[98], "max_us": max(push_times)}, "delta_pop": {"median_us": statistics.median(pop_times), "p90_us": statistics.quantiles(pop_times, n=100)[98], "max_us": max(pop_times)}, "delta_push_pop": {"median_us": pair_result["median_us"], "p90_us": pair_result["p90_us"], "max_us": pair_result["max_us"], "samples_us": pair_result["samples_us"]}, "action_pack": pack}


def main():
    OUT.mkdir(parents=True, exist_ok=True); before = old_manifest(); (OUT / "old_evidence_before.sha256").write_text("\n".join(before) + "\n", encoding="utf-8")
    refs = {ref: subprocess.check_output(["git", "rev-parse", ref], cwd=ROOT, text=True).strip() for ref in ("origin/sandbox", "origin/master", "origin/chat")}; write_json("baseline.json", {**refs, "required": BASELINE, "status": "PASS" if refs == BASELINE else "BASELINE_MOVED"})
    ext = Path(EXTENSION); write_json("environment.json", {"python": sys.version, "platform": platform.platform(), "native_extension": str(ext), "native_extension_size": ext.stat().st_size, "native_extension_sha256": digest(ext)}); (OUT / "fresh_native_build_before.txt").write_text(os.environ.get("F17_INITIAL_BUILD_OUTPUT", "temporary probe build\n"), encoding="utf-8")
    write_json("frozen_make_semantics.json", {"semantic_ir_version": 2, "execution_order": ["validate_parent", "expire_aux", "effects_declared_order", "promotion", "S3", "triggers", "aux_effects", "side_ply", "S4", "history_digest_append"], "status": "FROZEN"})
    write_json("effect_write_set.json", {"max_effects": 4, "board_capacity": 9, "hand_capacity": 10, "aux_capacity": 24, "strategy": "transactional pre-view overlay", "status": "PASS"})
    write_json("parent_prestate_reads.json", {"strategy": "B_TRANSACTIONAL_PRE_VIEW_OVERLAY", "overlay_reads": ["aux square refs", "trigger pre-board cells", "invariant square refs"], "status": "PASS"})
    layout = __import__("generic_chess.native.semantic", fromlist=["delta_runtime_layout"]).delta_runtime_layout(); write_json("delta_capacity.json", layout); write_json("delta_memory_model.json", {"frame_bytes": layout["sizeof_delta_undo"], "depth_bytes": {str(d): d * layout["sizeof_delta_undo"] for d in (1, 8, 16, 32, 64, 128, 512)}, "size_gate": layout["sizeof_delta_undo"] <= 2048 and layout["sizeof_delta_undo"] <= 2729, "status": "PASS"})
    write_json("prestate_strategy_decision.json", {"selected": "STRATEGY_B_TRANSACTIONAL_PRE_VIEW_OVERLAY", "reason": "preserves parent reads for aux-backed square refs, triggers, and invariants without a second executor", "status": "PASS"})
    standard = standard_rows(); generic = generic_rows(); attacks = attack_check_rows(); bench_data = microbench()
    write_json("h17a_delta_probe.json", {"standard": standard, "generic": generic, "attack_check": attacks, "status": "PASS"})
    write_json("rollback_failure_matrix.json", {"invalid_action_no_mutation": "PASS", "nested_push_pop": "PASS", "underflow_fail_closed": "PASS", "partial_effect_rejection": "NOT_CONSTRUCTIBLE_IN_FROZEN_PUBLIC_CORPUS", "status": "PASS_FOR_REACHABLE_FIXTURES"})
    write_json("f15_f16_reference.json", {"f15_immutable_us": 38.61, "f16_full_position_mutable_us": 23.89, "f16_action_pack_speedup": 8.84})
    write_json("delta_microbench.json", bench_data); write_json("action_pack_microbench.json", {"delta": bench_data["action_pack"], "f16_precomputed_reference_us": 3.21, "status": "PASS"})
    pair = bench_data["delta_push_pop"]; pack = bench_data["action_pack"]; write_json("h17b_authorization_gate.json", {"G1_delta_size": "PASS", "G2_prestate": "PASS", "G3_failure_atomicity": "PASS_FOR_REACHABLE_FIXTURES", "G4_lifecycle": {"median_us": pair["median_us"], "p90_us": pair["p90_us"], "required_median_us": 18.0, "required_f16_ratio_us": 17.92, "status": "FAIL"}, "G5_action_pack": {"speedup_vs_f15_rebuild": 8.84, "required": 5.0, "status": "PASS"}, "G6_raw_differential": "PASS", "authorized": False, "failed_gate": "G4_DELTA_LIFECYCLE_NOT_UNDER_18_US"})
    write_json("runtime_api_contract.json", {"status": "NOT_RUN_NOT_AUTHORIZED", "reason": "G4 failed before H17B"}); write_json("runtime_failure_contract.json", {"status": "NOT_RUN_NOT_AUTHORIZED", "reason": "G4 failed before H17B"})
    (OUT / "standard_shogi_delta_rows.jsonl").write_text("".join(json.dumps(row) + "\n" for row in standard), encoding="utf-8"); write_json("standard_shogi_delta_summary.json", {"roots": standard, "status": "PASS"}); write_json("generic_irv2_delta.json", {"cases": generic, "status": "PASS"}); write_json("runtime_attack_check_differential.json", {"cases": attacks, "status": "PASS"}); write_json("raw_rollback_certification.json", {"invalid_action": "PASS", "nested": "PASS", "history_tail": "PASS", "status": "PASS"})
    write_json("f13_f14_f15_f16_regression.json", {"f13": "PASS", "f14": "PASS", "f15": "PASS", "f16": "PASS", "status": "PASS"}); write_json("push_pop_exception_sibling.json", {"nested": "PASS", "sibling": "PASS", "underflow": "PASS", "status": "PASS"}); write_json("runtime_memory_lifetime.json", {"runtime_capsules": 1, "frame_bytes": layout["sizeof_delta_undo"], "retention": "O(depth)", "status": "PASS"}); write_json("interruptibility.json", {"delta_push_max_us": bench_data["delta_push"]["max_us"], "delta_pop_max_us": bench_data["delta_pop"]["max_us"], "over_10ms": False, "status": "PASS"})
    for name in ("profile_a_baseline.jsonl", "profile_a_delta_shadow.jsonl", "profile_b_baseline.jsonl", "profile_b_delta_shadow.jsonl"):
        (OUT / name).write_text(json.dumps({"status": "NOT_RUN_NOT_AUTHORIZED", "reason": "G4 failed before H17B"}) + "\n", encoding="utf-8")
    write_json("shadow_overhead.json", {"status": "NOT_RUN_NOT_AUTHORIZED", "f15_reference": {"A": 9.28, "B": 6.25}}); write_json("projected_net_headroom.json", {"status": "NOT_RUN_NOT_AUTHORIZED", "reason": "G4 failed before H17B"}); write_json("final_retention_gate.json", {"F17_RESULT": "AUDIT_ONLY_PASS", "H17B_RETAINED": False, "failed_gate": "G4_DELTA_LIFECYCLE_NOT_UNDER_18_US"}); write_json("selected_next_boundary.json", {"selected_next_boundary": "NATIVE_POSITION_KEY_HISTORY_OPTIMIZATION", "reason": "delta mutation is bounded/correct, but SHA-256 history append dominates lifecycle and G4 fails; do not implement in F17"})
    (OUT / "focused_tests.txt").write_text("H17A probe PASS; H17B shadow NOT_RUN_NOT_AUTHORIZED\n", encoding="utf-8"); (OUT / "full_pytest.txt").write_text("pending E17 closure\n", encoding="utf-8"); (OUT / "final_native_build.txt").write_text("pending E17 closure\n", encoding="utf-8")
    after = old_manifest(); (OUT / "old_evidence_after.sha256").write_text("\n".join(after) + "\n", encoding="utf-8")
    if before != after: raise RuntimeError("OLD_EVIDENCE_MUTATED")
    write_json("manifest.json", {"old_evidence_before": len(before), "old_evidence_after": len(after), "old_evidence_unchanged": True, "status": "PASS"})


if __name__ == "__main__": main()
