"""Gate 2 R4: independent generated-ruleset mate-in-two policy witness."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_to_dict
from generic_chess.core.identity import position_identity_key
from generic_chess.core.position import GameState
from generic_chess.core.terminal import TerminalResult, TerminalStatus, terminal_result
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from scripts import f86q_check_forcing_depth3_probe as f86q
from scripts.f86f_ordinary_mate_capacity_census import _build_position
from scripts.f86n_transport_aware_signed_sampler import _load_json
from scripts.gate2_r1_rule_prior_forced_win_microbench import (
    ROOT,
    _decision,
    _digest_action,
    _profiles,
    _session_at,
)
from scripts.gate2_r2_selected_action_forced_win_check import _exact_forced_win
from scripts.gate2_r3_forced_win_horizon_disambiguation import _decision_depth3


SOURCE_SAMPLE = "V4-3"
SOURCE_TEMPLATE = "T0075"
SOURCE_FINGERPRINT = "856a810d3a21eec779f9ba8300ce602cd24d3e8850ba895e39579603fd4ff3e2"
MAX_CANDIDATES = 256


def _index(square, n):
    return square[1] * n + square[0]


def _load_source(root: Path):
    manifest = _load_json(root, "artifacts/f86n_r1_transport_aware_signed_sampler/manifest.json")
    entries = [row for row in manifest["entries"] if row["sample_id"] == SOURCE_SAMPLE]
    if len(entries) != 1:
        raise AssertionError("F86N V4-3 candidate is not unique")
    compiled = compile_ruleset(ruleset_from_dict(entries[0]["candidate_ruleset"]))
    if compiled.ruleset_fingerprint != SOURCE_FINGERPRINT:
        raise AssertionError("F86N V4-3 fingerprint drift")
    witness_payload = _load_json(root, "artifacts/f86s_f86n_r1_joint_witness_confinement/witnesses.json")
    witnesses = witness_payload["witnesses"]
    row = next(
        (item for item in witnesses if item["sample_id"] == SOURCE_SAMPLE),
        None,
    )
    if row is None or row["source_template_id"] != SOURCE_TEMPLATE:
        raise AssertionError("first F86S V4-3 witness drift")
    n = compiled.board_size
    defender = _index(row["defender_anchor"], n)
    attacker = _index(row["attacker_anchor_admissible_target_square"], n)
    placement = tuple((_item["type_id"], _index(_item["square"], n)) for _item in row["ordinary"])
    position = _build_position(compiled, defender, attacker, placement)
    if position_identity_key(position, compiled) is None:
        raise AssertionError("source witness identity unavailable")
    if not row["exact_checkmate_confinement"]["validated_exact_checkmate"]:
        raise AssertionError("F86S witness is not validated exact checkmate")
    if position.side_to_move != 1:
        raise AssertionError("source checkmate side drift")
    return compiled, position, row


def _fresh_state(position, compiled):
    from generic_chess.core.identity import position_identity_key as identity

    key = identity(position, compiled)
    state = GameState(
        position,
        0,
        ((key, 1),),
        TerminalResult(TerminalStatus.ONGOING),
    )
    return replace(state, terminal_status=terminal_result(state, compiled))


def _mate2_candidates(compiled, source_position):
    ordinary = sorted(
        (
            index,
            piece,
        )
        for index, piece in enumerate(source_position.board)
        if piece is not None and piece.owner == 0 and not compiled.types_by_id[piece.current_type_id].is_anchor
    )
    empty = [index for index, piece in enumerate(source_position.board) if piece is None]
    checked = 0
    for (first_index, first_piece), (second_index, second_piece) in combinations(ordinary, 2):
        for first_target, second_target in combinations(empty, 2):
            if checked >= MAX_CANDIDATES:
                return None, checked
            checked += 1
            board = list(source_position.board)
            board[first_index] = None
            board[second_index] = None
            board[first_target] = first_piece
            board[second_target] = second_piece
            candidate_position = replace(source_position, board=tuple(board), side_to_move=0)
            state = _fresh_state(candidate_position, compiled)
            if state.terminal_status.status is not TerminalStatus.ONGOING:
                continue
            successors = f86q._canonical_successors(state, compiled)
            if len(successors) < 2:
                continue
            ground_truth = []
            for action, _child in successors:
                row = _exact_forced_win(state, compiled, action)
                ground_truth.append(row)
            # R4 is a genuine mate-in-two predecessor: an immediate mate
            # would let production search terminate before the requested
            # depth-2 guidance comparison.
            if any(row["immediate_mate"] for row in ground_truth):
                continue
            forced = [row for row in ground_truth if row["forced_mate_within_3_plies"]]
            nonforced = [row for row in ground_truth if not row["forced_mate_within_3_plies"]]
            if forced and nonforced:
                return {
                    "state": state,
                    "witness": {
                        "root_position_digest": position_identity_key(state.position, compiled),
                        "legal_action_count": len(successors),
                        "forced_mate_action_digests": [row["action_digest"] for row in forced],
                        "forced_mate_action_count": len(forced),
                        "non_forced_action_count": len(nonforced),
                        "candidate_checks": checked,
                        "relocation": {
                            "first": {"type_id": first_piece.current_type_id, "from": first_index, "to": first_target},
                            "second": {"type_id": second_piece.current_type_id, "from": second_index, "to": second_target},
                        },
                    },
                }, checked
    return None, checked


def _search_row(decision, forced_digests):
    return {
        **decision,
        "selected_forced_mate_action": decision["action_digest"] in forced_digests,
    }


def run_gate2_r4(root: Path = ROOT):
    compiled, source_position, source_row = _load_source(root)
    source_state = _fresh_state(source_position, compiled)
    if source_state.terminal_status.status is not TerminalStatus.CHECKMATE:
        raise AssertionError("F86S source geometry is not exact checkmate")
    puzzle, candidate_checks = _mate2_candidates(compiled, source_position)
    if puzzle is None:
        return {
            "status": "PASS",
            "classification": "GATE2_R4_NO_BOUNDED_MATE2_PREDECESSOR",
            "source_ruleset_fingerprint": compiled.ruleset_fingerprint,
            "source_template_id": SOURCE_TEMPLATE,
            "candidate_checks": candidate_checks,
        }

    state = puzzle["state"]
    witness = puzzle["witness"]
    config, rule_profile, flat_profile, values = _profiles(compiled)
    if len(set(values[type_id] for type_id in values if type_id in {"P0", "P1"})) < 2:
        return {
            "status": "PASS",
            "classification": "GATE2_R4_NO_RULE_PRIOR_VALUE_CONTRAST",
            "source_ruleset_fingerprint": compiled.ruleset_fingerprint,
            "source_template_id": SOURCE_TEMPLATE,
            "witness": witness,
        }
    witnesses = (state.position,)

    # Exactly four fresh searches: rule/flat at depth 2, then rule/flat at 3.
    depth2 = {
        "rule_prior": _search_row(_decision(compiled, state, witnesses, config, rule_profile), set(witness["forced_mate_action_digests"])),
        "flat_control": _search_row(_decision(compiled, state, witnesses, config, flat_profile), set(witness["forced_mate_action_digests"])),
    }
    depth3 = {
        "rule_prior": _search_row(_decision_depth3(compiled, state, witnesses, config, rule_profile), set(witness["forced_mate_action_digests"])),
        "flat_control": _search_row(_decision_depth3(compiled, state, witnesses, config, flat_profile), set(witness["forced_mate_action_digests"])),
    }
    if not all(row["selected_forced_mate_action"] for row in depth3.values()):
        classification = "GATE2_R4_SOLVING_DEPTH_FAILURE"
    else:
        rule_guided = depth2["rule_prior"]["selected_forced_mate_action"]
        flat_guided = depth2["flat_control"]["selected_forced_mate_action"]
        if rule_guided and not flat_guided:
            classification = "RULE_PRIOR_SHALLOW_TACTICAL_GUIDANCE_SIGNAL"
        elif flat_guided and not rule_guided:
            classification = "RULE_PRIOR_SHALLOW_TACTICAL_COUNTEREXAMPLE"
        elif rule_guided and flat_guided:
            classification = "GATE2_R4_BOTH_GUIDED_TO_WINNING_ROUTE"
        else:
            classification = "GATE2_R4_NEITHER_GUIDED_TO_WINNING_ROUTE"
    return {
        "status": "PASS",
        "classification": classification,
        "source_ruleset_fingerprint": compiled.ruleset_fingerprint,
        "source_template_id": SOURCE_TEMPLATE,
        "source_validated_exact_checkmate": source_row["exact_checkmate_confinement"]["validated_exact_checkmate"],
        "witness": witness,
        "rule_prior_values": values,
        "depth_2": depth2,
        "depth_3": depth3,
        "compute": {"candidate_checks": candidate_checks, "depth_2_searches": 2, "depth_3_searches": 2},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_gate2_r4()
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
