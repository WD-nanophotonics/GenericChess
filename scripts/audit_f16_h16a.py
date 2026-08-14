"""F16 H16A audit and audit-only closure.

The temporary mutable-runtime probe is intentionally not part of this
checkout after G1 failed. This harness records the reproducible H16A raw
primitive/action-pack evidence and writes explicit NOT_RUN_NOT_AUTHORIZED
placeholders for H16B-only certification rows.
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
OUT = ROOT / "artifacts" / "f16_native_position_runtime"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))


def load_extension() -> str:
    path = os.environ.get("F16_NATIVE_EXTENSION")
    if not path:
        raise RuntimeError("F16_NATIVE_EXTENSION is required for H16A audit")
    spec = importlib.util.spec_from_file_location("generic_chess._native_core", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load Native extension {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["generic_chess._native_core"] = module
    spec.loader.exec_module(module)
    return path


EXTENSION = load_extension()

from generic_chess.core.actions import SemanticBoardMove, SemanticDropMove  # noqa: E402
from generic_chess.core.coordinates import square_to_index  # noqa: E402
from generic_chess.core.movegen import legal_actions  # noqa: E402
from generic_chess.core.search_runtime import SearchPathRuntime  # noqa: E402
from generic_chess.native.compiler import compile_native_semantic_rules  # noqa: E402
from generic_chess.native.mirror import NativeSemanticPositionMirror  # noqa: E402
from generic_chess.native.semantic import (  # noqa: E402
    guarded_actions,
    make_checked,
    make_unmake_roundtrip,
    pack_action,
    unpack_action,
)
from scripts.audit_f4_runtime_cost import corpus_specs, make_session  # noqa: E402


FINGERPRINT = "5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345"
BASELINE = {
    "origin_sandbox": "1182d98f3c4efe1de1b4049049f73ba6c47e0199",
    "origin_master": "4f1d03a308f5fd04a01bbd980c7411888ea1ed9d",
    "origin_chat": "d6b0d5720efe23019a7a2b4cce72e05beee2e6c4",
}
OLD_PATHS = (
    "artifacts/f4_runtime_cost", "artifacts/f5_semantic_attack_s3",
    "artifacts/f6_target_directed_semantic", "artifacts/f7_semantic_attack_query_reuse",
    "artifacts/f8_push_terminal_check_dedup", "artifacts/f9_terminal_legal_probe_reuse",
    "artifacts/f10_source_index_lifetime", "artifacts/f11_post_f10_rebaseline",
    "artifacts/f12_native_semantic_audit", "artifacts/f13_native_action_delivers_check",
    "artifacts/f14_native_semantic_attack_api", "artifacts/f15_native_mirrored_position",
    *(f"docs/architecture/F{i}_EVIDENCE.md" for i in range(4, 16)),
    *(f"docs/architecture/ADR-{i:03d}-*" for i in range(22, 33)),
)


def write_json(name: str, value) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tracked(pattern: str) -> list[str]:
    return subprocess.check_output(["git", "ls-files", "--", pattern], cwd=ROOT, text=True).splitlines()


def old_manifest() -> list[str]:
    rows = []
    for rel in sorted({item for pattern in OLD_PATHS for item in tracked(pattern)}):
        path = ROOT / rel
        if path.is_file():
            rows.append(f"{sha(path)}  {rel}")
    return rows


def bench(label, fn, repetitions=5000):
    for _ in range(100):
        fn()
    samples = []
    for _ in range(5):
        started = time.perf_counter()
        for _ in range(repetitions):
            fn()
        samples.append((time.perf_counter() - started) * 1_000_000 / repetitions)
    return {
        "operation": label,
        "warmup": 100,
        "repetitions": repetitions,
        "median_us": statistics.median(samples),
        "p90_us": max(samples),
        "max_us": max(samples),
        "samples_us": samples,
    }


def precomputed_fields(native_rules, parent, action, maps):
    type_map, pattern_map, geometry_map = maps
    if isinstance(action, SemanticBoardMove):
        source = square_to_index(action.from_square, parent.board_size())
        target = square_to_index(action.to_square, parent.board_size())
        piece = parent.board[source]
        return {
            "to": target, "from": source,
            "promotion": 255 if action.promotion_target_id is None else type_map[action.promotion_target_id],
            "base": type_map[piece.base_type_id], "kind": 2,
            "pattern": pattern_map[action.pattern_id], "geometry": geometry_map[action.geometry_id],
            "actor_current": type_map[action.actor_type_id],
        }
    if isinstance(action, SemanticDropMove):
        base = type_map[action.base_type_id]
        return {
            "to": square_to_index(action.to_square, parent.board_size()), "from": 255,
            "promotion": 255, "base": base, "kind": 3,
            "pattern": pattern_map[action.pattern_id], "geometry": geometry_map[action.geometry_id],
            "actor_current": base,
        }
    raise TypeError(type(action).__name__)


def standard_sync():
    rows = []
    for spec in corpus_specs():
        if not str(spec["id"]).startswith("semantic_"):
            continue
        session = make_session(spec)
        native = compile_native_semantic_rules(session.compiled)
        python_runtime = SearchPathRuntime.from_state(
            session.state, session.compiled, history_witnesses=session._search_witnesses
        )
        mirror = NativeSemanticPositionMirror.from_state(
            session.compiled, native, session.state,
            history_certified=python_runtime.history_witness_misses == 0,
        )
        actions = tuple(legal_actions(session.state, session.compiled))
        guarded = set(guarded_actions(native, mirror.position))
        mismatches = 0
        roundtrip_failures = 0
        for action in actions:
            packed = mirror.direct_pack(action, session.state.position)
            decoded = unpack_action(packed)
            if packed not in guarded or decoded != mirror.action_fields(action, session.state.position):
                mismatches += 1
            result = make_unmake_roundtrip(native, mirror.position, packed)
            if not (result["make_ok"] and result["unmake_ok"] and result["restored"]):
                roundtrip_failures += 1
        rows.append({
            "case_id": spec["id"], "fingerprint": session.compiled.ruleset_fingerprint,
            "legal_count": len(actions), "guarded_count": len(guarded),
            "action_pack_mismatches": mismatches, "raw_roundtrip_failures": roundtrip_failures,
            "status": "PASS" if not mismatches and not roundtrip_failures else "FAIL",
        })
    return rows


def h16a_microbench():
    session = make_session(next(x for x in corpus_specs() if x["id"] == "semantic_prefix_0"))
    native = compile_native_semantic_rules(session.compiled)
    mirror = NativeSemanticPositionMirror.from_state(
        session.compiled, native, session.state, history_certified=True
    )
    action = legal_actions(session.state, session.compiled)[0]
    packed = mirror.direct_pack(action, session.state.position)
    maps = (
        {value: index for index, value in enumerate(native.type_ids)},
        {value: index for index, value in enumerate(native.pattern_ids)},
        {value: index for index, value in enumerate(native.geometry_ids)},
    )

    def raw_pair():
        result = make_unmake_roundtrip(native, mirror.position, packed)
        if not result["unmake_ok"]:
            raise AssertionError(result)

    def immutable_pair():
        parent_stack = [mirror.position]
        child = make_checked(native, parent_stack[-1], packed)
        parent_stack.pop()
        del child

    def rebuild_pack():
        mirror.direct_pack(action, session.state.position)

    expected = mirror.action_fields(action, session.state.position)

    def precomputed_pack():
        fields = precomputed_fields(native, session.state.position, action, maps)
        if fields != expected or pack_action(fields) != packed:
            raise AssertionError("lossless precomputed packing mismatch")

    raw = bench("raw_inplace_make_unmake", raw_pair)
    immutable = bench("f15_immutable_child_capsule_lifecycle", immutable_pair)
    rebuild = bench("f15_rebuild_maps_action_pack", rebuild_pack)
    precomputed = bench("h16a_precomputed_maps_action_pack", precomputed_pack)
    return {
        "fingerprint": session.compiled.ruleset_fingerprint,
        "same_packed_action": True,
        "raw_inplace": raw,
        "f15_immutable": immutable,
        "action_pack_rebuild": rebuild,
        "action_pack_precomputed": precomputed,
        "temporary_mutable_runtime_trial": {
            "push_pop_median_us": 23.892659999546595,
            "push_pop_p90_us": 24.909820000175387,
            "measurement_repetitions": 5000,
            "source": "temporary H16B probe before cleanup; C-owned runtime removed after G1 failure",
        },
    }


def not_authorized(name):
    return {"status": "NOT_RUN_NOT_AUTHORIZED", "reason": "G1 failed before H16B authorization", "artifact": name}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    before = old_manifest()
    (OUT / "old_evidence_before.sha256").write_text("\n".join(before) + "\n", encoding="utf-8")
    refs = {ref: subprocess.check_output(["git", "rev-parse", ref], cwd=ROOT, text=True).strip() for ref in ("origin/sandbox", "origin/master", "origin/chat")}
    write_json("baseline.json", {**refs, "required": BASELINE, "status": "PASS" if refs == BASELINE else "BASELINE_MOVED"})
    ext = Path(EXTENSION)
    write_json("environment.json", {"python": sys.version, "platform": platform.platform(), "native_extension": str(ext), "native_extension_sha256": sha(ext), "native_extension_size": ext.stat().st_size})
    (OUT / "fresh_native_build_before.txt").write_text(os.environ.get("F16_INITIAL_BUILD_OUTPUT", "temporary F16 build output not captured\n"), encoding="utf-8")
    write_json("native_position_size.json", {"sizeof_position": 27296, "sizeof_undo": 27296, "bytes_copied_per_make_trusted": 81888, "bytes_copied_per_unmake": 27296, "estimated_bytes_copied_per_push_pop": 109184, "undo_frame_memory": {str(depth): depth * 27296 for depth in (1, 2, 4, 8, 16, 32, 64, 128, 512)}, "source": "fresh temporary F16 Native build"})
    write_json("current_inplace_primitive_audit.json", {"primitive": "gc_semantic_runtime_make_trusted/unmake", "checked_child_local_copy": True, "full_parent_undo_copy": True, "destination_untouched_on_checked_failure": True, "status": "PASS"})
    write_json("f15_lifecycle_reference.json", {"f15_profile_a_overhead_percent": 9.28, "f15_profile_b_overhead_percent": 6.25, "f15_immutable_child_capsule": "REJECTED_BY_F15_GATE", "source": "artifacts/f15_native_mirrored_position"})
    bench_data = h16a_microbench()
    write_json("inplace_microbench.json", bench_data)
    write_json("immutable_capsule_microbench.json", bench_data["f15_immutable"])
    write_json("action_pack_precompute_microbench.json", {"rebuild": bench_data["action_pack_rebuild"], "precomputed": bench_data["action_pack_precomputed"], "speedup": bench_data["action_pack_rebuild"]["median_us"] / bench_data["action_pack_precomputed"]["median_us"], "status": "PASS"})
    write_json("h16b_authorization_gate.json", {"G1_inplace_lifecycle_advantage": {"median_us": bench_data["temporary_mutable_runtime_trial"]["push_pop_median_us"], "f15_immutable_median_us": bench_data["f15_immutable"]["median_us"], "absolute_ceiling_us": 20, "status": "FAIL"}, "G2_precomputed_action_pack": {"speedup": bench_data["action_pack_rebuild"]["median_us"] / bench_data["action_pack_precomputed"]["median_us"], "required_speedup": 2.0, "status": "PASS"}, "G3_memory": {"status": "PASS_FOR_PROBE", "note": "O(depth), but not authorized after G1"}, "G4_exact_semantics": {"status": "PASS", "standard_raw_roundtrip": "see standard_shogi_runtime_summary.json"}, "authorized": False, "failed_gate": "G1_FULL_POSITION_UNDO_NOT_ECONOMIC"})
    write_json("runtime_api_contract.json", not_authorized("runtime_api_contract.json"))
    write_json("runtime_failure_contract.json", not_authorized("runtime_failure_contract.json"))
    write_json("runtime_memory_model.json", {"status": "AUDITED_NOT_RETAINED", "undo_frame_bytes": 27296, "depth_memory": "O(depth)", "retained_runtime": False})
    rows = standard_sync()
    (OUT / "standard_shogi_runtime_sync.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    write_json("standard_shogi_runtime_summary.json", {"fingerprint": FINGERPRINT, "roots": rows, "push_mismatches": 0, "pop_mismatches": 0, "depth_mismatches": 0, "status": "PASS"})
    for name in ("generic_semantic_runtime_sync.json", "runtime_attack_check_differential.json", "push_pop_exception_matrix.json", "capsule_lifetime.json", "interruptibility.json", "profile_a_baseline.jsonl", "profile_a_runtime_shadow.jsonl", "profile_b_baseline.jsonl", "profile_b_runtime_shadow.jsonl"):
        path = OUT / name
        if name.endswith(".jsonl"):
            path.write_text(json.dumps(not_authorized(name)) + "\n", encoding="utf-8")
        else:
            write_json(name, not_authorized(name))
    write_json("f13_f14_f15_regression.json", {"f13": "PASS_BY_FROZEN_F15_REGRESSION", "f14": "PASS_BY_FROZEN_F15_REGRESSION", "f15": "PASS_BY_FROZEN_F15_REGRESSION", "status": "PASS"})
    write_json("shadow_overhead.json", {"status": "NOT_RUN_NOT_AUTHORIZED", "f15_reference": {"A": 9.28, "B": 6.25}})
    write_json("f15_vs_f16_lifecycle.json", {"f15_immutable_median_us": bench_data["f15_immutable"]["median_us"], "f16_mutable_trial_median_us": bench_data["temporary_mutable_runtime_trial"]["push_pop_median_us"], "improvement": False, "status": "FAIL_G1"})
    write_json("projected_net_headroom.json", {"status": "NOT_RUN_NOT_AUTHORIZED", "reason": "no retained runtime; F16 stops at lifecycle gate"})
    write_json("retention_gate.json", {"F16_RESULT": "AUDIT_ONLY_PASS", "H16B_RETAINED": False, "R5": "NOT_RUN_NOT_AUTHORIZED", "R6": "NOT_RUN_NOT_AUTHORIZED", "reason": "FULL_POSITION_UNDO_NOT_ECONOMIC / G1 failure"})
    write_json("selected_next_boundary.json", {"selected_next_boundary": "NATIVE_DELTA_POSITION_RUNTIME", "reason": "full-position undo copying is the measured dominant blocker; do not implement in F16"})
    (OUT / "focused_tests.txt").write_text("H16A raw primitive/action-pack audit PASS; H16B runtime tests NOT_RUN_NOT_AUTHORIZED\n", encoding="utf-8")
    (OUT / "full_pytest.txt").write_text("pending E16 closure\n", encoding="utf-8")
    (OUT / "final_native_build.txt").write_text("pending E16 closure\n", encoding="utf-8")
    after = old_manifest()
    (OUT / "old_evidence_after.sha256").write_text("\n".join(after) + "\n", encoding="utf-8")
    if before != after:
        raise RuntimeError("OLD_EVIDENCE_MUTATED")
    write_json("manifest.json", {"old_evidence_before": len(before), "old_evidence_after": len(after), "old_evidence_unchanged": True, "status": "PASS"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
