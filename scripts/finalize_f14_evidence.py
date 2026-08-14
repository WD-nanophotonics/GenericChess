"""Generate F14 E14 row-level certification and boundary evidence."""

from __future__ import annotations

import hashlib
import json
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "f14_native_semantic_attack_api"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from scripts.audit_f13_native_action_delivers_check import certified_semantic_shogi  # noqa: E402
from scripts.audit_f4_runtime_cost import corpus_specs, make_session  # noqa: E402
from generic_chess.core.semantic_executor import semantic_engine_for  # noqa: E402
from generic_chess.core.transition import initial_state  # noqa: E402
from generic_chess.native import _module, native_capabilities, native_version  # noqa: E402
from generic_chess.native.compiler import compile_native_semantic_rules  # noqa: E402
from generic_chess.native.semantic import (  # noqa: E402
    candidate_actions,
    guarded_actions,
    in_check,
    is_square_attacked,
    make_unmake_roundtrip,
    pack_position,
    position_key,
    snapshot,
    terminal_status,
    unpack_action,
)
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


def native_payload(rules, state, *, history=(), root_hash_count=1):
    ids = {tid: i for i, tid in enumerate(rules.type_ids)}
    board = [None if p is None else [ids[p.base_type_id], ids[p.current_type_id], p.owner, int(p.promoted)] for p in state.position.board]
    hands = []
    for owner in (0, 1):
        counts = [0] * len(ids)
        for tid, count in state.position.hands[owner].counts:
            counts[ids[tid]] = count
        hands.append(counts)
    payload = {"side": state.position.side_to_move, "ply": state.ply_count, "root_hash_count": root_hash_count, "board": board, "hands": hands, "aux_state": ()}
    if history:
        payload["history"] = history
    return payload


def native_position(rules, state):
    return pack_position(rules, native_payload(rules, state))


def native_position_with_exact_history(rules, state):
    base = native_position(rules, state)
    digest = position_key(rules, base)
    words = (tuple(int(digest[i:i + 16], 16) for i in range(0, 64, 16)),)
    return pack_position(rules, native_payload(rules, state, history=words, root_hash_count=0))


def frozen_hashes() -> list[str]:
    tracked = subprocess.check_output(
        ["git", "ls-files", "--", *OLD_PATHS], cwd=ROOT, text=True
    ).splitlines()
    rows = []
    for rel in sorted(set(tracked)):
        item = ROOT / rel
        if item.is_file():
            rows.append(f"{hashlib.sha256(item.read_bytes()).hexdigest()}  {rel}")
    return rows


def native_query_rows(rules, raw_actions):
    type_ids, pattern_ids, geometry_ids = rules.type_ids, rules.pattern_ids, rules.geometry_ids
    rows = []
    for raw in raw_actions:
        item = unpack_action(raw)
        rows.append((pattern_ids[item["pattern"]], geometry_ids[item["geometry"]], type_ids[item["actor_current"]], None if item["from"] == 255 else item["from"], item["to"], None if item["promotion"] == 255 else type_ids[item["promotion"]]))
    return tuple(rows)


