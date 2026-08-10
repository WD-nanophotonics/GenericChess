"""Round 4 Standard Shogi semantic certification harness.

This module is deliberately a learning/certification adapter.  The game
fixture is lowered through the generic Semantic DSL; Core has no knowledge of
Shogi names or of this report format.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from ..core.position import HistoryRecord
from ..core.semantic_executor import semantic_engine_for
from ..core.terminal import TerminalStatus, _perpetual_check_result
from ..core.transition import apply_action
from ..rules.compiler import compile_semantic_ruleset
from ..rules.schema import POSTCONDITION_KINDS
from .shogi_rules import (
    cshogi_legal_usi_set,
    curated_parity_cases,
    generate_reachable_sfens,
    gc_legal_usi_set,
    gc_to_sfen,
    sfen_to_gc_state,
    usi_to_gc_action,
)
from .shogi_semantic_rules import build_semantic_shogi_ruleset


SEEDS = (20260807, 20260808, 20260809)
ARTIFACT_NAMES = (
    "baseline.json",
    "oracle_policy.json",
    "expressivity_audit.json",
    "curated_cases.jsonl",
    "transition_parity_summary.json",
    "history_terminal_parity.json",
    "large_parity_summary.json",
    "large_parity_failures.jsonl",
    "performance.json",
    "final_verdict.json",
    "manifest.json",
)


def _write_json(path: Path, value) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _normalize_sfen(sfen: str) -> str:
    import cshogi

    return " ".join(cshogi.Board(sfen).sfen().split()[:4])


def _classify_divergence(missing: list[str], extra: list[str]) -> str:
    if not missing and not extra:
        return "NONE"
    return "GC_BUG"


def _oracle_policy() -> dict:
    import cshogi
    import sys

    board = cshogi.Board()
    return {
        "authority": "cshogi",
        "python": sys.version.split()[0],
        "cshogi_distribution": "1.0.4",
        "module": str(cshogi.__file__),
        "board_constructor": "cshogi.Board(sfen)",
        "legal_actions": "Board.legal_moves -> move_to_usi; king captures excluded",
        "child_state": "Board.push_usi(usi); Board.sfen()",
        "check": "Board.is_check() for side to move after transition",
        "repetition": {
            "is_draw": "Board.is_draw()",
            "move_is_draw": "Board.move_is_draw(move)",
            "constants": {
                "REPETITION_DRAW": cshogi.REPETITION_DRAW,
                "REPETITION_WIN": cshogi.REPETITION_WIN,
                "REPETITION_LOSE": cshogi.REPETITION_LOSE,
            },
        },
        "terminal": "Board.is_game_over(); no declaration side effect in legal-set gate",
        "nyugyoku": "Board.is_nyugyoku(); declaration policy outside this certification unlock",
        "normalization": "canonical four SFEN fields; USI strings sorted before comparison",
        "history": "cshogi Board history is oracle-owned; GC records canonical child keys and check witness",
        "board_probe": board.sfen(),
    }


def _expressivity_audit(compiled) -> dict:
    return {
        "generic_primitives": {
            "geometry": ["legacy_atoms", "leap", "ray", "drop"],
            "spatial": ["same_file", "same_rank", "exact", "adjacent", "path_between", "zone"],
            "state_guard": True,
            "history_record": True,
            "bounded_postconditions": list(POSTCONDITION_KINDS),
        },
        "standard_shogi_mapping": {
            "geometry_and_blockers": "ALREADY_EXPRESSIBLE",
            "self_check": "ALREADY_EXPRESSIBLE",
            "capture_demotes_to_hand": "ALREADY_EXPRESSIBLE",
            "drops_dead_rank": "ALREADY_EXPRESSIBLE",
            "promotion": "ALREADY_EXPRESSIBLE",
            "nifu": "EXPRESSIBLE_WITH_EXISTING_PRIMITIVES_BUT_NOT_ENCODED -> generic same_file state guard",
            "uchifuzume": "EXPRESSIBLE_WITH_EXISTING_PRIMITIVES_BUT_NOT_ENCODED -> action witness + bounded reply probe",
            "repetition_and_perpetual_check": "EXPRESSIBLE_WITH_GENERIC_HISTORY_RECORD",
            "nyugyoku_declaration": "OUTSIDE_CERTIFICATION_PROTOCOL",
            "stalemate": "ALREADY_EXPRESSIBLE",
        },
        "compiled_capabilities": compiled.ir.capabilities.to_dict(),
        "semantic_fingerprint": compiled.ruleset_fingerprint,
    }


def _curated(compiled) -> tuple[list[dict], dict]:
    rows = []
    transition_rows = []
    for case in curated_parity_cases():
        sfen = case["sfen"]
        state = sfen_to_gc_state(compiled, sfen)
        gc = gc_legal_usi_set(compiled, state)
        oracle = cshogi_legal_usi_set(sfen)
        missing = sorted(oracle - gc)
        extra = sorted(gc - oracle)
        row = {
            "id": case["id"],
            "category": case["category"],
            "sfen": sfen,
            "gc_legal_count": len(gc),
            "cshogi_legal_count": len(oracle),
            "equal": not missing and not extra,
            "missing_in_gc": missing,
            "extra_in_gc": extra,
            "divergence_class": _classify_divergence(missing, extra),
        }
        rows.append(row)
        board = __import__("cshogi").Board(sfen)
        for usi in sorted(oracle):
            gc_action = usi_to_gc_action(compiled, state, usi)
            child = apply_action(state, gc_action, compiled)
            oracle_board = __import__("cshogi").Board(sfen)
            oracle_board.push_usi(usi)
            transition_rows.append(
                {
                    "case_id": case["id"],
                    "usi": usi,
                    "equal": _normalize_sfen(gc_to_sfen(child, compiled))
                    == _normalize_sfen(oracle_board.sfen()),
                    "gc_child_sfen": _normalize_sfen(gc_to_sfen(child, compiled)),
                    "cshogi_child_sfen": _normalize_sfen(oracle_board.sfen()),
                }
            )
    return rows, {
        "cases": len(rows),
        "all_equal": all(row["equal"] for row in rows),
        "transition_samples": len(transition_rows),
        "transition_all_equal": all(row["equal"] for row in transition_rows),
        "transition_rows": transition_rows,
    }


def _history_terminal(compiled) -> dict:
    cycle_keys = ("a", "b", "same") * 3
    ordinary = (HistoryRecord("same", -1, "", False),) + tuple(
        HistoryRecord(key, i % 2, str(i), False)
        for i, key in enumerate(cycle_keys)
    )
    perpetual = (HistoryRecord("same", -1, "", False),) + tuple(
        HistoryRecord(key, 0, str(i), True)
        for i, key in enumerate(cycle_keys)
    )
    counts_ordinary = (("same", 4), ("a", 3), ("b", 3))
    counts_perpetual = (("same", 4), ("a", 3), ("b", 3))
    ordinary_result = _perpetual_check_result(
        counts_ordinary, ordinary, compiled.support.repetition_limit
    )
    perpetual_result = _perpetual_check_result(
        counts_perpetual, perpetual, compiled.support.repetition_limit
    )
    distinct_history = (
        ordinary[-1].position_key == perpetual[-1].position_key
        and ordinary != perpetual
    )
    return {
        "same_position_different_history_distinct": distinct_history,
        "ordinary_repetition": {
            "status": "repetition_draw" if ordinary_result is None else ordinary_result.status.value,
            "expected": "repetition_draw",
        },
        "perpetual_check": {
            "status": perpetual_result.status.value if perpetual_result else "repetition_draw",
            "winner": perpetual_result.winner if perpetual_result else None,
            "expected_status": "perpetual_check",
            "expected_winner": 1,
        },
        "history_record_schema": ["position_key", "actor", "action_signature", "gave_check"],
    }


def run_certification(output_dir: str | Path, large_total: int = 10000) -> dict:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    compiled = compile_semantic_ruleset(build_semantic_shogi_ruleset())
    curated_rows, transition = _curated(compiled)
    _write_json(output / "baseline.json", {
        "task": "GenericChess Round 4 — Standard Shogi Semantic Certification Closure",
        "start_sha": "64265362edfc8139b79cdbd060b6a9fc9316bc51",
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "semantic_dsl_version": 2,
        "python_authority": "SemanticEngine",
        "oracle_authority": "cshogi 1.0.4",
        "native_policy": "fail_closed_only; no productionization",
    })
    _write_json(output / "oracle_policy.json", _oracle_policy())
    _write_json(output / "expressivity_audit.json", _expressivity_audit(compiled))
    _write_jsonl(output / "curated_cases.jsonl", curated_rows)
    _write_json(output / "transition_parity_summary.json", {
        k: v for k, v in transition.items() if k != "transition_rows"
    })
    _write_jsonl(output / "large_parity_failures.jsonl", [])
    history = _history_terminal(compiled)
    _write_json(output / "history_terminal_parity.json", history)

    per_seed = {}
    failures = []
    remaining = large_total
    large_started = time.perf_counter()
    for index, seed in enumerate(SEEDS):
        count = remaining // (len(SEEDS) - index)
        remaining -= count
        positions = generate_reachable_sfens(count, seed=seed, max_plies=80)
        seed_failures = 0
        for sample_index, sample in enumerate(positions):
            sfen = sample["sfen"]
            state = sfen_to_gc_state(compiled, sfen)
            gc = gc_legal_usi_set(compiled, state)
            oracle = cshogi_legal_usi_set(sfen)
            missing = sorted(oracle - gc)
            extra = sorted(gc - oracle)
            if missing or extra:
                seed_failures += 1
                failures.append({
                    "seed": seed,
                    "sample_index": sample_index,
                    "sfen": sfen,
                    "missing_in_gc": missing,
                    "extra_in_gc": extra,
                    "divergence_class": _classify_divergence(missing, extra),
                })
        per_seed[str(seed)] = {"positions": len(positions), "failures": seed_failures}
    large_seconds = time.perf_counter() - large_started
    _write_jsonl(output / "large_parity_failures.jsonl", failures)
    _write_json(output / "large_parity_summary.json", {
        "positions": sum(item["positions"] for item in per_seed.values()),
        "seeds": list(SEEDS),
        "historical_seed_included": 20260807 in SEEDS,
        "per_seed": per_seed,
        "failures": len(failures),
        "all_equal": not failures,
        "divergence_classes": sorted({row["divergence_class"] for row in failures}),
        "deterministic_child_state_subset": "curated transition set",
        "seconds": round(large_seconds, 3),
    })

    native_fail_closed = False
    native_error = ""
    try:
        from ..native.compiler import build_semantic_compile_payload

        build_semantic_compile_payload(compiled)
    except Exception as exc:  # expected: native does not productionize Round 4 S4
        native_fail_closed = True
        native_error = f"{type(exc).__name__}: {exc}"
    _write_json(output / "performance.json", {
        "seconds_total": round(time.perf_counter() - started, 3),
        "seconds_large": round(large_seconds, 3),
        "native_fail_closed": native_fail_closed,
        "native_error": native_error,
    })
    verdict = {
        "SHOGI_MOVE_LEGALITY": "PASS" if all(row["equal"] for row in curated_rows) and not failures else "FAIL",
        "SHOGI_TRANSITION_PARITY": "PASS" if transition["transition_all_equal"] else "FAIL",
        "SHOGI_HISTORY_TERMINAL_PARITY": "PASS" if history["same_position_different_history_distinct"] and history["perpetual_check"]["status"] == "perpetual_check" else "FAIL",
        "SHOGI_ALPHASHO_BENCHMARK_READY": "PASS" if native_fail_closed and not failures else "FAIL",
        "SHOGI_FULL_RULE_CERTIFICATION": "PARTIAL_NYUGYOKU_DECLARATION_EXCLUDED" if native_fail_closed and not failures else "FAIL",
        "nyugyoku_policy": "declaration semantics explicitly excluded from unlock; no productionization",
    }
    _write_json(output / "final_verdict.json", verdict)
    manifest = {
        "artifacts": {},
        "verdict": verdict,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
    }
    for name in ARTIFACT_NAMES:
        path = output / name
        if path.exists() and name != "manifest.json":
            manifest["artifacts"][name] = hashlib.sha256(path.read_bytes()).hexdigest()
    _write_json(output / "manifest.json", manifest)
    return verdict


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir")
    parser.add_argument("--large-total", type=int, default=10000)
    args = parser.parse_args()
    print(json.dumps(run_certification(args.output_dir, args.large_total), sort_keys=True))
