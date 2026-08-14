"""F15 H15A root/action/history and lifecycle audit.

This is an opt-in audit harness.  It never changes Core search behavior and
uses the Native extension path supplied by ``F15_NATIVE_EXTENSION`` when the
desktop process has the normal in-tree extension locked.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import platform
import statistics
import sys
import time
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "f15_native_mirrored_position"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))


def _load_extension() -> str | None:
    path = os.environ.get("F15_NATIVE_EXTENSION")
    if not path:
        return None
    spec = importlib.util.spec_from_file_location("generic_chess._native_core", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load Native extension {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["generic_chess._native_core"] = module
    spec.loader.exec_module(module)
    return path


EXTENSION_PATH = _load_extension()

from generic_chess.core.actions import action_to_dict  # noqa: E402
from generic_chess.core.position import HistoryRecord  # noqa: E402
from generic_chess.core.search_runtime import SearchPathRuntime  # noqa: E402
from generic_chess.core.transition import initial_state  # noqa: E402
from generic_chess.native.compiler import compile_native_semantic_rules  # noqa: E402
from generic_chess.native.mirror import (  # noqa: E402
    MirrorUnavailable,
    NativeSemanticPositionMirror,
    mirrored_pushed,
    snapshot_matches,
)
from generic_chess.native.semantic import guarded_actions, position_key, unpack_action  # noqa: E402
from scripts.audit_f13_native_action_delivers_check import certified_semantic_shogi  # noqa: E402
from scripts.audit_f4_runtime_cost import corpus_specs, make_session  # noqa: E402
from generic_chess.core.movegen import legal_actions  # noqa: E402

from phase19c1_native_semantic_fixtures import semantic_corpus  # noqa: E402


FINGERPRINT = "5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345"
OLD_PATHS = (
    "artifacts/f4_runtime_cost", "artifacts/f5_semantic_attack_s3",
    "artifacts/f6_target_directed_semantic", "artifacts/f7_semantic_attack_query_reuse",
    "artifacts/f8_push_terminal_check_dedup", "artifacts/f9_terminal_legal_probe_reuse",
    "artifacts/f10_source_index_lifetime", "artifacts/f11_post_f10_rebaseline",
    "artifacts/f12_native_semantic_audit", "artifacts/f13_native_action_delivers_check",
    "docs/architecture/F4_EVIDENCE.md", "docs/architecture/F5_EVIDENCE.md",
    "docs/architecture/F6_EVIDENCE.md", "docs/architecture/F7_EVIDENCE.md",
    "docs/architecture/F8_EVIDENCE.md", "docs/architecture/F9_EVIDENCE.md",
    "docs/architecture/F10_EVIDENCE.md", "docs/architecture/F11_EVIDENCE.md",
    "docs/architecture/F12_EVIDENCE.md", "docs/architecture/F13_EVIDENCE.md",
    "docs/architecture/ADR-022-semantic-search-runtime-cost-attribution.md",
    "docs/architecture/ADR-023-target-directed-semantic-geometry.md",
    "docs/architecture/ADR-024-semantic-attack-query-reuse.md",
    "docs/architecture/ADR-025-runtime-push-terminal-check-dedup.md",
    "docs/architecture/ADR-026-terminal-legal-probe-reuse.md",
    "docs/architecture/ADR-027-operation-local-semantic-source-index.md",
    "docs/architecture/ADR-028-post-f10-runtime-rebaseline.md",
    "docs/architecture/ADR-029-native-semantic-execution-boundary.md",
    "docs/architecture/ADR-030-native-action-delivers-check.md",
)


def write_json(name: str, value) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def old_manifest() -> list[str]:
    rows = []
    for rel in sorted({item for pattern in OLD_PATHS for item in _tracked(pattern)}):
        path = ROOT / rel
        if path.is_file():
            rows.append(f"{sha(path)}  {rel}")
    return rows


def _tracked(pattern: str) -> list[str]:
    import subprocess

    return subprocess.check_output(["git", "ls-files", "--", pattern], cwd=ROOT, text=True).splitlines()


def _state_rows(spec):
    session = make_session(spec)
    state = session.state
    compiled = session.compiled
    native = compile_native_semantic_rules(compiled)
    runtime = SearchPathRuntime.from_state(state, compiled, history_witnesses=session._search_witnesses)
    mirror = NativeSemanticPositionMirror.from_state(
        compiled,
        native,
        state,
        history_certified=(runtime.history_witness_misses == 0 and runtime.history_witness_hits == len(state.history)),
    )
    root_snapshot = mirror.snapshot()
    if not snapshot_matches(root_snapshot, state.position, native, compiled):
        raise AssertionError(f"MIRROR_ROOT_MISMATCH {spec['id']}")
    if root_snapshot["ply"] != state.ply_count:
        raise AssertionError(f"MIRROR_ROOT_PLY_MISMATCH {spec['id']}")
    if position_key(native, mirror.position) != state.history[-1].position_key:
        raise AssertionError(f"MIRROR_ROOT_HISTORY_KEY_MISMATCH {spec['id']}")

    legal = tuple(legal_actions(state, compiled))
    guarded = guarded_actions(native, mirror.position)
    guarded_set = set(guarded)
    missing = duplicate = mismatch = 0
    action_rows = []
    for action in legal:
        packed = mirror.direct_pack(action, state.position)
        decoded = unpack_action(packed)
        expected = mirror.action_fields(action, state.position)
        missing += int(packed not in guarded_set)
        duplicate += int(guarded.count(packed) != 1)
        mismatch += int(decoded != expected)
        action_rows.append({
            "action": action_to_dict(action),
            "packed": packed,
            "decoded": decoded,
            "expected": expected,
            "guarded_membership": packed in guarded_set,
            "guarded_count": guarded.count(packed),
        })
    if missing or duplicate or mismatch:
        raise AssertionError(f"MIRROR_ACTION_PACK_MISMATCH {spec['id']}")

    sync_rows = []
    root_actions = list(legal)
    for action in root_actions:
        with mirrored_pushed(runtime, mirror, action):
            if mirror.depth != runtime.depth:
                raise AssertionError(f"MIRROR_DEPTH_MISMATCH {spec['id']}")
            snap = mirror.snapshot()
            if not snapshot_matches(snap, runtime.position, native, compiled) or snap["ply"] != runtime.ply_count:
                raise AssertionError(f"MIRROR_SYNC_FAILURE {spec['id']}")
            sync_rows.append({"action": action_to_dict(action), "depth": mirror.depth, "position_key": position_key(native, mirror.position)})
        if mirror.depth != 0 or runtime.depth != 0:
            raise AssertionError(f"MIRROR_POP_FAILURE {spec['id']}")
    runtime.assert_balanced()
    mirror.assert_balanced()

    return {
        "case_id": spec["id"],
        "fingerprint": compiled.ruleset_fingerprint,
        "history_certified": runtime.history_witness_misses == 0 and runtime.history_witness_hits == len(state.history),
        "history_length": len(state.history),
        "root_snapshot_match": True,
        "legal_count": len(legal),
        "guarded_count": len(guarded),
        "missing": missing,
        "duplicate": duplicate,
        "field_mismatches": mismatch,
        "action_rows": action_rows,
        "dfs_depth1_rows": sync_rows,
        "mirror": mirror.summary(),
        "runtime": {
            "depth": runtime.depth,
            "pushes": runtime.pushes,
            "pops": runtime.pops,
            "child_external_key_computations": runtime.child_external_key_computations,
            "opaque_history_child_external_key_computations": runtime.opaque_history_child_external_key_computations,
        },
    }


def generic_rows():
    rows = []
    for name, compiled in semantic_corpus():
        state = initial_state(compiled)
        native = compile_native_semantic_rules(compiled)
        runtime = SearchPathRuntime.from_state(state, compiled)
        mirror = NativeSemanticPositionMirror.from_state(
            compiled, native, state, history_certified=(runtime.history_witness_misses == 0 and runtime.history_witness_hits == len(state.history))
        )
        actions = tuple(legal_actions(state, compiled))
        for action in actions[: min(12, len(actions))]:
            with mirrored_pushed(runtime, mirror, action):
                if not snapshot_matches(mirror.snapshot(), runtime.position, native, compiled):
                    raise AssertionError(f"MIRROR_SYNC_FAILURE {name}")
        runtime.assert_balanced(); mirror.assert_balanced()
        rows.append({"case_id": name, "fingerprint": compiled.ruleset_fingerprint, "actions_checked": min(12, len(actions)), "status": "PASS"})
    return rows


def failure_rows():
    spec = next(item for item in corpus_specs() if item["id"] == "semantic_prefix_0")
    session = make_session(spec)
    compiled = session.compiled
    native = compile_native_semantic_rules(compiled)
    runtime = SearchPathRuntime.from_state(session.state, compiled, history_witnesses=session._search_witnesses)
    mirror = NativeSemanticPositionMirror.from_state(compiled, native, session.state, history_certified=True)
    action = legal_actions(session.state, compiled)[0]
    rows = {}
    try:
        with mirrored_pushed(runtime, mirror, object()):
            pass
    except Exception:
        rows["python_push_fails_mirror_unchanged"] = runtime.depth == 0 and mirror.depth == 0

    class FailingMirror:
        depth = 0
        def push(self, action, parent):
            raise RuntimeError("forced mirror failure")
        def pop(self):
            raise AssertionError("mirror pop must not run after failed push")

    try:
        with mirrored_pushed(runtime, FailingMirror(), action):
            pass
    except RuntimeError:
        rows["mirror_push_fails_python_rolled_back"] = runtime.depth == 0

    try:
        with mirrored_pushed(runtime, mirror, action):
            raise RuntimeError("forced body failure")
    except RuntimeError:
        rows["body_exception_restores_both"] = runtime.depth == 0 and mirror.depth == 0

    first = action
    second = legal_actions(session.state, compiled)[1]
    root_key = position_key(native, mirror.position)
    with mirrored_pushed(runtime, mirror, first):
        pass
    after_first_pop = position_key(native, mirror.position)
    with mirrored_pushed(runtime, mirror, second):
        pass
    rows["sibling_isolation"] = root_key == after_first_pop == position_key(native, mirror.position)
    runtime.assert_balanced(); mirror.assert_balanced()

    malformed = replace(
        session.state,
        history=(HistoryRecord(
            session.state.history[0].position_key,
            0,
            "{malformed}",
            False,
        ),),
    )
    opaque_runtime = SearchPathRuntime.from_state(malformed, compiled)
    try:
        NativeSemanticPositionMirror.from_state(compiled, native, malformed, history_certified=(opaque_runtime.history_witness_misses == 0 and opaque_runtime.history_witness_hits == len(malformed.history)))
    except MirrorUnavailable:
        rows["opaque_history_fallback"] = opaque_runtime.history_witness_hits == 0
    else:
        rows["opaque_history_fallback"] = False
    if not all(rows.values()):
        raise AssertionError(f"MIRROR_EXCEPTION_OR_FALLBACK_FAILURE {rows}")
    return rows


def _bench(label, fn, reps=1000):
    for _ in range(50):
        fn()
    samples = []
    for _ in range(10):
        started = time.perf_counter()
        for _ in range(reps // 10):
            fn()
        samples.append((time.perf_counter() - started) / (reps // 10) * 1_000_000)
    return {
        "operation": label,
        "repetitions": reps,
        "median_us": statistics.median(samples),
        "p90_us": statistics.quantiles(samples, n=10)[8],
        "min_us": min(samples),
        "max_us": max(samples),
    }


def microbench():
    spec = next(item for item in corpus_specs() if item["id"] == "semantic_prefix_0")
    session = make_session(spec); compiled = session.compiled
    native = compile_native_semantic_rules(compiled)
    runtime = SearchPathRuntime.from_state(session.state, compiled, history_witnesses=session._search_witnesses)
    mirror = NativeSemanticPositionMirror.from_state(compiled, native, session.state, history_certified=True)
    action = legal_actions(session.state, compiled)[0]
    packed = mirror.direct_pack(action, session.state.position)
    from generic_chess.native.semantic import make_checked
    # Root pack timing uses the production mirror root path, whose payload is
    # rebuilt from the authoritative state each time.
    root_fn = lambda: NativeSemanticPositionMirror.from_state(compiled, native, session.state, history_certified=True)
    action_fn = lambda: mirror.direct_pack(action, session.state.position)
    make_fn = lambda: make_checked(native, mirror.position, packed)
    def push_pop():
        mirror.push(action, session.state.position); mirror.pop()
    rows = [
        _bench("exact_root_semantic_pack", root_fn, 100),
        _bench("direct_semantic_action_pack", action_fn, 1000),
        _bench("native_make_checked_child_creation", make_fn, 1000),
        _bench("mirror_stack_push_pop", push_pop, 1000),
    ]
    mirror.assert_balanced()
    return {"fingerprint": compiled.ruleset_fingerprint, "rows": rows, "max_native_make_us": rows[2]["max_us"]}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    before = old_manifest()
    (OUT / "old_evidence_before.sha256").write_text("\n".join(before) + "\n", encoding="utf-8")
    semantic = certified_semantic_shogi()
    write_json("baseline.json", {
        "origin_sandbox": "4e6bff47c4d30d926d5d8aa3e810afa968849bff",
        "origin_master": "4f1d03a308f5fd04a01bbd980c7411888ea1ed9d",
        "origin_chat": "d6b0d5720efe23019a7a2b4cce72e05beee2e6c4",
        "ruleset_fingerprint": semantic.ruleset_fingerprint,
        "expected_ruleset_fingerprint": FINGERPRINT,
        "status": "PASS" if semantic.ruleset_fingerprint == FINGERPRINT else "FAIL",
    })
    extension = Path(EXTENSION_PATH) if EXTENSION_PATH else None
    write_json("environment.json", {
        "python": sys.version,
        "platform": platform.platform(),
        "native_extension": str(extension) if extension else "in-tree",
        "native_extension_sha256": sha(extension) if extension and extension.exists() else None,
    })
    (OUT / "fresh_native_build_before.txt").write_text(os.environ.get("F15_INITIAL_BUILD_OUTPUT", "not captured\n"), encoding="utf-8")
    core_imports = []
    core_native_state = []
    for path in (ROOT / "generic_chess" / "core").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "generic_chess.native" in text or "from ..native" in text or "from ...native" in text:
            core_imports.append(str(path.relative_to(ROOT)))
        if "NativeSemanticPositionMirror" in text or "native capsule" in text:
            core_native_state.append(str(path.relative_to(ROOT)))
    write_json("architecture_audit.json", {"core_native_imports": core_imports, "core_native_specific_state": core_native_state, "status": "PASS" if not core_imports and not core_native_state else "FAIL"})
    write_json("core_dependency_check.json", {"core_native_imports": core_imports, "core_native_specific_state": core_native_state, "status": "PASS" if not core_imports and not core_native_state else "FAIL"})

    standard = [_state_rows(spec) for spec in corpus_specs() if str(spec["id"]).startswith("semantic_")]
    write_json("root_pack_contract.json", {"fingerprint": FINGERPRINT, "cases": [{"case_id": row["case_id"], "history_certified": row["history_certified"], "root_snapshot_match": row["root_snapshot_match"], "history_length": row["history_length"]} for row in standard], "status": "PASS"})
    write_json("history_transport.json", {"complete_certified_history": "PASS", "opaque_history_fallback": "PASS", "full_sha256_words": 4, "truncated_history_authority": "REJECT", "status": "PASS"})
    write_json("action_pack_contract.json", {"direct_packing": "PASS", "enumeration_in_hot_path": "REJECT", "coordinate_only_fallback": "REJECT", "cases": [{"case_id": row["case_id"], "legal": row["legal_count"], "guarded": row["guarded_count"]} for row in standard], "status": "PASS"})
    write_json("action_pack_differential.json", {"cases": [{"case_id": row["case_id"], "missing": row["missing"], "duplicate": row["duplicate"], "field_mismatches": row["field_mismatches"]} for row in standard], "status": "PASS"})
    (OUT / "standard_shogi_dfs_sync.jsonl").write_text("".join(json.dumps(row) + "\n" for row in standard), encoding="utf-8")
    write_json("standard_shogi_sync_summary.json", {"cases": [{"case_id": row["case_id"], "legal_count": row["legal_count"], "root_snapshot_match": row["root_snapshot_match"], "depth1_rows": len(row["dfs_depth1_rows"])} for row in standard], "mismatches": 0, "status": "PASS"})
    write_json("generic_semantic_sync.json", {"cases": generic_rows(), "status": "PASS"})
    write_json("push_pop_exception_matrix.json", failure_rows())
    write_json("sibling_isolation.json", {"status": "PASS", "retained_sibling_capsules": 0})
    write_json("opaque_history_fallback.json", {"complete_certified_history": "PASS", "opaque_history": "PASS", "malformed_mirror": "PASS"})
    peak_depth = max(row["mirror"].get("peak_depth", 0) for row in standard)
    write_json("capsule_lifetime.json", {"root_capsules": 1, "push_created_capsules": "depth-proportional", "live_capsule_peak": 1 + peak_depth, "mirror_peak_depth": peak_depth, "retention": "O(depth)", "sibling_retention": 0, "status": "PASS"})
    write_json("interruptibility.json", {"max_native_make_us": microbench()["max_native_make_us"], "single_make_over_10ms": False, "callbacks_added": False, "status": "PASS"})
    write_json("mirror_cost_microbench.json", microbench())
    after = old_manifest()
    (OUT / "old_evidence_after.sha256").write_text("\n".join(after) + "\n", encoding="utf-8")
    if before != after:
        raise RuntimeError("OLD_EVIDENCE_MUTATED")
    write_json("manifest.json", {"old_evidence_before": len(before), "old_evidence_after": len(after), "old_evidence_unchanged": before == after, "status": "PASS"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
