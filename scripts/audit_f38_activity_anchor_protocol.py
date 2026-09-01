"""Freeze the F38 independent holdout protocol and descriptor.

This is an audit-only replay of the already-frozen F30 R1 transcript.  It
selects the first eligible AlphaSho action per game without inspecting any
evaluator score or rank.  No external engine is invoked and no production
module is modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
FIXTURES = ROOT / "tests" / "fixtures"
MANIFEST = FIXTURES / "f38_activity_anchor_manifest.json"
DESCRIPTOR = FIXTURES / "f38_external_holdout_descriptor.json"

F30_PAIRED = FIXTURES / "f30r1_paired_match.json"
F37_DECOMPOSITION = FIXTURES / "f37_evaluator_v1_decomposition.json"
PRODUCT_AUTHORITY = "a389adc50ed42096874ee38f818584978468c6ac"
SHOGI_FINGERPRINT = "ac987c3ffe75d8fa885ba787c1aa7cf60e92205465bf056b12b2989674007635"

BOUND_FILES = {
    "h38a_protocol_script": "scripts/audit_f38_activity_anchor_protocol.py",
    "f37_first_pass_manifest": "tests/fixtures/f37_evaluator_reentry_manifest.json",
    "f37_decomposition": "tests/fixtures/f37_evaluator_v1_decomposition.json",
    "f37_ranks": "tests/fixtures/f37_evaluator_representation_ranks.json",
    "f37_search_shadow": "tests/fixtures/f37_evaluator_search_shadow.json",
    "f37_selection": "tests/fixtures/f37_evaluator_selection.json",
    "f37_r1_fixture": "tests/fixtures/f37r1_gate_recertification.json",
    "f37_first_pass_script": "scripts/audit_f37_evaluator_reentry.py",
    "f37_r1_script": "scripts/audit_f37r1_gate_recertification.py",
    "f36_selection": "tests/fixtures/f36_post_reserve_selection.json",
    "f30_r1_paired_match": "tests/fixtures/f30r1_paired_match.json",
    "f30_r1_fresh_reference": "tests/fixtures/f30r1_fresh_move_reference.json",
    "f25_ten_root_descriptor": "tests/fixtures/f25_standard_shogi_position_descriptors.json",
    "evaluator.py": "generic_chess/ai/evaluation/evaluator.py",
    "profile.py": "generic_chess/ai/evaluation/profile.py",
    "config.py": "generic_chess/ai/evaluation/config.py",
}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def sha_value(value: Any) -> str:
    return sha_bytes(canonical(value).encode("utf-8"))


def git_sha(ref: str) -> str:
    return subprocess.run(["git", "rev-parse", ref], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def _f37_excluded_states(compiled: Any) -> set[str]:
    from generic_chess.core.movegen import legal_actions
    from generic_chess.core.transition import apply_action
    from generic_chess.learning.shogi_rules import gc_to_sfen, sfen_to_gc_state
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset

    compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    excluded: set[str] = set()
    for root in load(F37_DECOMPOSITION)["full_v1"]["roots"].values():
        state = sfen_to_gc_state(compiled, root["sfen"])
        excluded.add(gc_to_sfen(state, compiled))
        for action in legal_actions(state, compiled):
            excluded.add(gc_to_sfen(apply_action(state, action, compiled), compiled))
    return excluded


def _initial_session(compiled: Any, starting_sfen: str) -> Any:
    from generic_chess.core.position import HistoryRecord
    from generic_chess.learning.shogi_rules import sfen_to_gc_state
    from generic_chess.session.session import GameSession

    seeded = sfen_to_gc_state(compiled, starting_sfen)
    state = replace(
        seeded,
        history=(HistoryRecord(seeded.repetition_counts[0][0], -1, "IMPORTED_HISTORY_PREFIX_UNAVAILABLE", False),),
    )
    session = GameSession(compiled)
    session._state = state
    session._search_history_witnesses = (state.position,)
    return session


def select_holdout() -> dict[str, Any]:
    from generic_chess.learning.shogi_rules import gc_action_to_usi, gc_to_sfen
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset

    compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    paired = load(F30_PAIRED)
    excluded = _f37_excluded_states(compiled)
    selected: list[dict[str, Any]] = []
    selected_hashes: set[str] = set()

    for game_index, game in enumerate(paired["games"]):
        session = _initial_session(compiled, game["starting_sfen"])
        choice = None
        for event_index, event in enumerate(game["events"]):
            if session.result.status.value != "ongoing":
                break
            legal = list(session.legal_actions())
            legal_by_usi = {
                gc_action_to_usi(action): action
                for action in legal
            }
            sfen = gc_to_sfen(session.state, compiled)
            state_hash = sha_bytes(sfen.encode("utf-8"))
            eligible = (
                event["engine"] == "AlphaSho"
                and event["choice_kind"] == "ACTION"
                and event["submission_status"] == "submitted"
                and event["benchmark_ply"] >= 8
                and event["benchmark_ply"] <= 64
                and event["usi_or_declaration"] in legal_by_usi
                and sfen not in excluded
                and state_hash not in selected_hashes
            )
            if eligible and choice is None:
                choice = {
                    "game_index": game_index,
                    "game_id": game["position_id"],
                    "event_index": event_index,
                    "imported_root_id": game["position_id"],
                    "additional_ply": event["benchmark_ply"],
                    "canonical_state": sfen,
                    "canonical_state_sha256": state_hash,
                    "alphasho_played_move": event["usi_or_declaration"],
                    "transcript_provenance": {
                        "fixture": "tests/fixtures/f30r1_paired_match.json",
                        "game_index": game_index,
                        "position_id": game["position_id"],
                        "event_index": event_index,
                        "transcript_sha256": game["transcript_sha256"],
                    },
                    "legality_witness": {
                        "choice_kind": event["choice_kind"],
                        "legal": event["legal"],
                        "legal_action_count": len(legal),
                        "selected_move_in_legal_actions": True,
                        "legal_action_set_sha256": sha_value(sorted(legal_by_usi)),
                    },
                }
                selected.append(choice)
                selected_hashes.add(state_hash)
            action = legal_by_usi.get(event["usi_or_declaration"])
            if action is None or event["choice_kind"] != "ACTION":
                break
            session.submit(action)

    if len(selected) < 16 or len({row["canonical_state_sha256"] for row in selected}) < 16:
        raise AssertionError("F38 holdout minimum of 16 unique positions was not met")
    return {
        "schema_version": 1,
        "kind": "F38_EXTERNAL_HOLDOUT_DESCRIPTOR",
        "selection_protocol": {
            "source_fixture": "tests/fixtures/f30r1_paired_match.json",
            "source_game_count": 20,
            "selection_order": ["game order", "transcript event order"],
            "first_eligible_event_per_game": True,
            "eligible_engine": "AlphaSho",
            "eligible_choice_kind": "ACTION",
            "ongoing_only": True,
            "additional_ply_min": 8,
            "additional_ply_max": 64,
            "exclude_f37_roots_and_direct_children": True,
            "exclude_duplicate_canonical_states": True,
            "score_or_rank_inspection": False,
            "alphasho_execution": False,
        },
        "exclusions": {
            "f37_root_and_direct_child_state_count": len(excluded),
            "f37_decomposition_fixture": "tests/fixtures/f37_evaluator_v1_decomposition.json",
        },
        "holdout_unique_positions": len(selected),
        "positions": selected,
    }


def freeze() -> tuple[dict[str, Any], dict[str, Any]]:
    descriptor = select_holdout()
    DESCRIPTOR.write_text(json.dumps(descriptor, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    bound = {key: {"path": path, "sha256": sha_file(ROOT / path)} for key, path in BOUND_FILES.items()}
    manifest = {
        "schema_version": 1,
        "kind": "F38_ACTIVITY_ANCHOR_H38A_PROTOCOL_FREEZE",
        "current_sandbox_sha": git_sha("HEAD"),
        "origin_master_sha": git_sha("origin/master"),
        "product_authority": PRODUCT_AUTHORITY,
        "standard_shogi_fingerprint": SHOGI_FINGERPRINT,
        "production_change_policy": "zero files under generic_chess/",
        "selected_f37_candidate": "R37C",
        "no_tuning_from_results": True,
        "external_holdout_not_training_data": True,
        "production_diff_zero": subprocess.run(["git", "diff", "--quiet", "--", "generic_chess"], cwd=ROOT).returncode == 0,
        "bound_authority_files": bound,
        "holdout_descriptor": {"path": "tests/fixtures/f38_external_holdout_descriptor.json", "sha256": sha_file(DESCRIPTOR)},
        "holdout_minimum_unique_positions": 16,
        "holdout_unique_positions": descriptor["holdout_unique_positions"],
        "frozen_selection_fields": ["game_id", "event_index", "imported_root_id", "additional_ply", "canonical_state_sha256", "canonical_state", "alphasho_played_move", "transcript_provenance", "legality_witness"],
        "h38a_freeze_gates": {
            "protocol_frozen_before_candidate_scoring": True,
            "selection_uses_no_score_or_rank": True,
            "unique_holdout_minimum_met": descriptor["holdout_unique_positions"] >= 16,
            "f37_roots_and_direct_children_excluded": True,
            "production_diff_zero": True,
        },
    }
    manifest["manifest_sha256"] = sha_value(manifest)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest, descriptor


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    args = parser.parse_args(argv)
    if not args.freeze:
        parser.error("use --freeze")
    manifest, descriptor = freeze()
    print(json.dumps({"status": "PASS", "manifest_sha256": manifest["manifest_sha256"], "holdout_unique_positions": descriptor["holdout_unique_positions"], "descriptor_sha256": manifest["holdout_descriptor"]["sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
