"""Resume only the missing role games of the pinned sigma-.70 screen."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import f149_shogi_material_score_race_deep_openings as race
from scripts import f153_sigma070_gen1_second_opening_candidate_screen as screen
from scripts import f158_shogi_sigma070_single_pair_diagnostic as bounded_game
from scripts.f144_shogi_material_only_arena_evolution import _ordering_values

ROOT = Path(__file__).resolve().parents[1]
BASE_SHA = "1edf185ddbc070503d0d9b3e700b190cfae821e4"
PRIOR_SCREEN_SHA = "8855dcde957ec5323bacefeebbb43eb6646df828"
PRIOR_RESULT_SHA256 = "AB6ED4846D88D0137B3A241B6CE58463A6359D3BC617C73659FE41FCA3D1B41A"
PRIOR_M4_OWNER0_SHA256 = "7E59E3D97A6676825DE7D52B003932CCD68EA30F5BD490572BA70A06E13D3580"
PRIOR_RUN_ID = "f153-sigma070-gen1-second-opening-candidate-449074eea58b"
PRIOR_OUTPUT = ROOT / ".generic_chess_flow/f153-sigma070-gen1-second-opening-candidate-output"
OPENING_ID = "7a426930f39a4c1d267dbbf3bb861ffa91c3fad3e7c9d1ff1e9698913a2a46ef"
MAX_GAME_SECONDS = 480
MAX_INTERNAL_SECONDS = 1_500
EXTERNAL_HARD_SECONDS = 1_800
MISSING_GAMES = ((4, 1), (5, 0), (5, 1))


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def resource_envelope() -> dict:
    return {
        "schema": "generic-chess-resource-envelope-v1",
        "envelope_id": "f153-sigma070-second-opening-resume-v1",
        "logical_cpu_count": 2,
        "intended_cpu_lanes": 1,
        "expected_wall_minutes": None,
        "hard_wall_minutes": 30,
        "expected_cpu_hours": None,
        "hard_cpu_hours": 1,
        "arena_pairs": 2,
        "maximum_games": 3,
        "maximum_nodes": 315_000,
        "maximum_plies": 384,
        "maximum_concurrent_games": 1,
        "stage_count": 1,
        "nodes_per_move": 1_000,
        "max_depth": 12,
        "qdepth": [4, 8],
        "tt_entries": 250_000,
        "opening_seed": 1_590_301,
        "opening_count": 1,
        "opening_id": OPENING_ID,
        "opening_plies": 23,
        "maximum_total_plies_per_game_including_opening": 128,
        "maximum_searched_plies_per_game": 105,
        "maximum_nodes_per_game": 105_000,
        "maximum_game_wall_seconds": MAX_GAME_SECONDS,
        "maximum_internal_wall_seconds": MAX_INTERNAL_SECONDS,
        "external_hard_wall_seconds": EXTERNAL_HARD_SECONDS,
        "purpose": (
            "Run exactly mutant4-owner1, mutant5-owner0, mutant5-owner1 on the "
            "preserved opening; no other game, replacement opening, Gen2, or promotion"
        ),
    }


def _read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"expected JSON object: {path}")
    return value


def _read_pinned_json(path: Path, expected_sha256: str) -> dict:
    payload = path.read_bytes()
    observed = hashlib.sha256(payload).hexdigest().upper()
    if observed != expected_sha256:
        raise AssertionError(f"pinned evidence digest mismatch: {path.name}")
    value = json.loads(payload.decode("utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"expected JSON object: {path}")
    return value


def _validate_pair(pair: dict, mutant_index: int, expected_score: float) -> None:
    if (pair.get("mutant_index") != mutant_index or pair.get("valid") is not True
            or pair.get("pair_score") != expected_score):
        raise AssertionError(f"preserved mutant {mutant_index} pair does not match Chat evidence")
    games = pair.get("games")
    if not isinstance(games, list) or len(games) != 2 or {g.get("child_owner") for g in games} != {0, 1}:
        raise AssertionError(f"preserved mutant {mutant_index} pair is not role-swapped")
    for game in games:
        if (game.get("valid") is not True or game.get("completed") is not True
                or game.get("opening_id") != OPENING_ID):
            raise AssertionError(f"preserved mutant {mutant_index} contains invalid game evidence")
        role_path = PRIOR_OUTPUT / f"mutant-{mutant_index}-owner-{game['child_owner']}.json"
        if _read_json(role_path) != game:
            raise AssertionError(f"preserved mutant {mutant_index} role file differs from pair evidence")
    pair_path = PRIOR_OUTPUT / f"mutant-{mutant_index}-pair.json"
    if _read_json(pair_path) != pair:
        raise AssertionError(f"preserved mutant {mutant_index} pair file differs from result evidence")


def validate_preserved_evidence() -> tuple[dict, dict, dict]:
    result = _read_pinned_json(PRIOR_OUTPUT / "result.json", PRIOR_RESULT_SHA256)
    if (result.get("git_sha") != PRIOR_SCREEN_SHA
            or result.get("classification") != "SIGMA070_GEN1_SECOND_OPENING_SCREEN_INCONCLUSIVE"
            or result.get("first_screen_result_sha256") != screen.FIRST_SCREEN_RESULT_SHA256):
        raise AssertionError("prior screen result is not the pinned failed run")
    opening = result.get("opening")
    if (not isinstance(opening, dict)
            or (opening.get("seed"), opening.get("opening_id"), opening.get("plies"))
            != (1_590_301, OPENING_ID, 23)
            or len(opening.get("actions", [])) != 23):
        raise AssertionError("prior screen opening identity/action record differs")
    pairs_by_id = {int(pair["mutant_index"]): pair for pair in result.get("pairs", [])}
    if set(pairs_by_id) != {0, 1}:
        raise AssertionError("prior result must preserve exactly complete pairs 0 and 1")
    _validate_pair(pairs_by_id[0], 0, 0.50)
    _validate_pair(pairs_by_id[1], 1, 0.75)

    m4_owner0 = _read_pinned_json(
        PRIOR_OUTPUT / "mutant-4-owner-0.json", PRIOR_M4_OWNER0_SHA256,
    )
    required_m4 = {
        "mutant_index": 4,
        "child_owner": 0,
        "valid": True,
        "completed": True,
        "child_game_score": 1.0,
        "mutant_points": 2,
        "gen0_points": 0,
        "plies": 128,
        "scored_plies": 105,
        "nodes": 105_000,
        "opening_id": OPENING_ID,
    }
    if any(m4_owner0.get(key) != expected for key, expected in required_m4.items()):
        raise AssertionError("preserved mutant 4 owner 0 evidence differs from Chat order")
    for mutant_index, owner in ((4, 1), (5, 0), (5, 1)):
        if (PRIOR_OUTPUT / f"mutant-{mutant_index}-owner-{owner}.json").exists():
            raise AssertionError(f"unexpected prior record for scheduled missing game {mutant_index}/{owner}")
    return result, pairs_by_id, m4_owner0


def _load_opening(payload: dict):
    return race.v2._opening_from_payload({
        "index": payload["index"],
        "opening_seed": payload["opening_seed"],
        "target_plies": payload["target_plies"],
        "actions": payload["actions"],
        "final_position_key": payload["opening_id"],
    })


def _assemble_pairs(prior_pairs: dict, m4_owner0: dict, resumed: dict) -> list[dict]:
    pairs = [prior_pairs[0], prior_pairs[1]]
    m4_games = [m4_owner0] + ([resumed[(4, 1)]] if (4, 1) in resumed else [])
    pairs.append(screen._pair_record(4, m4_games))
    m5_games = [resumed[key] for key in ((5, 0), (5, 1)) if key in resumed]
    if m5_games:
        pairs.append(screen._pair_record(5, m5_games))
    return pairs


def run(*, output_dir: Path) -> dict:
    started = time.monotonic()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    remote = subprocess.check_output(["git", "rev-parse", "origin/sandbox"], cwd=ROOT, text=True).strip()
    parent = subprocess.check_output(["git", "rev-parse", "HEAD^"], cwd=ROOT, text=True).strip()
    if head != remote or parent != BASE_SHA:
        raise AssertionError("resume requires a published checkpoint directly based on the Chat SHA")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite resumed evidence: {output_dir}")
    prior_result, prior_pairs, m4_owner0 = validate_preserved_evidence()
    envelope = resource_envelope()
    output_dir.mkdir(parents=True, exist_ok=True)
    _atomic_json(output_dir / "resource-envelope.json", envelope)

    compiled = race._compile()
    opening = _load_opening(prior_result["opening"])
    if len(opening.actions) != envelope["opening_plies"] or opening.final_position_key != OPENING_ID:
        raise AssertionError("reconstructed opening differs from preserved opening identity")
    gen0, mutants = screen._vectors()
    ordering = _ordering_values(compiled)
    deadline = started + MAX_INTERNAL_SECONDS
    resumed: dict[tuple[int, int], dict] = {}
    stop_reason = None

    for mutant_index, owner in MISSING_GAMES:
        if time.monotonic() >= deadline:
            stop_reason = f"mutant_{mutant_index}_owner_{owner}_internal_wall_clock_cap_before_start"
            break
        raw = bounded_game.play_capped_game(
            compiled, opening, gen0, mutants[mutant_index], owner, ordering,
            deadline=deadline, game_timeout=MAX_GAME_SECONDS,
        )
        game = {
            "mutant_index": mutant_index,
            "child_owner": owner,
            "opening_id": opening.final_position_key,
            "opening_plies": len(opening.actions),
            **raw,
            "mutant_points": int(raw["scores"][owner]),
            "gen0_points": int(raw["scores"][1 - owner]),
            "mutant_capture_events": int(raw["capture_points"][owner]),
            "gen0_capture_events": int(raw["capture_points"][1 - owner]),
            "mutant_check_events": int(raw["check_points"][owner]),
            "gen0_check_events": int(raw["check_points"][1 - owner]),
            "child_game_score": race.v2.child_game_score(raw),
            "end_category": screen.first_screen._game_end_category(raw),
            "resource_envelope_compliant": None,
            "resource_bound_violations": None,
        }
        game_path = output_dir / f"mutant-{mutant_index}-owner-{owner}.json"
        _atomic_json(game_path, game)
        violations = screen._resource_bound_violations(game, envelope)
        game["resource_envelope_compliant"] = not violations
        game["resource_bound_violations"] = violations
        if violations:
            game["valid"] = False
            game["child_game_score"] = None
        _atomic_json(game_path, game)
        resumed[(mutant_index, owner)] = game
        stop_reason = screen._game_stop_reason(game, violations)

        pairs = _assemble_pairs(prior_pairs, m4_owner0, resumed)
        _atomic_json(output_dir / "result.json", {
            "schema": "F153_SIGMA070_GEN1_SECOND_OPENING_RESUME_V1",
            "diagnostic_type": "CAUSAL_DIAGNOSTIC",
            "source_screen_run_id": PRIOR_RUN_ID,
            "source_screen_sha": PRIOR_SCREEN_SHA,
            "git_sha": head,
            "opening": prior_result["opening"],
            "resource_envelope": envelope,
            "classification": "SIGMA070_GEN1_SECOND_OPENING_SCREEN_INCONCLUSIVE",
            "incomplete_reason": stop_reason or "resume_in_progress",
            "candidate_eligibility": "second_opening_pair_score > 0.5 and two_opening_mean_pair_score > 0.5",
            "pairs": pairs,
            "resumed_games_attempted": len(resumed),
        })
        if stop_reason:
            break

    pairs = _assemble_pairs(prior_pairs, m4_owner0, resumed)
    complete_valid = (len(pairs) == screen.MAX_PAIRS
                      and all(pair.get("valid") for pair in pairs))
    classification, candidate = screen._result_classification(pairs)
    if not complete_valid:
        classification, candidate = "SIGMA070_GEN1_SECOND_OPENING_SCREEN_INCONCLUSIVE", None
    games = [game for pair in pairs for game in pair["games"]]
    result = {
        "schema": "F153_SIGMA070_GEN1_SECOND_OPENING_RESUME_V1",
        "diagnostic_type": "CAUSAL_DIAGNOSTIC",
        "strength_or_promotion_evidence": False,
        "source_screen_run_id": PRIOR_RUN_ID,
        "source_screen_sha": PRIOR_SCREEN_SHA,
        "git_sha": head,
        "opening": prior_result["opening"],
        "resource_envelope": envelope,
        "classification": classification,
        "incomplete_reason": stop_reason or (None if complete_valid else "preserved_or_resumed_pair_incomplete_or_invalid"),
        "candidate_eligibility": "second_opening_pair_score > 0.5 and two_opening_mean_pair_score > 0.5",
        "pairs": pairs,
        "ranked_candidates": screen._rank_candidates(pairs) if complete_valid else [],
        "selected_candidate": candidate if complete_valid else None,
        "resumed_games_attempted": len(resumed),
        "resumed_games_completed_valid": sum(g.get("completed") is True and g.get("valid") is True for g in resumed.values()),
        "resumed_total_nodes": sum(g["nodes"] for g in resumed.values()),
        "elapsed_seconds": round(time.monotonic() - started, 6),
    }
    _atomic_json(output_dir / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run(output_dir=args.output_dir)
    print(json.dumps({
        "classification": result["classification"],
        "candidate": result["selected_candidate"],
        "resumed_games": result["resumed_games_attempted"],
        "pairs": len(result["pairs"]),
    }, sort_keys=True))
    return int(result["classification"] not in {
        "SIGMA070_GEN1_SECOND_OPENING_CANDIDATE_SELECTED",
        "SIGMA070_GEN1_SECOND_OPENING_NO_POSITIVE_CANDIDATE",
    })


if __name__ == "__main__":
    raise SystemExit(main())
