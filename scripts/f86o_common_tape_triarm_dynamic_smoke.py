"""F86O common-tape tri-arm dynamic smoke.

PREP freezes the six rulesets, four policy tapes, and every replay contract.
RESULT only deserializes that frozen manifest and plays the bounded smoke.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import replace
from pathlib import Path
from statistics import median
from typing import Any

from generic_chess.benchmark.game_quality import QualityObservation, profile_from_observations
from generic_chess.benchmark.policy_tape import PolicyTape
from generic_chess.core.actions import action_to_dict
from generic_chess.core.identity import position_identity_key
from generic_chess.core.movement import LeapAtom
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict, ruleset_to_dict
from generic_chess.session.session import GameSession


SAMPLES = ("V4-3", "V5-3")
ARMS = ("L", "F", "N")
MAX_PLY = 32
TAPE_ALGORITHM = "python_random_mt19937_random_floor_index_v1"
TAPE_SEEDS = {
    "V4-3": {"A": 8624301, "B": 8624302},
    "V5-3": {"A": 8625301, "B": 8625302},
}
EXPECTED_FINGERPRINTS = {
    "F": {
        "V4-3": "8ca58376a52e539c7c8519e902b8dd9e6991b002586d36d846a7a864fffea05d",
        "V5-3": "29390db6050d1ba482a393f7466608a6f19d0df9e6d4f7c3bd3a556f2d194fff",
    },
    "N": {
        "V4-3": "856a810d3a21eec779f9ba8300ce602cd24d3e8850ba895e39579603fd4ff3e2",
        "V5-3": "e8528688a64bce3f39231d9e4f38d5d200ade57c6f517ae33ce9b71b9f75ebe5",
    },
}


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _load_json(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _orthogonal_anchor_atoms() -> tuple[LeapAtom, ...]:
    return (LeapAtom((1, 0)), LeapAtom((-1, 0)), LeapAtom((0, 1)), LeapAtom((0, -1)))


def _arm_l_ruleset(source):
    piece_types = tuple(
        replace(piece_type, movement_atoms=_orthogonal_anchor_atoms())
        if piece_type.is_anchor
        else piece_type
        for piece_type in source.piece_types
    )
    return replace(source, piece_types=piece_types)


def _source_rows(root: Path) -> dict[str, dict[str, Any]]:
    payload = _load_json(root, "artifacts/f86c_generator_viability/rulesets.json")
    rows = {row["sample_id"]: row for row in payload["sample"]}
    if not set(SAMPLES).issubset(rows):
        raise RuntimeError("F86C source artifact does not contain the requested samples")
    return rows


def _frozen_candidate_rows(root: Path, relative: str) -> dict[str, dict[str, Any]]:
    payload = _load_json(root, relative)
    rows = {row["sample_id"]: row for row in payload["entries"]}
    if not set(SAMPLES).issubset(rows):
        raise RuntimeError(f"{relative} does not contain the requested samples")
    return rows


def _ruleset_entry(arm: str, sample_id: str, ruleset, source_seed: int, provenance: str) -> dict[str, Any]:
    compiled = compile_ruleset(ruleset)
    return {
        "arm": arm,
        "sample_id": sample_id,
        "board_size": ruleset.board_size,
        "source_seed": source_seed,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "ruleset": ruleset_to_dict(ruleset),
        "provenance": provenance,
    }


def _tape_payload() -> dict[str, Any]:
    return {
        sample_id: {
            policy_id: {
                "seed": seed,
                "uniforms": list(PolicyTape.from_seed(policy_id, seed, MAX_PLY).uniforms),
            }
            for policy_id, seed in TAPE_SEEDS[sample_id].items()
        }
        for sample_id in SAMPLES
    }


def build_manifest(root: Path, output_dir: Path) -> dict[str, Any]:
    source_rows = _source_rows(root)
    f86i = _frozen_candidate_rows(root, "artifacts/f86i_reversibility_rescue/manifest.json")
    f86n = _frozen_candidate_rows(root, "artifacts/f86n_r1_transport_aware_signed_sampler/manifest.json")
    rulesets: list[dict[str, Any]] = []
    for sample_id in SAMPLES:
        source_row = source_rows[sample_id]
        source = ruleset_from_dict(source_row["ruleset"])
        if compile_ruleset(source).ruleset_fingerprint != source_row["ruleset_fingerprint"]:
            raise RuntimeError(f"F86C source fingerprint mismatch for {sample_id}")
        rulesets.append(_ruleset_entry("L", sample_id, _arm_l_ruleset(source), source_row["seed"], "F86C source + ORTHO4 anchor"))

        full_reverse = ruleset_from_dict(f86i[sample_id]["candidate_ruleset"])
        if compile_ruleset(full_reverse).ruleset_fingerprint != EXPECTED_FINGERPRINTS["F"][sample_id]:
            raise RuntimeError(f"F86I frozen fingerprint mismatch for {sample_id}")
        rulesets.append(_ruleset_entry("F", sample_id, full_reverse, f86i[sample_id]["source_seed"], "F86I frozen candidate"))

        transport = ruleset_from_dict(f86n[sample_id]["candidate_ruleset"])
        if compile_ruleset(transport).ruleset_fingerprint != EXPECTED_FINGERPRINTS["N"][sample_id]:
            raise RuntimeError(f"F86N-R1 frozen fingerprint mismatch for {sample_id}")
        rulesets.append(_ruleset_entry("N", sample_id, transport, f86n[sample_id]["source_seed"], "F86N-R1 frozen candidate"))

    manifest = {
        "schema_version": 1,
        "status": "PRE_REGISTERED_F86O_COMMON_TAPE_TRIARM_DYNAMIC_SMOKE",
        "sample_ids": list(SAMPLES),
        "arms": list(ARMS),
        "rulesets": rulesets,
        "policy_tape_algorithm": TAPE_ALGORITHM,
        "policy_tape_length": MAX_PLY,
        "policy_tapes": _tape_payload(),
        "replay_contract": {
            "canonical_legal_action_ordering": "sorted canonical JSON action representation",
            "selection": "floor(u * legal_count)",
            "seat_assignments": [["A", "B"], ["B", "A"]],
            "terminal_labels": ["checkmate", "stalemate", "repetition", "ongoing@32"],
            "ongoing_is_not_draw": True,
            "pair_score_requires_both_games_terminal": True,
            "terminal_draw_score": [0.5, 0.5],
        },
        "dynamic_budget": {
            "real_games": 12,
            "games_per_arm_sample": 2,
            "max_ply": MAX_PLY,
        },
        "prohibited_compute": {
            "tactical_nodes": 0,
            "bfs_game_state_expansion": 0,
            "teacher_training": 0,
            "f85": 0,
        },
        "default_generator_changed": False,
        "result_driven_replacement_forbidden": True,
    }
    _write_json(output_dir / "manifest.json", manifest)
    return manifest


def _load_manifest(root: Path) -> dict[str, Any]:
    manifest = _load_json(root, "artifacts/f86o_common_tape_triarm_dynamic_smoke/manifest.json")
    if manifest["status"] != "PRE_REGISTERED_F86O_COMMON_TAPE_TRIARM_DYNAMIC_SMOKE":
        raise RuntimeError("F86O manifest is not the frozen PREP manifest")
    if manifest["dynamic_budget"] != {"games_per_arm_sample": 2, "max_ply": 32, "real_games": 12}:
        raise RuntimeError("F86O dynamic budget drift")
    if len(manifest["rulesets"]) != 6 or len(manifest["policy_tapes"]) != 2:
        raise RuntimeError("F86O frozen cohort is incomplete")
    return manifest


def _compiled_entries(manifest: dict[str, Any]) -> list[tuple[dict[str, Any], Any]]:
    compiled_entries = []
    seen = set()
    for row in manifest["rulesets"]:
        key = (row["arm"], row["sample_id"])
        if key in seen:
            raise RuntimeError(f"duplicate frozen ruleset {key}")
        seen.add(key)
        ruleset = ruleset_from_dict(row["ruleset"])
        compiled = compile_ruleset(ruleset)
        if compiled.ruleset_fingerprint != row["ruleset_fingerprint"]:
            raise RuntimeError(f"frozen ruleset fingerprint drift for {key}")
        compiled_entries.append((row, compiled))
    if seen != {(arm, sample_id) for arm in ARMS for sample_id in SAMPLES}:
        raise RuntimeError("F86O frozen ruleset cohort keys drifted")
    return compiled_entries


def _tapes(manifest: dict[str, Any]) -> dict[str, dict[str, PolicyTape]]:
    result = {}
    for sample_id in SAMPLES:
        result[sample_id] = {}
        for policy_id in ("A", "B"):
            data = manifest["policy_tapes"][sample_id][policy_id]
            if len(data["uniforms"]) != MAX_PLY or data["seed"] != TAPE_SEEDS[sample_id][policy_id]:
                raise RuntimeError(f"policy tape drift for {sample_id}/{policy_id}")
            expected = PolicyTape.from_seed(policy_id, data["seed"], MAX_PLY)
            if list(expected.uniforms) != data["uniforms"]:
                raise RuntimeError(f"policy tape payload mismatch for {sample_id}/{policy_id}")
            result[sample_id][policy_id] = PolicyTape(policy_id, data["seed"], tuple(data["uniforms"]))
    return result


def _canonical_actions(session: GameSession) -> list[Any]:
    return sorted(
        session.legal_actions(),
        key=lambda action: json.dumps(action_to_dict(action), sort_keys=True, separators=(",", ":")),
    )


def _play_game(compiled, tapes: dict[str, PolicyTape], seat_assignment: tuple[str, str]) -> dict[str, Any]:
    session = GameSession(compiled)
    consumed = {"A": 0, "B": 0}
    branching_counts: list[int] = []
    action_sequence: list[dict[str, Any]] = []
    while session.result.status.value == "ongoing" and len(session.history) < MAX_PLY:
        legal = _canonical_actions(session)
        if not legal:
            break
        branching_counts.append(len(legal))
        actor = session.state.position.side_to_move
        policy_id = seat_assignment[actor]
        tape_index = consumed[policy_id]
        if tape_index >= MAX_PLY:
            raise RuntimeError("policy tape exhausted before max ply")
        action_index = tapes[policy_id].choose_index(tape_index, len(legal))
        action = legal[action_index]
        action_sequence.append({"actor": actor, "action": action_to_dict(action), "legal_action_count": len(legal)})
        consumed[policy_id] += 1
        session.submit(action)
    terminal_status = session.result.status.value
    outcome_label = f"ongoing@{MAX_PLY}" if terminal_status == "ongoing" else terminal_status
    canonical_sequence = json.dumps(action_sequence, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "seat_assignment": {"player0": seat_assignment[0], "player1": seat_assignment[1]},
        "terminal_status": terminal_status,
        "outcome_label": outcome_label,
        "winner": session.result.winner,
        "plies": len(session.history),
        "branching_counts": branching_counts,
        "policy_move_counts": consumed,
        "action_sequence_sha256": hashlib.sha256(canonical_sequence).hexdigest(),
        "final_position_digest": position_identity_key(session.state.position, compiled),
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
    }


def _profile(games: list[dict[str, Any]]) -> dict[str, Any]:
    observations = [
        QualityObservation(tuple(game["branching_counts"]), game["plies"], game["terminal_status"])
        for game in games
    ]
    profile = profile_from_observations(observations, ruleset_fingerprint="F86O-triarm", board_size=0)
    return {
        "definition": "generic_chess.benchmark.game_quality.profile_from_observations",
        "trajectory_count": profile.trajectory_count,
        "trajectory_lengths": list(profile.trajectory_lengths),
        "median_branching": profile.median_branching,
        "p10_game_branching": profile.p10_game_branching,
        "p90_game_branching": profile.p90_game_branching,
        "forced_move_fraction": profile.forced_move_fraction,
        "low_branch_fraction": profile.low_branch_fraction,
        "branching_collapse_fraction": profile.branching_collapse_fraction,
        "median_game_length": profile.median_game_length,
        "p10_game_length": profile.p10_game_length,
        "p90_game_length": profile.p90_game_length,
        "terminal_distribution": dict(sorted(profile.terminal_distribution.items())),
    }


def _pair_summary(games: list[dict[str, Any]]) -> dict[str, Any]:
    first = next((game for game in games if game["seat_assignment"] == {"player0": "A", "player1": "B"}), None)
    second = next((game for game in games if game["seat_assignment"] == {"player0": "B", "player1": "A"}), None)
    pair = [first, second]
    complete = len(pair) == 2 and all(game is not None and game["terminal_status"] != "ongoing" for game in pair)
    if not complete:
        return {
            "scoreable": False,
            "first_player_score": None,
            "second_player_score": None,
            "incomplete_pair_is_unresolved": True,
        }
    scores = []
    for game in pair:
        if game["winner"] is None:
            scores.append((0.5, 0.5))
        else:
            scores.append((1.0 if game["winner"] == 0 else 0.0, 1.0 if game["winner"] == 1 else 0.0))
    return {
        "scoreable": True,
        "first_player_score": sum(score[0] for score in scores) / 2,
        "second_player_score": sum(score[1] for score in scores) / 2,
        "incomplete_pair_is_unresolved": True,
    }


def _arm_summary(games: list[dict[str, Any]], arm: str) -> dict[str, Any]:
    arm_games = [game for game in games if game["arm"] == arm]
    by_sample = {}
    pairs = {}
    for sample_id in SAMPLES:
        sample_games = [game for game in arm_games if game["sample_id"] == sample_id]
        labels = Counter(game["outcome_label"] for game in sample_games)
        by_sample[sample_id] = {
            "game_count": len(sample_games),
            "terminal_distribution": dict(sorted(labels.items())),
            "quality": _profile(sample_games),
        }
        pairs[sample_id] = _pair_summary(sample_games)
    labels = Counter(game["outcome_label"] for game in arm_games)
    return {
        "arm": arm,
        "game_count": len(arm_games),
        "terminal_distribution": dict(sorted(labels.items())),
        "by_sample": by_sample,
        "quality": _profile(arm_games),
        "paired_outcomes": pairs,
    }


def _dynamic_route(arm_games: list[dict[str, Any]]) -> str:
    labels = [game["outcome_label"] for game in arm_games]
    if len(labels) != 4:
        raise RuntimeError("ARM N routing requires four games")
    counts = Counter(labels)
    if counts["ongoing@32"] + counts["repetition"] == 4:
        return "TRANSPORT_BACKBONE_DYNAMIC_NONTERMINATION_FAILURE"
    if counts["stalemate"] == 4:
        return "TRANSPORT_BACKBONE_DYNAMIC_STALEMATE_FAILURE"
    if counts["checkmate"] >= 1 and all(counts[label] < 3 for label in ("stalemate", "repetition", "ongoing@32")):
        return "TRANSPORT_BACKBONE_DYNAMIC_RESCUE_SIGNAL_OBSERVED"
    return "TRANSPORT_BACKBONE_DYNAMIC_TERMINATION_VIABILITY_UNRESOLVED"


def _comparison(games: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for sample_id in SAMPLES:
        by_arm = {arm: [game for game in games if game["arm"] == arm and game["sample_id"] == sample_id] for arm in ARMS}
        summary = {arm: _arm_summary(by_arm[arm], arm) for arm in ARMS}
        counts = {arm: summary[arm]["terminal_distribution"] for arm in ARMS}
        rows.append({
            "sample_id": sample_id,
            "arm_n_vs_legacy": {
                "stalemate_count_delta": counts["N"].get("stalemate", 0) - counts["L"].get("stalemate", 0),
                "median_length_delta": summary["N"]["quality"]["median_game_length"] - summary["L"]["quality"]["median_game_length"],
            },
            "arm_n_vs_full_reverse": {
                "ongoing_or_repetition_count_delta": (
                    counts["N"].get("ongoing@32", 0) + counts["N"].get("repetition", 0)
                    - counts["F"].get("ongoing@32", 0) - counts["F"].get("repetition", 0)
                ),
                "median_length_delta": summary["N"]["quality"]["median_game_length"] - summary["F"]["quality"]["median_game_length"],
            },
            "checkmate_count": {arm: counts[arm].get("checkmate", 0) for arm in ARMS},
            "branching_collapse_fraction": {arm: summary[arm]["quality"]["branching_collapse_fraction"] for arm in ARMS},
        })
    return {"by_sample": rows}


def run(root: Path, output_dir: Path) -> dict[str, Any]:
    manifest = _load_manifest(root)
    compiled_entries = _compiled_entries(manifest)
    tapes = _tapes(manifest)
    games = []
    for entry, compiled in compiled_entries:
        for seats in (("A", "B"), ("B", "A")):
            game = _play_game(compiled, tapes[entry["sample_id"]], seats)
            games.append({
                "arm": entry["arm"],
                "sample_id": entry["sample_id"],
                **game,
            })
    by_arm = {arm: _arm_summary(games, arm) for arm in ARMS}
    route = _dynamic_route([game for game in games if game["arm"] == "N"])
    result = {
        "schema_version": 1,
        "status": "F86O_COMMON_TAPE_TRIARM_DYNAMIC_SMOKE_COMPLETE",
        "manifest": "artifacts/f86o_common_tape_triarm_dynamic_smoke/manifest.json",
        "manifest_result_driven_replacement_forbidden": manifest["result_driven_replacement_forbidden"],
        "ruleset_fingerprints": {row["arm"] + "/" + row["sample_id"]: row["ruleset_fingerprint"] for row in manifest["rulesets"]},
        "policy_tape_algorithm": manifest["policy_tape_algorithm"],
        "policy_tape_seeds": TAPE_SEEDS,
        "real_games": len(games),
        "max_ply": MAX_PLY,
        "games": games,
        "by_arm": by_arm,
        "comparisons": _comparison(games),
        "routing": {
            "dynamic": [route],
            "overall": [route],
        },
        "incomplete_pairs_are_unresolved": True,
        "tactical_nodes": 0,
        "bfs_expansions": 0,
        "teacher_training_compute": 0,
        "f85_actual_compute": 0,
        "default_generator_changed": False,
    }
    _write_json(output_dir / "summary.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/f86o_common_tape_triarm_dynamic_smoke"))
    parser.add_argument("--prep", action="store_true")
    args = parser.parse_args()
    result = build_manifest(args.root, args.output_dir) if args.prep else run(args.root, args.output_dir)
    print(json.dumps({
        "status": result["status"],
        "real_games": result.get("dynamic_budget", {}).get("real_games", result.get("real_games", 0)),
        "routing": result.get("routing"),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
