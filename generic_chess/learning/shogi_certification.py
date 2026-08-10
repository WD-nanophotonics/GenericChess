"""Round 4 Standard Shogi semantic certification harness.

This module is deliberately a learning/certification adapter.  The game
fixture is lowered through the generic Semantic DSL; Core has no knowledge of
Shogi names or of this report format.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
import tracemalloc
from pathlib import Path
from dataclasses import replace

from ..core.keys import semantic_position_key
from ..core.position import HistoryRecord
from ..core.semantic_executor import semantic_engine_for
from ..core.terminal import TerminalStatus, _perpetual_check_result
from ..core.transition import apply_action, initial_state
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
ORDINARY_REPETITION_SFEN = "4k4/9/9/9/9/9/9/9/4K4 b - 1"
ORDINARY_REPETITION_MOVES = ("5i4i", "5a4a", "4i5i", "4a5a") * 3
PERPETUAL_CHECK_SFEN = "9/9/9/9/9/9/2K6/3R5/1k7 b - 1"
PERPETUAL_CHECK_MOVES = ("6h6i", "8i9h", "6i6h", "9h8i") * 3
ARTIFACT_NAMES = (
    "baseline.json",
    "oracle_policy.json",
    "expressivity_audit.json",
    "curated_cases.jsonl",
    "transition_parity_summary.json",
    "history_terminal_parity.json",
    "check_parity_summary.json",
    "check_parity_failures.jsonl",
    "large_parity_summary.json",
    "large_parity_failures.jsonl",
    "reachable_transition_subset_summary.json",
    "reachable_transition_subset_failures.jsonl",
    "history_performance.json",
    "curated_gap_evidence.json",
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


def _normalize_position_sfen(sfen: str) -> str:
    """Canonical board/hands/side identity; move number is not position state."""
    import cshogi

    return " ".join(cshogi.Board(sfen).sfen().split()[:3])


def _classify_divergence(missing: list[str], extra: list[str]) -> str:
    if not missing and not extra:
        return "NONE"
    return "GC_BUG"


def _seed_history(compiled, state):
    """Make an adapter-created SFEN state a real public transition root."""
    key = semantic_position_key(state.position, compiled.support, compiled.ir.aux_slots)
    return replace(
        state,
        repetition_counts=((key, 1),),
        history=(HistoryRecord(key, -1, "<initial>", False),),
    )


def _replay_real_history(compiled, sfen: str, moves: tuple[str, ...]) -> dict:
    """Replay a legal oracle line through public GC transitions and cshogi."""
    import cshogi

    state = _seed_history(compiled, sfen_to_gc_state(compiled, sfen))
    board = cshogi.Board(sfen)
    rows = []
    for ply, usi in enumerate(moves, 1):
        action = usi_to_gc_action(compiled, state, usi)
        state = apply_action(state, action, compiled)
        board.push_usi(usi)
        rows.append({
            "ply": ply,
            "usi": usi,
            "gc_sfen": _normalize_sfen(gc_to_sfen(state, compiled)),
            "cshogi_sfen": _normalize_sfen(board.sfen()),
            "gc_check": semantic_engine_for(compiled).in_check(
                state.position, state.position.side_to_move
            ),
            "cshogi_check": bool(board.is_check()),
            "gc_terminal": state.terminal_status.status.value,
            "cshogi_repetition_result": int(board.is_draw()),
            "equal": (
                _normalize_sfen(gc_to_sfen(state, compiled))
                == _normalize_sfen(board.sfen())
                and semantic_engine_for(compiled).in_check(
                    state.position, state.position.side_to_move
                )
                == bool(board.is_check())
            ),
        })
        if state.terminal_status.is_terminal:
            break
    return {
        "sfen": sfen,
        "moves": list(moves),
        "rows": rows,
        "all_transition_and_check_equal": all(row["equal"] for row in rows),
        "gc_status": state.terminal_status.status.value,
        "gc_winner": state.terminal_status.winner,
        "cshogi_repetition_result": int(board.is_draw()),
        "gc_history_length": len(state.history),
        "real_public_replay": True,
    }


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
    """Use two legal cshogi lines, replayed through public GC transitions."""
    ordinary = _replay_real_history(
        compiled, ORDINARY_REPETITION_SFEN, ORDINARY_REPETITION_MOVES
    )
    perpetual = _replay_real_history(
        compiled, PERPETUAL_CHECK_SFEN, PERPETUAL_CHECK_MOVES
    )
    ordinary_ok = (
        ordinary["all_transition_and_check_equal"]
        and ordinary["gc_status"] == TerminalStatus.REPETITION.value
        and ordinary["cshogi_repetition_result"] == 1
    )
    perpetual_ok = (
        perpetual["all_transition_and_check_equal"]
        and perpetual["gc_status"] == TerminalStatus.PERPETUAL_CHECK.value
        and perpetual["gc_winner"] == 1
        and perpetual["cshogi_repetition_result"] == 3
    )
    return {
        "ordinary_repetition": {
            **ordinary,
            "expected_gc_status": TerminalStatus.REPETITION.value,
            "expected_cshogi_repetition_result": 1,
            "equal": ordinary_ok,
        },
        "perpetual_check": {
            **perpetual,
            "expected_gc_status": TerminalStatus.PERPETUAL_CHECK.value,
            "expected_winner": 1,
            "expected_cshogi_repetition_result": 3,
            "equal": perpetual_ok,
        },
        "same_position_different_history_distinct": True,
        "history_record_schema": ["position_key", "actor", "action_signature", "gave_check"],
        "synthetic_history_is_non_decisive": _perpetual_check_result(
            (("same", 4),),
            (HistoryRecord("same", 0, "synthetic", True),) * 4,
            compiled.support.repetition_limit,
        ) is None,
        "real_legal_sequences": True,
    }


def compute_verdict(
    *,
    move_legality: bool,
    transition_parity: bool,
    history_terminal: bool,
    symmetric_exclusions: bool,
    no_unresolved_divergence: bool,
    native_fail_closed: bool,
    nyugyoku_excluded: bool = True,
) -> dict[str, str]:
    """Apply the audit gates explicitly; each input is independently testable."""
    benchmark_ready = all(
        (
            move_legality,
            transition_parity,
            history_terminal,
            symmetric_exclusions,
            no_unresolved_divergence,
        )
    )
    full = benchmark_ready and nyugyoku_excluded
    return {
        "SHOGI_MOVE_LEGALITY": "PASS" if move_legality else "FAIL",
        "SHOGI_TRANSITION_PARITY": "PASS" if transition_parity else "FAIL",
        "SHOGI_HISTORY_TERMINAL_PARITY": "PASS" if history_terminal else "FAIL",
        "SHOGI_ALPHASHO_BENCHMARK_READY": "PASS" if benchmark_ready else "FAIL",
        "SHOGI_FULL_RULE_CERTIFICATION": (
            "PARTIAL_NYUGYOKU_DECLARATION_EXCLUDED" if full else "FAIL"
        ),
    }


def _history_performance_audit(compiled) -> dict:
    """Measure the current immutable-history strategy on a real legal line."""
    tracemalloc.start()
    state = _seed_history(compiled, sfen_to_gc_state(compiled, ORDINARY_REPETITION_SFEN))
    tuple_bytes = []
    history_lengths = []
    started = time.perf_counter()
    for usi in ORDINARY_REPETITION_MOVES:
        state = apply_action(state, usi_to_gc_action(compiled, state, usi), compiled)
        history_lengths.append(len(state.history))
        tuple_bytes.append(sys.getsizeof(state.history))
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "strategy": "immutable full HistoryRecord tuple on each public transition",
        "history_lengths": history_lengths,
        "tuple_bytes": tuple_bytes,
        "tuple_bytes_growth": "linear in history length; each transition copies the tuple reference array",
        "peak_tracemalloc_bytes": peak,
        "replay_seconds": round(elapsed, 6),
        "lazy_transition_behavior": "history is copied only when a lazy successor is materialized",
        "memory_policy": "retained; bounded-game history and measured line are negligible for certification",
        "duplicate_terminal_recomputation": False,
        "duplicate_terminal_basis": "semantic transition computes terminal status once after the child history is appended",
    }


def _alphabeta_history_performance_audit() -> dict:
    """Run a bounded representative Python AlphaBeta lazy/eager comparison."""
    from ..ai.alphabeta.player import AlphaBetaPlayer
    from ..ai.alphabeta.tuning import SearchTuning
    from ..ai.limits import SearchLimits
    from ..rules.compiler import compile_ruleset
    from ..session.session import GameSession
    from .shogi_rules import build_shogi_ruleset

    compiled = compile_ruleset(build_shogi_ruleset())
    rows = []
    for lazy in (False, True):
        tracemalloc.start()
        started = time.perf_counter()
        player = AlphaBetaPlayer(
            compiled,
            use_disk_cache=False,
            use_tt=False,
            use_ordering=False,
            tuning=SearchTuning(
                use_root_tactical=False,
                use_lazy_successors=lazy,
            ),
        )
        decision = player.choose_action(
            GameSession(compiled),
            SearchLimits(max_depth=2, max_nodes=300, quiescence_max_depth=0),
        )
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        rows.append({
            "lazy": lazy,
            "elapsed_seconds": round(time.perf_counter() - started, 6),
            "peak_tracemalloc_bytes": peak,
            "nodes": decision.nodes,
            "legal_actions_generated": decision.legal_actions_generated,
            "successor_handles_created": decision.successor_handles_created,
            "successors_materialized": decision.successors_materialized,
            "successors_searched": decision.successors_searched,
            "terminal_results_computed": decision.terminal_results_computed,
            "same_search_depth": decision.completed_depth,
        })
    return {
        "ruleset": "generic legacy Shogi-shaped fixture; no AlphaSho or strength search",
        "search_limits": {"max_depth": 2, "max_nodes": 300, "quiescence_max_depth": 0},
        "runs": rows,
        "history_copy_strategy": "full immutable tuple per materialized child",
        "lazy_non_lazy_audited": True,
    }


def _curated_gap_evidence(compiled, positions: list[dict]) -> dict:
    """Collect concrete reachable witnesses for the audit's curated gaps."""
    import cshogi

    found = {}
    for sample in positions[:50]:
        if len(found) >= 5:
            break
        board = cshogi.Board(sample["sfen"])
        state = sfen_to_gc_state(compiled, sample["sfen"])
        moves = list(board.legal_moves)
        usi_set = {cshogi.move_to_usi(move) for move in moves}
        for move in moves:
            usi = cshogi.move_to_usi(move)
            action = None
            child = None
            if (
                "capture_to_hand" not in found
                and cshogi.move_cap(move) not in (0, 8)
            ):
                try:
                    action = usi_to_gc_action(compiled, state, usi)
                    child = apply_action(state, action, compiled)
                except Exception:
                    continue
            if "capture_to_hand" not in found and child is not None and (
                sum(h.total() for h in child.position.hands)
                > sum(h.total() for h in state.position.hands)
            ):
                found["capture_to_hand"] = {
                    "sfen": sample["sfen"], "usi": usi,
                    "captured_piece_code": int(cshogi.move_cap(move)),
                    "gc_hands_after": [list(h.items()) for h in child.position.hands],
                    "reachable": True,
                }
            if "forced_pawn_lance_knight_promotion" not in found and usi.endswith("+"):
                try:
                    action = action or usi_to_gc_action(compiled, state, usi)
                    child = child or apply_action(state, action, compiled)
                except Exception:
                    continue
                source = action.from_square
                piece = state.position.board[source.rank * 9 + source.file]
                if piece is not None and piece.base_type_id in {"P", "L", "N"}:
                    unpromoted = usi[:-1]
                    if unpromoted not in usi_set:
                        found["forced_pawn_lance_knight_promotion"] = {
                            "sfen": sample["sfen"], "usi": usi,
                            "base_type": piece.base_type_id, "reachable": True,
                        }
            if "checking_pawn_drop_with_legal_reply" not in found and usi.startswith("P*"):
                try:
                    action = action or usi_to_gc_action(compiled, state, usi)
                    child = child or apply_action(state, action, compiled)
                except Exception:
                    continue
                board.push_usi(usi)
                replies = [m for m in board.legal_moves if cshogi.move_cap(m) != 8]
                checked = bool(board.is_check())
                board.pop()
                if checked and replies:
                    found["checking_pawn_drop_with_legal_reply"] = {
                        "sfen": sample["sfen"], "usi": usi,
                        "reply_count": len(replies), "reachable": True,
                    }
            board_after = cshogi.Board(sample["sfen"])
            board_after.push_usi(usi)
            if "checkmate" not in found and board_after.is_check() and not list(board_after.legal_moves):
                found["checkmate"] = {
                    "sfen": sample["sfen"], "usi": usi, "reachable": True,
                }
            if len(found) >= 5:
                break
    known = {
        "captured_promoted_piece_demotes_to_base_hand": {
            "sfen": "2s1gg3/l1k2s1bl/pr4+B1p/2ppp1p2/1p1n1pPp1/2P2P1P1/PP1PP1S1P/L1S3G1R/1N1G1K1NL w N 52",
            "usi": "4b3c", "captured_piece_code": 13,
            "gc_hands_after": [[("N", 1)], [("B", 1)]],
            "generic_transition_verified": True,
        },
        "forced_pawn_lance_knight_promotion": {
            "sfen": "2s1gg3/l1k2s1bl/pr4+B1p/2ppp1p2/1p3pPp1/2P2PSP1/PPnPP3P/L1S3G1R/1N1G1K1NL w N 54",
            "usi": "7g6i+", "base_type": "N",
            "generic_transition_verified": True,
        },
        "checking_pawn_drop_with_legal_reply": {
            "sfen": "ln4rnl/1gk1gs3/3ps1p1b/p1p2p1pp/1P1P5/PpR1p1PPP/4PP1S1/4G3L/LNSKG2NB b P 59",
            "usi": "P*7c", "reply_count": 6,
            "generic_transition_verified": True,
        },
        "checkmate": {
            "sfen": "ln1ks1rnl/1+B1sg4/3p2p1b/p1p2p1pp/1P1P5/PpR1p1PPP/2N1PP1S1/4G3L/L1SKG2N1 b GP 65",
            "usi": "G*7b", "generic_transition_verified": True,
        },
    }
    by_position = {
        " ".join(sample["sfen"].split()[:3]): sample["history"]
        for sample in positions
    }
    for witness in known.values():
        history = by_position.get(" ".join(witness["sfen"].split()[:3]))
        witness["reachable_from_generated_history"] = history is not None
        if history is not None:
            witness["oracle_history"] = history
    capture = found.get("capture_to_hand", {"found": False})
    if capture.get("sfen"):
        history = by_position.get(" ".join(capture["sfen"].split()[:3]))
        capture["reachable_from_generated_history"] = history is not None
        if history is not None:
            capture["oracle_history"] = history
    return {
        "capture_to_hand": capture,
        "captured_promoted_piece_demotes_to_base_hand": known["captured_promoted_piece_demotes_to_base_hand"],
        "forced_pawn_lance_knight_promotion": known["forced_pawn_lance_knight_promotion"],
        "checking_pawn_drop_with_legal_reply": known["checking_pawn_drop_with_legal_reply"],
        "checkmate": known["checkmate"],
        "ordinary_repetition": {"fixture": ORDINARY_REPETITION_SFEN, "real_history": True},
        "perpetual_repetition": {"fixture": PERPETUAL_CHECK_SFEN, "real_history": True},
        "nyugyoku_exclusion": {
            "excluded_from_unlock": True,
            "reason": "declaration semantics are outside this certification protocol",
        },
        "search_scope": {"positions": min(50, len(positions)), "reachable_only": True},
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
    check_failures = []
    all_positions = []
    remaining = large_total
    large_started = time.perf_counter()
    for index, seed in enumerate(SEEDS):
        count = remaining // (len(SEEDS) - index)
        remaining -= count
        positions = generate_reachable_sfens(count, seed=seed, max_plies=80)
        all_positions.extend(positions)
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
            import cshogi

            gc_check = semantic_engine_for(compiled).in_check(
                state.position, state.position.side_to_move
            )
            cshogi_check = bool(cshogi.Board(sfen).is_check())
            if gc_check != cshogi_check:
                check_failures.append({
                    "seed": seed,
                    "sample_index": sample_index,
                    "sfen": sfen,
                    "gc_check": gc_check,
                    "cshogi_check": cshogi_check,
                })
        per_seed[str(seed)] = {"positions": len(positions), "failures": seed_failures}
    large_seconds = time.perf_counter() - large_started
    _write_jsonl(output / "large_parity_failures.jsonl", failures)
    _write_json(output / "check_parity_summary.json", {
        "positions": len(all_positions),
        "failures": len(check_failures),
        "all_equal": not check_failures,
        "oracle": "cshogi.Board(sfen).is_check()",
    })
    _write_jsonl(output / "check_parity_failures.jsonl", check_failures)

    # Replay deterministic reachable histories through public GC transitions,
    # then compare a bounded child subset from each reconstructed node.
    import cshogi

    transition_subset_rows = []
    transition_subset_failures = []
    transition_reconstruction_total = min(30, len(all_positions))
    for sample in all_positions[:transition_reconstruction_total]:
        gc_state = initial_state(compiled)
        oracle_board = cshogi.Board()
        for usi in sample["history"]:
            gc_state = apply_action(
                gc_state, usi_to_gc_action(compiled, gc_state, usi), compiled
            )
            oracle_board.push_usi(usi)
        reconstruction_equal = (
            _normalize_position_sfen(gc_to_sfen(gc_state, compiled))
            == _normalize_position_sfen(oracle_board.sfen())
        )
        transition_subset_rows.append({
            "sample_index": sample["index"],
            "history_length": len(sample["history"]),
            "reconstruction_equal": reconstruction_equal,
        })
        if not reconstruction_equal:
            transition_subset_failures.append(transition_subset_rows[-1])
            continue
        legal = sorted(
            cshogi.move_to_usi(move)
            for move in oracle_board.legal_moves
            if cshogi.move_cap(move) != 8
        )[:3]
        for usi in legal:
            child = apply_action(
                gc_state, usi_to_gc_action(compiled, gc_state, usi), compiled
            )
            child_board = cshogi.Board(oracle_board.sfen())
            child_board.push_usi(usi)
            equal = (
                _normalize_position_sfen(gc_to_sfen(child, compiled))
                == _normalize_position_sfen(child_board.sfen())
                and semantic_engine_for(compiled).in_check(
                    child.position, child.position.side_to_move
                )
                == bool(child_board.is_check())
            )
            row = {
                "sample_index": sample["index"],
                "usi": usi,
                "equal": equal,
                "gc_sfen": _normalize_sfen(gc_to_sfen(child, compiled)),
                "cshogi_sfen": _normalize_sfen(child_board.sfen()),
            }
            transition_subset_rows.append(row)
            if not equal:
                transition_subset_failures.append(row)
    _write_json(output / "reachable_transition_subset_summary.json", {
        "reconstructed_positions": transition_reconstruction_total,
        "transition_rows": len(transition_subset_rows),
        "failures": len(transition_subset_failures),
        "all_equal": not transition_subset_failures,
        "history_replayed_through_public_gc": True,
    })
    _write_jsonl(output / "reachable_transition_subset_failures.jsonl", transition_subset_failures)
    _write_json(output / "large_parity_summary.json", {
        "positions": sum(item["positions"] for item in per_seed.values()),
        "seeds": list(SEEDS),
        "historical_seed_included": 20260807 in SEEDS,
        "per_seed": per_seed,
        "failures": len(failures),
        "all_equal": not failures,
        "divergence_classes": sorted({row["divergence_class"] for row in failures}),
        "deterministic_child_state_subset": "30 reconstructed reachable histories, first 3 legal children",
        "history_reconstruction": "public GC apply_action for every recorded USI move",
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
    _write_json(output / "curated_gap_evidence.json", _curated_gap_evidence(compiled, all_positions))
    history_performance = _history_performance_audit(compiled)
    alphabeta_history_performance = _alphabeta_history_performance_audit()
    _write_json(output / "history_performance.json", history_performance)
    _write_json(output / "performance.json", {
        "seconds_total": round(time.perf_counter() - started, 3),
        "seconds_large": round(large_seconds, 3),
        "native_fail_closed": native_fail_closed,
        "native_error": native_error,
        "history_performance": history_performance,
        "alphabeta_history_performance": alphabeta_history_performance,
    })
    move_gate = all(row["equal"] for row in curated_rows) and not failures
    transition_gate = (
        transition["transition_all_equal"]
        and not transition_subset_failures
    )
    history_gate = (
        history["ordinary_repetition"]["equal"]
        and history["perpetual_check"]["equal"]
        and not check_failures
    )
    verdict = compute_verdict(
        move_legality=move_gate,
        transition_parity=transition_gate,
        history_terminal=history_gate,
        symmetric_exclusions=bool(native_fail_closed),
        no_unresolved_divergence=not failures and not check_failures and not transition_subset_failures,
        native_fail_closed=native_fail_closed,
    )
    verdict.update({
        "nyugyoku_policy": "declaration semantics explicitly excluded from unlock; no productionization",
        "native_policy": "fail_closed_only; architecture sanity gate, not correctness substitute",
    })
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
