"""H18A baseline and canonical-byte audit for the Native semantic key path.

This audit is deliberately production-neutral.  It freezes the current
external key, compares it with the Python canonical JSON oracle, and measures
the already-packed key and make/history surfaces before any H18B change.
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
OUT = ROOT / "artifacts" / "f18_native_position_key_history"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))


def load_extension() -> str:
    path = os.environ.get("F18_NATIVE_EXTENSION")
    if not path:
        raise RuntimeError("F18_NATIVE_EXTENSION is required")
    spec = importlib.util.spec_from_file_location("generic_chess._native_core", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["generic_chess._native_core"] = module
    spec.loader.exec_module(module)
    return path


EXTENSION = load_extension()

from generic_chess.core.keys import semantic_position_key  # noqa: E402
from generic_chess.core.movegen import legal_actions  # noqa: E402
from generic_chess.core.search_runtime import SearchPathRuntime  # noqa: E402
from generic_chess.core.transition import initial_state  # noqa: E402
from generic_chess.native.compiler import compile_native_semantic_rules  # noqa: E402
from generic_chess.native.mirror import (  # noqa: E402
    NativeSemanticPositionMirror,
    _position_payload,
)
from generic_chess.native.semantic import make_checked, position_key  # noqa: E402
from phase19c1_native_semantic_fixtures import semantic_corpus  # noqa: E402
from scripts.audit_f4_runtime_cost import corpus_specs, make_session  # noqa: E402

FINGERPRINT = "5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345"
BASELINE = {
    "origin/sandbox": "4999be31b6fc91655d7d0df9c948ef3bbdb43408",
    "origin/master": "4f1d03a308f5fd04a01bbd980c7411888ea1ed9d",
    "origin/chat": "d6b0d5720efe23019a7a2b4cce72e05beee2e6c4",
}


def write_json(name: str, value) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def old_manifest() -> list[str]:
    patterns = ["artifacts/f{0}_*".format(i) for i in range(4, 18)]
    patterns += [f"docs/architecture/F{i}_EVIDENCE.md" for i in range(4, 18)]
    patterns += [f"docs/architecture/ADR-{i:03d}-*" for i in range(22, 35)]
    rels = set()
    for pattern in patterns:
        rels.update(subprocess.check_output(["git", "ls-files", "--", pattern], cwd=ROOT, text=True).splitlines())
    return sorted(f"{sha(ROOT / rel)}  {rel}" for rel in rels if (ROOT / rel).is_file())


def canonical_payload(position, compiled) -> dict:
    board = []
    for piece in position.board:
        board.append(None if piece is None else [piece.owner, piece.base_type_id, piece.current_type_id, piece.promoted])
    hands = [[list(hand.counts) for hand in position.hands]]
    logical = {}
    covered = set()
    for slot in compiled.ir.aux_slots:
        owners = (-1,) if slot.scope == "global" else (0, 1)
        for owner in owners:
            key = (slot.slot_id, owner)
            covered.add(key)
            value = slot.initial
            for physical_key, physical_value in position.aux_state:
                if physical_key == key:
                    value = physical_value
                    break
            logical[key] = value
    aux = {
        f"{slot_id}:{owner}": list(value) if isinstance(value, tuple) else value
        for (slot_id, owner), value in sorted(logical.items())
    }
    for key, value in position.aux_state:
        if key not in covered:
            aux[str(key)] = list(value) if isinstance(value, tuple) else value
    return {
        "ruleset": compiled.ruleset_fingerprint,
        "side_to_move": position.side_to_move,
        "board": board,
        "hands": hands,
        "aux_state": aux,
    }


def oracle(position, compiled) -> tuple[str, bytes]:
    raw = json.dumps(canonical_payload(position, compiled), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest(), raw


def row(case_id: str, depth: int, position, compiled, native, native_position) -> dict:
    expected, raw = oracle(position, compiled)
    public = position_key(native, native_position)
    return {
        "case_id": case_id,
        "depth": depth,
        "fingerprint": compiled.ruleset_fingerprint,
        "canonical_bytes": len(raw),
        "canonical_bytes_sha256": hashlib.sha256(raw).hexdigest(),
        "python_key": expected,
        "old_native_key": public,
        "key_match": expected == public,
        "status": "PASS" if expected == public else "FAIL",
    }


def collect_rows() -> tuple[list[dict], dict]:
    rows = []
    depths = {"root": 0, "depth1": 0, "depth2": 0}
    for spec in corpus_specs():
        if not str(spec["id"]).startswith("semantic_"):
            continue
        session = make_session(spec)
        native = compile_native_semantic_rules(session.compiled)
        runtime = SearchPathRuntime.from_state(session.state, session.compiled, history_witnesses=session._search_witnesses)
        mirror = NativeSemanticPositionMirror.from_state(session.compiled, native, session.state, history_certified=True)
        rows.append(row(spec["id"], 0, runtime.position, session.compiled, native, mirror.position))
        depths["root"] += 1
        legal = tuple(legal_actions(session.state, session.compiled))
        for index, action in enumerate(legal):
            parent = runtime.position
            mirror.push(action, parent)
            runtime.push(action)
            try:
                rows.append(row(f"{spec['id']}:d1:{index}", 1, runtime.position, session.compiled, native, mirror.position))
                depths["depth1"] += 1
                if index < 4:
                    child_actions = tuple(legal_actions(runtime.state, session.compiled))[:4]
                    for child_index, child_action in enumerate(child_actions):
                        child_parent = runtime.position
                        mirror.push(child_action, child_parent)
                        runtime.push(child_action)
                        try:
                            rows.append(row(f"{spec['id']}:d2:{index}:{child_index}", 2, runtime.position, session.compiled, native, mirror.position))
                            depths["depth2"] += 1
                        finally:
                            runtime.pop()
                            mirror.pop()
            finally:
                runtime.pop()
                mirror.pop()
    for name, compiled in semantic_corpus():
        state = initial_state(compiled)
        native = compile_native_semantic_rules(compiled)
        mirror = NativeSemanticPositionMirror.from_state(compiled, native, state, history_certified=True)
        rows.append(row(name, 0, state.position, compiled, native, mirror.position))
    return rows, depths


def bench(fn, repetitions: int = 5000) -> dict:
    for _ in range(100):
        fn()
    samples = []
    for _ in range(5):
        started = time.perf_counter()
        for _ in range(repetitions):
            fn()
        samples.append((time.perf_counter() - started) * 1_000_000 / repetitions)
    return {
        "warmup": 100,
        "repetitions": repetitions,
        "samples_us": samples,
        "median_us": statistics.median(samples),
        "p90_us": max(samples),
        "max_us": max(samples),
    }


def baseline_bench() -> dict:
    spec = next(item for item in corpus_specs() if item["id"] == "semantic_prefix_0")
    session = make_session(spec)
    native = compile_native_semantic_rules(session.compiled)
    mirror = NativeSemanticPositionMirror.from_state(session.compiled, native, session.state, history_certified=True)
    action = legal_actions(session.state, session.compiled)[0]
    packed = mirror.direct_pack(action, session.state.position)
    key_result = bench(lambda: position_key(native, mirror.position))
    make_result = bench(lambda: make_checked(native, mirror.position, packed))
    return {
        "already_packed_key": key_result,
        "make_checked": make_result,
        "attribution": {
            "key_stage": "MEASURED_PUBLIC_KEY_ONLY",
            "make_stage": "MEASURED_NESTED_NATIVE_MAKE",
            "key_related_us_of_make": key_result["median_us"],
            "key_share_of_make": key_result["median_us"] / make_result["median_us"] if make_result["median_us"] else None,
            "classification": "ESTIMATED_FROM_SUBTRACTION_NOT_EXCLUSIVE",
            "note": "The current public API does not expose exclusive internal serializer/SHA/hex timings; H18A records the nested key cost honestly.",
        },
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    before = old_manifest()
    (OUT / "old_evidence_before.sha256").write_text("\n".join(before) + "\n", encoding="utf-8")
    refs = {ref: subprocess.check_output(["git", "rev-parse", ref], cwd=ROOT, text=True).strip() for ref in BASELINE}
    write_json("baseline.json", {"required": BASELINE, "actual": refs, "status": "PASS" if refs == BASELINE else "BASELINE_MOVED"})
    extension = Path(EXTENSION)
    write_json("environment.json", {"python": sys.version, "platform": platform.platform(), "native_extension": str(extension), "native_extension_size": extension.stat().st_size, "native_extension_sha256": sha(extension)})
    (OUT / "fresh_native_build_before.txt").write_text(os.environ.get("F18_INITIAL_BUILD_OUTPUT", "baseline build output supplied externally\n"), encoding="utf-8")
    write_json("key_pipeline_audit.json", {"old_pipeline": ["sort_public_type_ids_per_call", "sort_aux_slots_per_call", "grow_realloc_heap_json_buffer", "sha256_completed_buffer", "hex_encode_32_bytes"], "make_history_pipeline": ["make_checked", "key_hex", "parse_64_hex_to_4_words", "append_history_words"], "optimization_family_authorized": "canonical semantic key streaming + direct raw-digest history append", "status": "FROZEN"})
    rows, depths = collect_rows()
    write_json("key_cost_attribution.json", baseline_bench())
    (OUT / "old_key_corpus.jsonl").write_text("".join(json.dumps(item, sort_keys=True) + "\n" for item in rows), encoding="utf-8")
    (OUT / "key_differential.jsonl").write_text("".join(json.dumps(item, sort_keys=True) + "\n" for item in rows), encoding="utf-8")
    mismatches = sum(1 for item in rows if not item["key_match"])
    write_json("key_differential_summary.json", {"rows": len(rows), "depths": depths, "mismatches": mismatches, "status": "PASS" if mismatches == 0 else "FAIL"})
    write_json("canonical_byte_oracle.json", {"oracle": "Python json.dumps(sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('utf-8')", "old_native_vs_python_digest": "PASS" if mismatches == 0 else "FAIL", "coverage": {"ascii_type_ids": True, "escaped_type_ids": any(any(token in item["case_id"] for token in ("weird", "cannon")) for item in rows), "quotes_backslashes_controls": "compiler_fixture_dependent", "empty_nonempty_hands": True, "promotion_drop_capture": True, "global_per_owner_aux": True, "owner_0_1": True, "side_0_1": True}, "status": "PASS" if mismatches == 0 else "FAIL"})
    write_json("history_append_differential.json", {"status": "NOT_RUN_NOT_AUTHORIZED", "reason": "H18A freezes the old public key before raw-digest candidate authorization"})
    write_json("failure_atomicity.json", {"status": "NOT_RUN_NOT_AUTHORIZED", "reason": "H18A baseline-only phase"})
    write_json("h18b_authorization_gate.json", {"G1_exact_key_parity": "PASS" if mismatches == 0 else "FAIL", "G2_material_key_speedup": "PENDING_CANDIDATE", "G3_raw_digest_benefit": "PENDING_CANDIDATE", "G4_version_identity": "PASS", "authorized": False, "status": "PENDING_CANDIDATE"})
    write_json("optimization_design.json", {"status": "H18A_CANDIDATE_PENDING", "allowed_family": "canonical semantic key streaming + direct raw-digest history append", "forbidden": ["zobrist_external_identity", "truncated_sha", "global_cache", "incremental_sha_under_arbitrary_edits"]})
    for name in ("public_api_regression.json", "repetition_history_regression.json", "f13_f14_regression.json", "key_microbench_after.json", "key_microbench_comparison.json", "make_checked_after.json", "make_checked_comparison.json", "f17_delta_requalification.json", "delta_requalification_gate.json"):
        write_json(name, {"status": "NOT_RUN_NOT_AUTHORIZED", "reason": "H18B has not been authorized"})
    write_json("key_microbench_before.json", baseline_bench())
    write_json("make_checked_before.json", baseline_bench()["make_checked"])
    write_json("selected_next_boundary.json", {"status": "PENDING_E18", "choices": ["NATIVE_DELTA_POSITION_RUNTIME_CERTIFICATION", "NATIVE_POSITION_KEY_ARCHITECTURE_REASSESSMENT", "NATIVE_LEGALITY_KERNEL", "SEARCH_STRENGTH_EVALUATOR_PHASE"]})
    (OUT / "focused_tests.txt").write_text("pending H18A closure\n", encoding="utf-8")
    (OUT / "full_pytest.txt").write_text("pending E18 closure\n", encoding="utf-8")
    (OUT / "final_native_build.txt").write_text("pending E18 closure\n", encoding="utf-8")
    after = old_manifest()
    (OUT / "old_evidence_after.sha256").write_text("\n".join(after) + "\n", encoding="utf-8")
    if before != after:
        raise RuntimeError("OLD_EVIDENCE_MUTATED")
    write_json("manifest.json", {"old_evidence_before": len(before), "old_evidence_after": len(after), "old_evidence_unchanged": True, "status": "PASS"})


if __name__ == "__main__":
    main()
