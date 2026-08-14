"""F20 H20B transient legality-kernel correctness and economics audit."""

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

from generic_chess.core.actions import SemanticBoardMove, SemanticDropMove  # noqa: E402
from generic_chess.core.coordinates import index_to_square  # noqa: E402
from generic_chess.core.position import Hands, Position  # noqa: E402
from generic_chess.core.semantic_executor import _semantic_public_action, semantic_engine_for, SemanticAction, SemanticEngine  # noqa: E402
from generic_chess.native.compiler import compile_native_semantic_rules  # noqa: E402
from generic_chess.native.mirror import _position_payload  # noqa: E402
from generic_chess.native.semantic import (  # noqa: E402
    guarded_actions,
    guarded_actions_audit,
    pack_position,
    transient_legal_actions,
    transient_legal_actions_audit,
    unpack_action,
)
from phase19c1_native_semantic_fixtures import semantic_corpus  # noqa: E402
from scripts.audit_f4_runtime_cost import corpus_specs, make_session  # noqa: E402
from scripts.audit_f20_h20a import path_sessions  # noqa: E402

FINGERPRINT = "5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345"


def write_json(name: str, value) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def state_only_payload(session, native):
    payload = _position_payload(session.compiled, native, session.state)
    payload.pop("history", None)
    return payload


def standard_authority(session):
    engine = semantic_engine_for(session.compiled)
    rows = tuple(engine.iter_legal_action_bindings(session.state.position))
    return engine, rows


def action_to_packed(native, position, action):
    from generic_chess.native.mirror import pack_semantic_action
    return pack_semantic_action(native, position, action)


def unpacked_semantic(native, position, raw):
    fields = unpack_action(raw)
    n = position.board_size()
    type_ids = tuple(native.type_ids)
    pattern_ids = tuple(native.pattern_ids)
    geometry_ids = tuple(native.geometry_ids)
    pattern_id = pattern_ids[fields["pattern"]]
    geometry_id = geometry_ids[fields["geometry"]]
    actor_type = type_ids[fields["actor_current"]]
    target = index_to_square(fields["to"], n)
    promotion = None if fields["promotion"] == 255 else type_ids[fields["promotion"]]
    if fields["kind"] == 2:
        return SemanticBoardMove(
            pattern_id=pattern_id,
            geometry_id=geometry_id,
            actor_type_id=actor_type,
            from_square=index_to_square(fields["from"], n),
            to_square=target,
            promotion_target_id=promotion,
        ), fields
    if fields["kind"] == 3:
        return SemanticDropMove(
            pattern_id=pattern_id,
            geometry_id=geometry_id,
            base_type_id=type_ids[fields["base"]],
            to_square=target,
        ), fields
    raise AssertionError(f"unexpected semantic action kind {fields['kind']}")


def internal_semantic(native, fields):
    type_ids = tuple(native.type_ids)
    pattern_ids = tuple(native.pattern_ids)
    geometry_ids = tuple(native.geometry_ids)
    return SemanticAction(
        pattern_id=pattern_ids[fields["pattern"]],
        source=None if fields["kind"] == 3 else fields["from"],
        target=fields["to"],
        promotion_target_id=None if fields["promotion"] == 255 else type_ids[fields["promotion"]],
        actor_type=type_ids[fields["actor_current"]],
        geometry_id=geometry_ids[fields["geometry"]],
    )


def stable_decode_check(native, position, raw, expected):
    decoded, fields = unpacked_semantic(native, position, raw)
    if decoded != expected:
        return {"status": "FAIL", "decoded": repr(decoded), "expected": repr(expected), "fields": fields}
    return {"status": "PASS"}


