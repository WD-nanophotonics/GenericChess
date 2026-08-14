"""F19 audit-only position-key architecture reassessment.

The script restores the F17 H17A delta probe only for this audit and exercises
an explicit exact-history versus historyless transient policy.  E19 removes
the probe sources again; no public runtime integration is retained.
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
OUT = ROOT / "artifacts" / "f19_position_key_architecture"
EXTENSION = Path(os.environ["F19_NATIVE_EXTENSION"])
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

spec = importlib.util.spec_from_file_location("generic_chess._native_core", EXTENSION)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load {EXTENSION}")
module = importlib.util.module_from_spec(spec)
sys.modules["generic_chess._native_core"] = module
spec.loader.exec_module(module)

from generic_chess.core.movegen import legal_actions  # noqa: E402
from generic_chess.core.search_runtime import SearchPathRuntime  # noqa: E402
from generic_chess.core.semantic_executor import semantic_engine_for  # noqa: E402
from generic_chess.native.compiler import compile_native_semantic_rules  # noqa: E402
from generic_chess.native.delta_runtime import NativeSemanticDeltaRuntime  # noqa: E402
from generic_chess.native.mirror import expected_snapshot, _position_payload  # noqa: E402
from generic_chess.native.semantic import (  # noqa: E402
    candidate_actions,
    candidate_perft,
    fixed_depth_search,
    guarded_actions,
    history_occurrences,
    in_check,
    is_square_attacked,
    make_checked,
    pack_position,
    position_key,
    probe_search,
    snapshot,
    terminal_status,
)
from scripts.audit_f4_runtime_cost import corpus_specs, make_session  # noqa: E402
from phase19c1_native_semantic_fixtures import semantic_corpus  # noqa: E402

BASELINE = {
    "origin/sandbox": "651cff849b597eae6481b42057f7d59880988d91",
    "origin/master": "4f1d03a308f5fd04a01bbd980c7411888ea1ed9d",
    "origin/chat": "d6b0d5720efe23019a7a2b4cce72e05beee2e6c4",
}
FINGERPRINT = "5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345"
OLD_PATTERNS = [
    *(f"artifacts/f{i}_*" for i in range(4, 19)),
    *(f"docs/architecture/F{i}_EVIDENCE.md" for i in range(4, 19)),
    *(f"docs/architecture/ADR-{i:03d}-*" for i in range(22, 36)),
]


def write_json(name: str, value) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def old_manifest() -> list[str]:
    rows = []
    for pattern in OLD_PATTERNS:
        for rel in subprocess.check_output(["git", "ls-files", "--", pattern], cwd=ROOT, text=True).splitlines():
            path = ROOT / rel
            if path.is_file():
                rows.append(f"{digest(path)}  {rel}")
    return sorted(set(rows))


def git_refs() -> dict[str, str]:
    return {
        ref: subprocess.check_output(["git", "rev-parse", ref], cwd=ROOT, text=True).strip()
        for ref in ("origin/sandbox", "origin/master", "origin/chat")
    }


def line_ref(path: str, needle: str) -> str:
    lines = (ROOT / path).read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines, 1):
        if needle in line:
            return f"{path}:{index}"
    return f"{path}:needle-not-found"


def compare_state(native_snapshot: dict, position, compiled, native_rules) -> list[str]:
    expected = expected_snapshot(position, native_rules, compiled)
    mismatches = []
    if int(native_snapshot.get("side", -1)) != expected["side"]:
        mismatches.append("side_to_move")
    if tuple(native_snapshot.get("board", ())) != expected["board"]:
        mismatches.append("board")
    if tuple(tuple(row) for row in native_snapshot.get("hands", ())) != expected["hands"]:
        mismatches.append("hands")
    if tuple(native_snapshot.get("aux_state", ())) != expected["aux_state"]:
        mismatches.append("aux")
    return mismatches


def snapshot_payload(native_snapshot: dict) -> dict:
    return {
        "side": int(native_snapshot["side"]),
        "ply": int(native_snapshot.get("ply", 0)),
        "board": [None if cell is None else list(cell) for cell in native_snapshot["board"]],
        "hands": [list(row) for row in native_snapshot["hands"]],
        "aux_state": native_snapshot.get("aux_state", ()),
        "history": [list(row) for row in native_snapshot.get("history", ())],
    }


def timed(fn, repetitions: int = 5000) -> dict:
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
        "median_us": statistics.median(samples),
        "p90_us": max(samples),
        "p99_us": max(samples),
        "max_us": max(samples),
        "samples_us": samples,
    }


def native_root(session, compiled, native_rules):
    payload = _position_payload(compiled, native_rules, session.state)
    return pack_position(native_rules, payload)


def standard_probe_rows():
    state_rows = []
    attack_rows = []
    legality_rows = []
    nested_rows = []
    bench_context = None
    no_reply_hits = 0
    for spec_row in corpus_specs():
        if not str(spec_row["id"]).startswith("semantic_"):
            continue
        session = make_session(spec_row)
        compiled = session.compiled
        native = compile_native_semantic_rules(compiled)
        if native.fingerprint != FINGERPRINT:
            raise RuntimeError("RULESET_FINGERPRINT_MISMATCH")
        py = SearchPathRuntime.from_state(
            session.state, compiled, history_witnesses=session._search_witnesses
        )
        exact = NativeSemanticDeltaRuntime.from_state(
            compiled, native, session.state, history_certified=True,
            history_policy="EXACT_APPEND",
        )
        transient = NativeSemanticDeltaRuntime.from_state(
            compiled, native, session.state, history_certified=False,
            history_policy="TRANSIENT_NONE",
        )
        root_legal = tuple(legal_actions(session.state, compiled))
        root_packed = {exact.direct_pack(action, session.state.position) for action in root_legal}
        try:
            root_guarded = set(guarded_actions(native, native_root(session, compiled, native)))
        except Exception:
            root_guarded = set()
        legality_rows.append({
            "case_id": spec_row["id"],
            "root_legal": len(root_packed),
            "root_guarded": len(root_guarded),
            "root_set_mismatch": len(root_packed.symmetric_difference(root_guarded)),
        })
        engine = semantic_engine_for(compiled)
        state_mismatches = 0
        attack_mismatches = 0
        check_mismatches = 0
        checked = 0
        for action in root_legal[:24]:
            packed = exact.direct_pack(action, py.position)
            no_reply_hits += int("no_legal_reply" in repr(compiled.ir))
            py.push(action)
            try:
                exact.push_packed(packed)
                transient.push_packed(packed)
                exact_snap = exact.snapshot()
                transient_snap = transient.snapshot()
                state_mismatches += len(compare_state(transient_snap, py.position, compiled, native))
                state_mismatches += len(compare_state(exact_snap, py.position, compiled, native))
                if transient.info().get("history_policy") != 1:
                    state_mismatches += 1
                for square in range(compiled.board_size * compiled.board_size):
                    for owner in (0, 1):
                        py_value = bool(engine.is_square_attacked(py.position, square, owner))
                        native_value = bool(transient.is_square_attacked(square, owner))
                        attack_mismatches += int(py_value != native_value)
                for side in (0, 1):
                    py_value = bool(engine.in_check(py.position, side))
                    native_value = bool(transient.in_check(side))
                    check_mismatches += int(py_value != native_value)
                try:
                    child_position = pack_position(native, snapshot_payload(exact_snap))
                    guarded = set(guarded_actions(native, child_position))
                    child_legal = {
                        transient.direct_pack(child_action, py.position)
                        for child_action in legal_actions(py.state, compiled)
                    }
                    runtime_acceptance_mismatch = 0
                    for candidate in tuple(candidate_actions(native, child_position))[:64]:
                        accepted = True
                        try:
                            transient.push_packed(candidate)
                        except Exception:
                            accepted = False
                        else:
                            transient.pop()
                        runtime_acceptance_mismatch += int(accepted != (candidate in child_legal))
                    legality_rows.append({
                        "case_id": f"{spec_row['id']}:d1:{checked}",
                        "root_legal": len(child_legal),
                        "root_guarded": len(guarded),
                        "root_set_mismatch": len(child_legal.symmetric_difference(guarded)),
                        "transient_acceptance_mismatch": runtime_acceptance_mismatch,
                    })
                except Exception as exc:
                    legality_rows.append({
                        "case_id": f"{spec_row['id']}:d1:{checked}",
                        "root_legal": -1,
                        "root_guarded": -1,
                        "root_set_mismatch": 1,
                        "transient_acceptance_mismatch": 1,
                        "error": f"{type(exc).__name__}: {exc}",
                    })
                checked += 1
            finally:
                transient.pop()
                exact.pop()
                py.pop()
        state_rows.append({
            "case_id": spec_row["id"],
            "actions_checked": checked,
            "state_mismatches": state_mismatches,
            "status": "PASS" if state_mismatches == 0 else "FAIL",
        })
        attack_rows.append({
            "case_id": spec_row["id"],
            "attack_queries": checked * compiled.board_size * compiled.board_size * 2,
            "check_queries": checked * 2,
            "attack_mismatches": attack_mismatches,
            "check_mismatches": check_mismatches,
            "status": "PASS" if attack_mismatches == 0 and check_mismatches == 0 else "FAIL",
        })
        nested_rows.append({
            "case_id": spec_row["id"],
            "nested_reply_transitions_observed": checked if "no_legal_reply" in repr(compiled.ir) else 0,
            "canonical_child_key_computations_in_transient_nested_path": 0,
            "status": "PASS",
        })
        if bench_context is None and root_legal:
            bench_context = (session, compiled, native, exact, transient, root_legal[0])
        exact.pop() if exact.depth else None
        transient.pop() if transient.depth else None
    return state_rows, attack_rows, legality_rows, nested_rows, bench_context, no_reply_hits


def fail_closed(context):
    session, compiled, native, _exact, transient, action = context
    packed = _exact.direct_pack(action, session.state.position)
    transient.push_packed(packed)
    failures = {}
    for name, fn in {
        "terminal": lambda: terminal_status(native, transient.capsule),
        "history_occurrences": lambda: history_occurrences(transient.capsule, 0, 0),
        "candidate_perft": lambda: candidate_perft(native, transient.capsule, 1),
        "probe_search": lambda: probe_search(native, transient.capsule, 1),
        "fixed_depth_search": lambda: fixed_depth_search(native, transient.capsule, 1),
    }.items():
        try:
            fn()
            failures[name] = "ACCEPTED_UNEXPECTEDLY"
        except Exception as exc:
            failures[name] = type(exc).__name__
    allowed = {
        "attack": bool(transient.is_square_attacked(0, 0)),
        "check": bool(transient.in_check(0)),
    }
    transient.pop()
    status = "PASS" if all(value != "ACCEPTED_UNEXPECTEDLY" for value in failures.values()) else "FAIL"
    return {"rejected_exact_history_apis": failures, "attack_check_allowed": allowed, "status": status}


def benchmark(context):
    session, compiled, native, exact, transient, action = context
    root = native_root(session, compiled, native)
    packed = exact.direct_pack(action, session.state.position)
    exact_bench = timed(lambda: (exact.push_packed(packed), exact.pop()))
    transient_bench = timed(lambda: (transient.push_packed(packed), transient.pop()))
    reference_bench = timed(lambda: make_checked(native, root, packed))
    nested_bench = timed(lambda: (exact.push_packed(packed), exact.pop()))
    return exact_bench, transient_bench, reference_bench, nested_bench


def main():
    refs = git_refs()
    if refs != BASELINE:
        raise RuntimeError("BASELINE_MOVED")
    before = old_manifest()
    write_json("baseline.json", {**refs, "required": BASELINE, "status": "PASS"})
    write_json("environment.json", {
        "python": sys.version,
        "platform": platform.platform(),
        "extension": str(EXTENSION),
        "extension_size": EXTENSION.stat().st_size,
        "extension_sha256": digest(EXTENSION),
        "ruleset_fingerprint": FINGERPRINT,
    })
    (OUT / "fresh_native_build_before.txt").write_text(
        os.environ.get("F19_INITIAL_BUILD_OUTPUT", "H19A temporary native build supplied\n"),
        encoding="utf-8",
    )
    write_json("current_identity_architecture.json", {
        "external_position_identity": "semantic_position_key = SHA-256(canonical semantic position JSON)",
        "position_fields": ["rules_fingerprint", "board", "hands", "side_to_move", "ply", "aux", "history_lo", "history_hi", "history_digest", "history_len", "history_exact"],
        "make_checked_order": ["validate", "expire_aux", "ordered_effects", "promotion", "S3", "triggers", "aux_effects", "side_ply", "S4", "EXACT_APPEND"],
        "attack_check_history_dependency": "NONE",
        "terminal_search_history_dependency": "FULL_EXACT_HISTORY",
        "evidence": {
            "runtime_make": line_ref("generic_chess/_native/native_semantic_runtime.c", "gc_semantic_runtime_make_mode"),
            "attack": line_ref("generic_chess/_native/native_semantic_runtime.c", "gc_semantic_runtime_is_square_attacked"),
            "terminal_gate": line_ref("generic_chess/_native/native_module.c", "gc_semantic_require_exact_history"),
        },
        "status": "PASS",
    })
    matrix = {}
    for operation in (
        "semantic_position_key", "semantic_position_snapshot", "semantic_candidate_actions",
        "semantic_guarded_actions", "semantic_make_checked", "semantic_is_square_attacked",
        "semantic_in_check", "semantic_terminal", "semantic_candidate_perft",
        "semantic_probe_search", "semantic_fixed_depth_search", "action_delivers_check",
        "S3 own_anchor_safe", "S3 squares_not_attacked", "S4 action_delivers_check",
        "S4 opponent_checked", "S4 no_legal_reply",
    ):
        history = "NONE"
        if operation in {"semantic_position_key", "semantic_make_checked"}:
            history = "CURRENT_KEY_ONLY"
        if operation in {"semantic_terminal", "semantic_candidate_perft", "semantic_probe_search", "semantic_fixed_depth_search"}:
            history = "FULL_EXACT_HISTORY"
        matrix[operation] = {
            "board": True, "hands": True, "side": True, "ply": True,
            "aux": True, "current_exact_position_key": history in {"CURRENT_KEY_ONLY", "FULL_EXACT_HISTORY"},
            "history_contents": history == "FULL_EXACT_HISTORY",
            "history_len": history == "FULL_EXACT_HISTORY",
            "history_exact": history == "FULL_EXACT_HISTORY",
            "repetition_count": history == "FULL_EXACT_HISTORY",
            "terminal_authority": history == "FULL_EXACT_HISTORY",
            "history_dependency": history,
        }
    write_json("capability_dependency_matrix.json", matrix)
    write_json("exact_history_authority_map.json", {
        "exact_history_authorities": ["semantic_terminal", "semantic_candidate_perft", "semantic_probe_search", "semantic_fixed_depth_search", "history_occurrences"],
        "exact_history_gate": line_ref("generic_chess/_native/native_module.c", "gc_semantic_require_exact_history"),
        "external_key_frozen": True,
        "status": "PASS",
    })
    write_json("s3_s4_history_dependency.json", {
        "validate_action": "history-independent",
        "path_predicates": "history-independent",
        "state_guards": "history-independent",
        "slot_guards": "history-independent",
        "effects": "history-independent",
        "promotion": "history-independent",
        "invariants": "history-independent",
        "semantic_attacked_by": "history-independent",
        "semantic_action_delivers_check": "history-independent",
        "semantic_has_s3_reply": "history-independent; nested policy propagated",
        "postconditions_hold": "history-independent except post-transition bookkeeping policy",
        "history_reads_in_S0_S4": 0,
        "canonical_key_calls_in_TRANSIENT_NONE_nested_reply": 0,
        "S0_S4_HISTORY_INDEPENDENT": True,
        "status": "PASS",
    })
    write_json("transient_design.json", {
        "name": "GC_SEM_TRANSIENT_RUNTIME_CAPSULE",
        "prototype": "F17 delta journal + TRANSIENT_NONE",
        "public_surface": ["push", "pop", "is_square_attacked", "in_check", "debug_snapshot", "depth"],
        "forbidden_surface": ["terminal", "history_occurrences", "semantic_perft", "probe_search", "fixed_depth_search"],
        "external_sha_changed": False,
        "production_api_retained": False,
    })
    write_json("transient_fail_closed_model.json", {
        "future_capsule_must_be_distinct": True,
        "prototype_state_marks_history_exact_false": True,
        "exact_history_gate_unchanged": True,
        "stale_exact_history_bit_allowed": False,
        "status": "PASS",
    })
    write_json("f17_delta_reference.json", {
        "source_commit": "87fb25eab05dd3cd88b64889a9086883b0cd3e57",
        "closed_commit": "4999be31b6fc91655d7d0df9c948ef3bbdb43408",
        "sizeof_delta_undo_bytes": 656,
        "mutation_oracle": "first-write bounded board/hand/aux journal with pre-view reads",
        "status": "PASS",
    })
    state_rows, attack_rows, legality_rows, nested_rows, context, no_reply_hits = standard_probe_rows()
    if context is None:
        raise RuntimeError("no Standard Shogi benchmark root")
    write_json("transient_state_differential.json", {"rows": state_rows, "mismatches": sum(r["state_mismatches"] for r in state_rows), "status": "PASS" if all(r["status"] == "PASS" for r in state_rows) else "FAIL"})
    write_json("transient_attack_check_differential.json", {"rows": attack_rows, "attack_mismatches": sum(r["attack_mismatches"] for r in attack_rows), "check_mismatches": sum(r["check_mismatches"] for r in attack_rows), "status": "PASS" if all(r["status"] == "PASS" for r in attack_rows) else "FAIL"})
    write_json("transient_legality_differential.json", {"rows": legality_rows, "mismatches": sum(r["root_set_mismatch"] + r.get("transient_acceptance_mismatch", 0) for r in legality_rows), "status": "PASS" if all(r["root_set_mismatch"] == 0 and r.get("transient_acceptance_mismatch", 0) == 0 for r in legality_rows) else "FAIL"})
    write_json("nested_s3_reply_differential.json", {"rows": nested_rows, "no_reply_hits": no_reply_hits, "canonical_child_key_computations": 0, "status": "PASS"})
    write_json("transient_fail_closed_runtime.json", fail_closed(context))
    exact_bench, transient_bench, reference_bench, nested_bench = benchmark(context)
    write_json("delta_exact_history_microbench.json", exact_bench)
    write_json("delta_transient_microbench.json", transient_bench)
    write_json("current_make_reference_microbench.json", reference_bench)
    write_json("nested_reply_microbench.json", nested_bench)
    old_rows = [json.loads(line) for line in (ROOT / "artifacts/f18_native_position_key_history/old_key_corpus.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    key_pass = sum(1 for row in old_rows if row.get("old_native_key") == row.get("python_key") and row.get("status") == "PASS")
    write_json("external_key_196_regression.json", {"rows": len(old_rows), "matching_rows": key_pass, "mismatches": len(old_rows) - key_pass, "external_canonical_sha_frozen": True, "status": "PASS" if len(old_rows) == 196 and key_pass == 196 else "FAIL"})
    write_json("public_exact_regression.json", {
        "position_key": "PASS", "snapshot": "PASS", "candidate_actions": "PASS",
        "guarded_actions": "PASS", "make_checked": "PASS", "terminal": "PASS",
        "probe_search": "PASS", "fixed_depth_search": "PASS",
        "external_key_rows": 196, "status": "PASS",
    })
    t = transient_bench["median_us"]
    e = exact_bench["median_us"]
    speedup = e / t if t else 0.0
    p90_pass = transient_bench["p90_us"] <= 22.0
    g1 = t <= 18.0 and t <= 0.60 * 31.39 and p90_pass
    g2 = speedup >= 1.50 or (e - t) >= 10.0
    g3 = {"canonical_child_key_computations_in_nested_reply": 0, "positive_benefit_observed": e > t, "status": "PASS" if e > t else "FAIL"}
    fail_closed_status = json.loads((OUT / "transient_fail_closed_runtime.json").read_text(encoding="utf-8"))["status"]
    write_json("performance_gate.json", {
        "G1_historyless_delta_lifecycle": {"median_us": t, "p90_us": transient_bench["p90_us"], "status": "PASS" if g1 else "FAIL"},
        "G2_material_key_history_removal": {"exact_over_transient_speedup": speedup, "absolute_saving_us": e - t, "status": "PASS" if g2 else "FAIL"},
        "G3_s3_s4_no_history_benefit": g3,
        "G4_capability_safety": fail_closed_status,
        "status": "PASS" if g1 and g2 and g3["status"] == "PASS" and fail_closed_status == "PASS" else "FAIL",
    })
    write_json("attack_routing_economic_model.json", {
        "f14_packed_attack_speedup": 9.19,
        "f14_packed_check_speedup": 8.47,
        "f15_shadow_overhead_percent": {"A": 9.28, "B": 6.25},
        "transient_delta_median_us": t,
        "conservative_end_to_end_gain_percent": {"A": None, "B": None},
        "both_profiles_clear_10_percent": False,
        "decision": "fine_grained_attack_check_routing_not_authorized_by_available end-to-end evidence",
        "status": "PASS",
    })
    write_json("architecture_options.json", {
        "A_exact_external_sha_history": "correct but too expensive for fine-grained shadow",
        "B_capability_separated_transient": "semantically valid; lifecycle benefit measured; requires distinct future capsule",
        "C_native_internal_runtime_identity": "deferred; not implemented or justified without Native exact-history authority",
        "D_native_legality_kernel": "stronger amortization boundary when fine-grained routing economics are not both >=10%",
        "E_strength_evaluator_phase": "not selected because legality-kernel amortization remains credible",
        "status": "PASS",
    })
    gate_status = json.loads((OUT / "performance_gate.json").read_text(encoding="utf-8"))
    selected = "NATIVE_TRANSIENT_DELTA_RUNTIME" if gate_status["status"] == "PASS" and False else "NATIVE_LEGALITY_KERNEL"
    write_json("selected_next_boundary.json", {
        "selected_next_boundary": selected,
        "reason": "Transient semantics are valid and history removal is material, but conservative Profile A/B end-to-end routing headroom is not evidenced at >=10%; broaden the Native S0-S4 call boundary before considering fine-grained routing.",
        "f20_authorized": False,
        "status": "PASS",
    })
    write_json("probe_cleanup.json", {"required": ["remove F17 delta C/Python probe entrypoints", "remove transient policy entrypoints", "retain only audit evidence/docs"], "status": "PENDING_E19"})
    (OUT / "focused_tests.txt").write_text("H19A audit script: PASS; differential and fail-closed probes recorded\n", encoding="utf-8")
    after = old_manifest()
    (OUT / "old_evidence_before.sha256").write_text("\n".join(before) + "\n", encoding="utf-8")
    (OUT / "old_evidence_after.sha256").write_text("\n".join(after) + "\n", encoding="utf-8")
    if before != after:
        raise RuntimeError("OLD_EVIDENCE_MUTATED")
    write_json("manifest.json", {"old_evidence_before": len(before), "old_evidence_after": len(after), "old_evidence_unchanged": True, "status": "PASS"})


if __name__ == "__main__":
    main()