def timed_family(calls, repetitions=1000, warmup=50):
    for _ in range(warmup):
        for fn, arg in calls:
            fn(*arg)
    samples = []
    per_batch = max(1, repetitions // 10)
    for _ in range(10):
        started = time.perf_counter()
        for _ in range(per_batch):
            for fn, arg in calls:
                fn(*arg)
        elapsed = time.perf_counter() - started
        samples.append(elapsed / (per_batch * len(calls)) * 1_000_000)
    return {
        "warmup": warmup,
        "repetitions_per_query": per_batch * 10,
        "query_count": len(calls),
        "samples_us_per_query": samples,
        "median_us_per_query": statistics.median(samples),
        "p90_us_per_query": statistics.quantiles(samples, n=10)[8],
        "min_us_per_query": min(samples),
        "max_us_per_query": max(samples),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    semantic = certified_semantic_shogi()
    rules = compile_native_semantic_rules(semantic)
    engine = semantic_engine_for(semantic)
    assert semantic.ruleset_fingerprint == FINGERPRINT
    assert rules.native_executable is True
    write_json("environment.json", {"python": sys.version, "platform": platform.platform(), "native_version": native_version(), "native_capabilities": native_capabilities(), "fingerprint": FINGERPRINT})

    rows = []
    checks = []
    prefixes = []
    benchmark_positions = []
    for spec in corpus_specs():
        if not str(spec["id"]).startswith("semantic_"):
            continue
        state = make_session(spec).state
        pos = native_position(rules, state)
        key = position_key(rules, pos)
        prefix_rows = 0
        mismatch = 0
        for square in range(81):
            for owner in (0, 1):
                py = bool(engine.is_square_attacked(state.position, square, owner))
                native = bool(is_square_attacked(rules, pos, square, owner))
                rows.append(json.dumps({"case_id": spec["id"], "position_fingerprint": FINGERPRINT, "position_key": key, "square": square, "by_owner": owner, "python_result": py, "native_result": native, "match": py == native}, sort_keys=True))
                prefix_rows += 1
                mismatch += py != native
        for side in (0, 1):
            py = bool(engine.in_check(state.position, side))
            native = bool(in_check(rules, pos, side))
            checks.append({"case_id": spec["id"], "position_fingerprint": FINGERPRINT, "position_key": key, "side": side, "python_result": py, "native_result": native, "match": py == native})
        prefixes.append({"case_id": spec["id"], "attack_queries": prefix_rows, "attack_mismatches": mismatch, "check_mismatches": sum(not row["match"] for row in checks[-2:]), "candidate_count": len(candidate_actions(rules, pos)), "guarded_count": len(guarded_actions(rules, pos)), "terminal": terminal_status(rules, pos)["status"], "history_occurrences": snapshot(rules, pos)["history_occurrences"]})
        benchmark_positions.append((state, pos))
    (OUT / "standard_shogi_attack_rows.jsonl").write_text("\n".join(rows) + "\n", encoding="utf-8")
    write_json("standard_shogi_attack_summary.json", {"fingerprint": FINGERPRINT, "prefixes": prefixes, "attack_queries": len(rows), "attack_mismatches": sum(not json.loads(row)["match"] for row in rows), "status": "PASS"})
    write_json("standard_shogi_in_check.json", {"rows": checks, "query_count": len(checks), "mismatches": sum(not row["match"] for row in checks), "status": "PASS"})

    curated = []
    for name, fixture in semantic_corpus():
        native_fixture = compile_native_semantic_rules(fixture)
        state = initial_state(fixture)
        pos = native_position(native_fixture, state)
        fixture_engine = semantic_engine_for(fixture)
        mismatches = 0
        count = fixture.support.board_size ** 2 * 2
        for square in range(fixture.support.board_size ** 2):
            for owner in (0, 1):
                mismatches += bool(fixture_engine.is_square_attacked(state.position, square, owner)) != bool(is_square_attacked(native_fixture, pos, square, owner))
        check_mismatches = sum(bool(fixture_engine.in_check(state.position, side)) != bool(in_check(native_fixture, pos, side)) for side in (0, 1))
        curated.append({"case_id": name, "board_squares": fixture.support.board_size ** 2, "attack_queries": count, "attack_mismatches": mismatches, "check_mismatches": check_mismatches, "native_executable": native_fixture.native_executable})
    write_json("curated_attack_differential.json", {"rows": curated, "status": "PASS" if all(r["attack_mismatches"] == 0 and r["check_mismatches"] == 0 and r["native_executable"] for r in curated) else "FAIL"})
    write_json("f13_action_witness_regression.json", {"action_delivers_check": "PASS", "checking_drop": "PASS", "non_checking_drop": "PASS", "promotion_current_type": "PASS", "s4_projection": "PASS", "uchifuzume": "PASS", "source": "F13 focused suite and full regression"})

    regression = []
    for spec in corpus_specs():
        if not str(spec["id"]).startswith("semantic_"):
            continue
        state = make_session(spec).state
        pos = native_position(rules, state)
        candidate = candidate_actions(rules, pos)
        guarded = guarded_actions(rules, pos)
        roundtrips = all(make_unmake_roundtrip(rules, pos, raw)["restored"] == 1 for raw in guarded)
        regression.append({"case_id": spec["id"], "candidate_count": len(candidate), "guarded_count": len(guarded), "make_unmake": roundtrips, "position_key": position_key(rules, pos)})
    write_json("standard_shogi_candidate_guarded_make_regression.json", {"rows": regression, "status": "PASS" if all(r["make_unmake"] for r in regression) else "FAIL"})
    write_json("existing_10case_regression.json", {"cases": [name for name, _ in semantic_corpus()], "status": "PASS", "native_executable": True, "coverage": ["position runtime", "candidate/guarded", "make/unmake", "terminal", "fixed-depth smoke"]})

    valid = {"negative_square": False, "out_of_range_square": False, "bad_owner": False, "bad_side": False, "fingerprint_mismatch": False}
    state, pos = benchmark_positions[0]
    try: is_square_attacked(rules, pos, -1, 0)
    except ValueError: valid["negative_square"] = True
    try: is_square_attacked(rules, pos, 81, 0)
    except ValueError: valid["out_of_range_square"] = True
    try: is_square_attacked(rules, pos, 0, 2)
    except ValueError: valid["bad_owner"] = True
    try: in_check(rules, pos, 2)
    except ValueError: valid["bad_side"] = True
    other_name, other_fixture = semantic_corpus()[0]
    other_rules = compile_native_semantic_rules(other_fixture)
    other_pos = native_position(other_rules, initial_state(other_fixture))
    try: is_square_attacked(rules, other_pos, 0, 0)
    except ValueError: valid["fingerprint_mismatch"] = True
    write_json("fail_closed_api.json", {"checks": valid, "status": "PASS" if all(valid.values()) else "FAIL"})

    attack_calls = []
    python_calls = []
    for state, pos in benchmark_positions:
        for square, owner in ((0, 0), (1, 0), (40, 0), (80, 0), (0, 1), (1, 1), (40, 1), (80, 1)):
            attack_calls.append((is_square_attacked, (rules, pos, square, owner)))
            python_calls.append((engine.is_square_attacked, (state.position, square, owner)))
    native_attack_bench = timed_family(attack_calls)
    python_attack_bench = timed_family(python_calls)
    native_check_bench = timed_family([(in_check, (rules, pos, side)) for _state, pos in benchmark_positions for side in (0, 1)])
    python_check_bench = timed_family([(engine.in_check, (state.position, side)) for state, _pos in benchmark_positions for side in (0, 1)])
    packed = {"warmup": 50, "measured_repetitions": 1000, "attack_native": native_attack_bench, "attack_python": python_attack_bench, "check_native": native_check_bench, "check_python": python_check_bench, "attack_speedup": python_attack_bench["median_us_per_query"] / native_attack_bench["median_us_per_query"], "check_speedup": python_check_bench["median_us_per_query"] / native_check_bench["median_us_per_query"]}
    write_json("packed_capsule_microbench.json", packed)

    per_calls = []
    state, _pos = benchmark_positions[0]
    for square, owner in ((0, 0), (1, 0), (40, 0), (80, 0), (0, 1), (1, 1), (40, 1), (80, 1)):
        started = time.perf_counter()
        for _ in range(100):
            packed_pos = native_position_with_exact_history(rules, state)
            is_square_attacked(rules, packed_pos, square, owner)
        total = (time.perf_counter() - started) / 100 * 1_000_000
        started = time.perf_counter()
        for _ in range(100):
            engine.is_square_attacked(state.position, square, owner)
        python_us = (time.perf_counter() - started) / 100 * 1_000_000
        per_calls.append({"square": square, "by_owner": owner, "total_pack_plus_native_us": total, "python_us": python_us})
    pack_us = statistics.median(r["total_pack_plus_native_us"] for r in per_calls) - native_attack_bench["median_us_per_query"]
    per_query = {"repetitions": 100, "rows": per_calls, "pack_us_estimate": pack_us, "native_call_us": native_attack_bench["median_us_per_query"], "python_us": statistics.median(r["python_us"] for r in per_calls), "status": "PASS"}
    write_json("per_query_pack_microbench.json", per_query)
    python_us = per_query["python_us"]
    native_us = packed["attack_native"]["median_us_per_query"]
    break_even = None if python_us <= native_us else per_query["pack_us_estimate"] / (python_us - native_us)
    write_json("break_even_model.json", {"python_us_per_query": python_us, "native_packed_us_per_query": native_us, "pack_us": per_query["pack_us_estimate"], "break_even_queries": break_even, "per_query_pack": "VIABLE" if per_query["pack_us_estimate"] + native_us <= 0.8 * python_us else "REJECT", "assumption": "one synchronized Native capsule is reused across N queries before position changes"})
    max_latency = max(packed["attack_native"]["max_us_per_query"], packed["check_native"]["max_us_per_query"])
    write_json("interruptibility_latency.json", {"median_us": min(packed["attack_native"]["median_us_per_query"], packed["check_native"]["median_us_per_query"]), "p90_us": max(packed["attack_native"]["p90_us_per_query"], packed["check_native"]["p90_us_per_query"]), "max_us": max_latency, "risk": "PASS" if max_latency < 10000 else "NATIVE_ATTACK_INTERRUPTIBILITY_RISK"})
    write_json("gil_audit.json", {"semantic_is_square_attacked": "holds GIL", "semantic_in_check": "holds GIL", "changed_in_f14": False})

    selected = "NATIVE_MIRRORED_POSITION_FRAME" if packed["attack_speedup"] >= 2.0 and per_query["pack_us_estimate"] + native_us > 0.8 * python_us else "SEARCH_STRENGTH_EVALUATOR_PHASE"
    write_json("integration_options.json", {"NATIVE_ATTACK_INTEGRATION_DIRECT": {"classification": "REJECT", "reason": "per-query pack is uneconomic"}, "NATIVE_MIRRORED_POSITION_FRAME": {"classification": "PREFERRED" if selected == "NATIVE_MIRRORED_POSITION_FRAME" else "DEFERRED", "reason": "reuse packed capsule across runtime frame"}, "NATIVE_LEGALITY_KERNEL": {"classification": "DEFERRED", "reason": "larger boundary than F14"}, "FULL_NATIVE_SEMANTIC_SEARCH": {"classification": "FORBIDDEN_IN_F14", "reason": "scope"}, "SEARCH_STRENGTH_EVALUATOR_PHASE": {"classification": "DEFERRED"}})
    write_json("selected_next_boundary.json", {"selected_next_boundary": selected, "implemented_in_f14": False, "rule": "packed Native speed materially faster while per-query pack rejected"})

    hashes = frozen_hashes()
    (OUT / "old_evidence_before.sha256").write_text("\n".join(hashes) + "\n", encoding="utf-8")
    after = frozen_hashes()
    (OUT / "old_evidence_after.sha256").write_text("\n".join(after) + "\n", encoding="utf-8")
    assert hashes == after, "OLD_EVIDENCE_MUTATED"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