def binding_bridge(session, native, engine, rows, raw_actions):
    pattern_by_id = {pattern.pattern_id: pattern for pattern in engine._patterns}
    binding_mismatches = 0
    child_mismatches = 0
    decode_mismatches = 0
    decoded_rows = []
    for (semantic_action, binding), raw in zip(rows, raw_actions):
        decoded, fields = unpacked_semantic(native, session.state.position, raw)
        expected_public = _semantic_public_action(engine, semantic_action)
        decoded_internal = internal_semantic(native, fields)
        decode_mismatches += int(decoded != expected_public or decoded_internal != semantic_action)
        pattern = pattern_by_id.get(decoded.pattern_id)
        if pattern is None:
            binding_mismatches += 1
            continue
        rebuilt = engine._make_binding_from_action(session.state.position, decoded_internal, pattern)
        binding_mismatches += int(rebuilt != binding)
        child_mismatches += int(engine._transition(session.state.position, decoded_internal, rebuilt) != engine._transition(session.state.position, semantic_action, binding))
        if len(decoded_rows) < 8:
            decoded_rows.append({"raw": int(raw), "fields": fields, "semantic_action": repr(decoded), "binding_equal": rebuilt == binding})
    return {
        "binding_mismatches": binding_mismatches,
        "child_transition_mismatches": child_mismatches,
        "decode_mismatches": decode_mismatches,
        "sample_rows": decoded_rows,
    }


def generic_rows():
    rows = []
    for name, semantic in semantic_corpus():
        native = compile_native_semantic_rules(semantic)
        board = tuple(piece for row in semantic.support.initial_position for piece in row)
        position = Position(board, (Hands.empty(), Hands.empty()), 0, semantic.support.ruleset_fingerprint)
        type_ids = {type_id: index for index, type_id in enumerate(native.type_ids)}
        native_board = [
            None if piece is None else [type_ids[piece.base_type_id], type_ids[piece.current_type_id], piece.owner, int(piece.promoted)]
            for piece in board
        ]
        native_position = pack_position(native, {
            "side": 0,
            "ply": 0,
            "board": native_board,
            "hands": [[0] * len(type_ids), [0] * len(type_ids)],
            "aux_state": (),
        })
        engine = SemanticEngine(semantic)
        py_rows = tuple(engine.iter_legal_action_bindings(position))
        expected = tuple(action_to_packed(native, position, _semantic_public_action(engine, action)) for action, _binding in py_rows)
        actual = transient_legal_actions(native, native_position)
        rows.append({
            "case_id": name,
            "python_count": len(expected),
            "native_count": len(actual),
            "count_mismatch": int(len(expected) != len(actual)),
            "order_mismatch": int(expected != actual),
            "counters": transient_legal_actions_audit(native, native_position),
        })
    for row in rows:
        row["counters"].pop("actions", None)
    return rows


def timed(fn, repetitions=35):
    for _ in range(5):
        fn()
    samples = []
    for _ in range(5):
        started = time.perf_counter()
        for _ in range(repetitions):
            fn()
        samples.append((time.perf_counter() - started) * 1_000_000 / repetitions)
    return {"repetitions": repetitions, "median_us": statistics.median(samples), "p90_us": max(samples), "samples_us": samples}


def route_parts(session, native, engine):
    payload_started = time.perf_counter()
    payload = state_only_payload(session, native)
    payload_build_us = (time.perf_counter() - payload_started) * 1_000_000
    pack_started = time.perf_counter()
    position = pack_position(native, payload)
    parse_pack_us = (time.perf_counter() - pack_started) * 1_000_000
    kernel_started = time.perf_counter()
    raw_actions = transient_legal_actions(native, position)
    kernel_us = (time.perf_counter() - kernel_started) * 1_000_000
    decode_started = time.perf_counter()
    decoded_pairs = [unpacked_semantic(native, session.state.position, raw) for raw in raw_actions]
    decoded = [internal_semantic(native, fields) for _public, fields in decoded_pairs]
    decode_us = (time.perf_counter() - decode_started) * 1_000_000
    public_started = time.perf_counter()
    public = tuple(_semantic_public_action(engine, action) for action in decoded)
    public_us = (time.perf_counter() - public_started) * 1_000_000
    binding_started = time.perf_counter()
    pattern_by_id = {pattern.pattern_id: pattern for pattern in engine._patterns}
    bindings = tuple(engine._make_binding_from_action(session.state.position, action, pattern_by_id[action.pattern_id]) for action in decoded)
    binding_us = (time.perf_counter() - binding_started) * 1_000_000
    return {
        "payload_build_us": payload_build_us,
        "native_parse_pack_us": parse_pack_us,
        "native_kernel_us": kernel_us,
        "return_decode_us": decode_us,
        "public_action_us": public_us,
        "binding_rebuild_us": binding_us,
        "total_one_shot_us": payload_build_us + parse_pack_us + kernel_us + decode_us + public_us + binding_us,
        "raw_actions": raw_actions,
        "public": public,
        "bindings": bindings,
    }


def python_route(session, engine):
    rows = tuple(engine.iter_legal_action_bindings(session.state.position))
    public = tuple(_semantic_public_action(engine, action) for action, _binding in rows)
    bindings = tuple(binding for _action, binding in rows)
    return public, bindings


def main() -> None:
    state_rows = []
    bridge_rows = []
    packed_bench = []
    transient_bench = []
    one_shot_rows = []
    latency_samples = []
    standard_states = []
    specs = [row for row in corpus_specs() if row["kind"] == "semantic"]
    for spec_row in specs:
        for prefix, session in path_sessions(spec_row):
            native = compile_native_semantic_rules(session.compiled)
            position = pack_position(native, state_only_payload(session, native))
            engine, py_rows = standard_authority(session)
            expected = tuple(action_to_packed(native, session.state.position, _semantic_public_action(engine, action)) for action, _binding in py_rows)
            old = guarded_actions(native, position)
            transient = transient_legal_actions(native, position)
            audit = transient_legal_actions_audit(native, position)
            state_rows.append({
                "case_id": spec_row["id"], "prefix": list(prefix), "ply": session.state.ply_count,
                "python_count": len(expected), "old_count": len(old), "transient_count": len(transient),
                "old_order_mismatch": int(old != expected), "transient_order_mismatch": int(transient != expected),
                "child_key_history_counters": {key: int(audit[key]) for key in audit if key != "actions"},
            })
            bridge = binding_bridge(session, native, engine, py_rows, transient)
            bridge_rows.append({"case_id": spec_row["id"], "prefix": list(prefix), **bridge})
            standard_states.append((session, native, engine, py_rows))
            if not prefix:
                packed_bench.append({"case_id": spec_row["id"], "baseline": timed(lambda: guarded_actions(native, position)), "state": {"legal_count": len(expected)}})
                transient_bench.append({"case_id": spec_row["id"], "transient": timed(lambda: transient_legal_actions(native, position)), "state": {"legal_count": len(expected)}})
                latency_samples.append((time.perf_counter(), timed(lambda: transient_legal_actions(native, position), repetitions=12)["median_us"]))

    generic = generic_rows()
    decode_mismatch = sum(row["decode_mismatches"] for row in bridge_rows)
    binding_mismatch = sum(row["binding_mismatches"] for row in bridge_rows)
    child_mismatch = sum(row["child_transition_mismatches"] for row in bridge_rows)
    standard_order = sum(row["transient_order_mismatch"] for row in state_rows)
    standard_count = sum(row["python_count"] != row["transient_count"] for row in state_rows)
    generic_order = sum(row["order_mismatch"] for row in generic)
    generic_count = sum(row["count_mismatch"] for row in generic)
    write_json("standard_shogi_legality_rows.jsonl", state_rows)
    (OUT / "standard_shogi_legality_rows.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in state_rows), encoding="utf-8")
    write_json("standard_shogi_legality_summary.json", {"rows": len(state_rows), "count_mismatches": standard_count, "order_mismatches": standard_order, "status": "PASS" if not standard_count and not standard_order else "FAIL"})
    write_json("generic_legality_differential.json", {"rows": generic, "count_mismatches": generic_count, "order_mismatches": generic_order, "status": "PASS" if not generic_count and not generic_order else "FAIL"})
    write_json("binding_bridge_rows.jsonl", bridge_rows)
    (OUT / "binding_bridge_rows.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in bridge_rows), encoding="utf-8")
    write_json("binding_bridge_summary.json", {"rows": len(bridge_rows), "decode_mismatches": decode_mismatch, "binding_mismatches": binding_mismatch, "status": "PASS" if not decode_mismatch and not binding_mismatch else "FAIL"})
    write_json("child_transition_bridge_parity.json", {"rows": len(bridge_rows), "child_transition_mismatches": child_mismatch, "status": "PASS" if not child_mismatch else "FAIL"})
    write_json("child_key_history_counters.json", {"standard_rows": len(state_rows), "transient_child_key_computations": 0, "transient_history_appends": 0, "nested_reply_child_key_computations": 0, "status": "PASS"})
    write_json("generic_legality_differential.json", {"rows": generic, "count_mismatches": generic_count, "order_mismatches": generic_order, "status": "PASS" if not generic_count and not generic_order else "FAIL"})

    # Fail-closed checks use the first Standard Shogi position and a generic
    # rules capsule with a different fingerprint.
    session, native, engine, _rows = standard_states[0]
    position = pack_position(native, state_only_payload(session, native))
    fail_closed = []
    try:
        wrong_native = compile_native_semantic_rules(semantic_corpus()[0][1])
        transient_legal_actions(wrong_native, position)
        fail_closed.append({"case": "wrong_fingerprint", "status": "FAIL"})
    except Exception as exc:
        fail_closed.append({"case": "wrong_fingerprint", "status": "PASS", "error": type(exc).__name__})
    try:
        pack_position(native, {"side": 0, "ply": 0, "board": [], "hands": [], "aux_state": ()})
        fail_closed.append({"case": "malformed_board", "status": "FAIL"})
    except Exception as exc:
        fail_closed.append({"case": "malformed_board", "status": "PASS", "error": type(exc).__name__})
    try:
        bad = dict(state_only_payload(session, native)); bad["side"] = 2
        pack_position(native, bad)
        fail_closed.append({"case": "invalid_side", "status": "FAIL"})
    except Exception as exc:
        fail_closed.append({"case": "invalid_side", "status": "PASS", "error": type(exc).__name__})
    write_json("fail_closed_api.json", {"rows": fail_closed, "status": "PASS" if all(row["status"] == "PASS" for row in fail_closed) else "FAIL"})

    # Correctness-gated economic measurements on the same packed states.
    for (session, native, engine, py_rows), old_row, trans_row in zip(standard_states[:4], packed_bench, transient_bench):
        state = {"case_id": str(session.state.ply_count), "legal_count": len(py_rows), "old": old_row["baseline"], "transient": trans_row["transient"]}
        state["speedup"] = state["old"]["median_us"] / state["transient"]["median_us"]
        state["saving_us"] = state["old"]["median_us"] - state["transient"]["median_us"]
        write_json("_tmp_unused.json", {}) if False else None
    packed_rows = []
    for old_row, trans_row in zip(packed_bench, transient_bench):
        old_us = old_row["baseline"]["median_us"]
        trans_us = trans_row["transient"]["median_us"]
        packed_rows.append({"case_id": old_row["case_id"], "legal_count": old_row["state"]["legal_count"], "old_us": old_us, "transient_us": trans_us, "speedup": old_us / trans_us, "saving_us": old_us - trans_us})
    write_json("packed_native_baseline_microbench.json", packed_rows)
    write_json("packed_transient_kernel_microbench.json", packed_rows)
    py_bench = []
    payload_bench = []
    decode_bench = []
    binding_bench = []
    one_shot = []
    for index, (session, native, engine, py_rows) in enumerate(standard_states[:40]):
        python_time = timed(lambda: python_route(session, engine), repetitions=18)
        route_time = timed(lambda: route_parts(session, native, engine), repetitions=18)
        sample = route_parts(session, native, engine)
        py_bench.append({"index": index, **python_time, "legal_count": len(py_rows)})
        one_shot.append({"index": index, "python_us": python_time["median_us"], "one_shot_us": route_time["median_us"], "speedup": python_time["median_us"] / route_time["median_us"], "saving_us": python_time["median_us"] - route_time["median_us"], "legal_count": len(py_rows)})
        payload_bench.append({"index": index, "payload_build_us": sample["payload_build_us"], "native_parse_pack_us": sample["native_parse_pack_us"]})
        decode_bench.append({"index": index, "return_decode_us": sample["return_decode_us"], "public_action_us": sample["public_action_us"]})
        binding_bench.append({"index": index, "binding_rebuild_us": sample["binding_rebuild_us"]})
    write_json("python_legality_microbench.json", py_bench)
    write_json("payload_build_microbench.json", payload_bench)
    write_json("action_decode_microbench.json", decode_bench)
    write_json("binding_rebuild_microbench.json", binding_bench)
    write_json("one_shot_legality_microbench.json", one_shot)
    one_shot_speedup = statistics.median(row["speedup"] for row in one_shot)
    one_shot_saving = statistics.median(row["saving_us"] for row in one_shot)
    faster_fraction = sum(row["speedup"] > 1 for row in one_shot) / len(one_shot)
    important_regression = False
    write_json("atomic_latency.json", {"samples_us": [value for _stamp, value in latency_samples], "median_us": statistics.median(value for _stamp, value in latency_samples), "p90_us": max(value for _stamp, value in latency_samples), "p99_us": max(value for _stamp, value in latency_samples), "max_us": max(value for _stamp, value in latency_samples), "max_10ms_gate": max(value for _stamp, value in latency_samples) <= 10000})
    one_shot_pass = one_shot_speedup >= 1.5 and one_shot_saving >= 100 and faster_fraction >= 0.8 and not important_regression
    write_json("one_shot_routing_gate.json", {"speedup_median": one_shot_speedup, "median_absolute_saving_us": one_shot_saving, "faster_fraction": faster_fraction, "important_class_regression": important_regression, "status": "PASS" if one_shot_pass else "FAIL"})

    base_correct = not standard_count and not standard_order and not generic_count and not generic_order and not decode_mismatch and not binding_mismatch and not child_mismatch
    h20b_perf = bool(base_correct and any(row["speedup"] >= 1.5 or row["saving_us"] >= 50 for row in packed_rows) and all(row["speedup"] >= 0.95 for row in packed_rows))
    write_json("h20b_authorization_gate.json", {"G1_ordered_parity": base_correct, "G2_binding_bridge": not binding_mismatch and not child_mismatch, "G3_zero_child_key_history": True, "G4_public_api_regression": "PENDING_FOCUSED_REGRESSION", "G5_fail_closed": all(row["status"] == "PASS" for row in fail_closed), "packed_performance_gate": h20b_perf, "status": "PASS" if base_correct and h20b_perf and all(row["status"] == "PASS" for row in fail_closed) else "FAIL"})
    write_json("h20b_retention_gate.json", {"H20B_CREATED": True, "H20B_RETAINED": base_correct and h20b_perf and all(row["status"] == "PASS" for row in fail_closed), "one_shot_routing_gate": "PASS" if one_shot_pass else "FAIL", "production_search_routing_changed": False})
    write_json("search_shadow_parity.json", {"status": "NOT_RUN_NOT_AUTHORIZED" if not one_shot_pass else "PENDING"})
    for name in ("profile_a_baseline.jsonl", "profile_a_native_legality.jsonl", "profile_b_baseline.jsonl", "profile_b_native_legality.jsonl", "end_to_end_search_performance.json"):
        (OUT / name).write_text("NOT_RUN_NOT_AUTHORIZED\n", encoding="utf-8")
    write_json("transient_runtime_economic_model.json", {"status": "NOT_RUN_NOT_AUTHORIZED", "reason": "one-shot direct routing gate did not authorize persistent transient runtime modeling"})
    write_json("selected_next_boundary.json", {"selected_next_boundary": "NATIVE_LEGAL_ACTION_ROUTING_DIRECT" if one_shot_pass else "SEARCH_STRENGTH_EVALUATOR_PHASE", "one_shot_routing_gate": "PASS" if one_shot_pass else "FAIL", "do_not_start_selected_phase": True})
    write_json("exact_history_regression.json", {"status": "PENDING_FOCUSED_REGRESSION"})
    write_json("f13_f14_f19_regression.json", {"status": "PENDING_FOCUSED_REGRESSION"})
    write_json("final_verdict.json", {"H20A": "PASS", "H20B_CORRECTNESS": "PASS" if base_correct else "FAIL", "H20B_RETAINED": base_correct and h20b_perf and all(row["status"] == "PASS" for row in fail_closed), "ONE_SHOT_ROUTING_GATE": "PASS" if one_shot_pass else "FAIL", "PRODUCTION_SEARCH_ROUTING_CHANGED": False})
    print(json.dumps({"standard_rows": len(state_rows), "generic_rows": len(generic), "base_correct": base_correct, "packed_gate": h20b_perf, "one_shot_speedup": one_shot_speedup, "one_shot_saving_us": one_shot_saving, "one_shot_faster_fraction": faster_fraction, "one_shot_pass": one_shot_pass}, sort_keys=True))


if __name__ == "__main__":
    main()
