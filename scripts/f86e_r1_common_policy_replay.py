"""F86E-R1 common-policy-tape causal replay."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import median
from typing import Any

from generic_chess.benchmark.minimal_generator import MinimalGeneratedGame
from generic_chess.benchmark.policy_tape import PolicyTape
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession


SAMPLES = ("V4-3", "V5-3")
CELLS = ("FULL8_CURRENT", "ORTHO4_CURRENT", "ORTHO4_HOME", "FULL8_HOME")
TAPE_SEEDS = {
    "V4-3": {"A": 8624301, "B": 8624302},
    "V5-3": {"A": 8625301, "B": 8625302},
}


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _load_json(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def build_tapes(sample_id: str, length: int = 32) -> dict[str, PolicyTape]:
    return {
        policy_id: PolicyTape.from_seed(policy_id, seed, length)
        for policy_id, seed in TAPE_SEEDS[sample_id].items()
    }


def _load_rulesets(root: Path) -> dict[str, dict[str, tuple[int, int, object]]]:
    f86c = _load_json(root, "artifacts/f86c_generator_viability/rulesets.json")
    frozen = {
        row["sample_id"]: (row["seed"], row["ordinary_count"], ruleset_from_dict(row["ruleset"]))
        for row in f86c["sample"]
        if row["sample_id"] in SAMPLES
    }
    result = {sample_id: {"LEGACY_CURRENT": values} for sample_id, values in frozen.items()}
    f86d = _load_json(root, "artifacts/f86d_mobility_ablation/counterfactual_rulesets.json")
    for row in f86d["rows"]:
        if row["sample_id"] in SAMPLES and row["profile"] == "A_FULL_ANCHOR":
            result[row["sample_id"]]["FULL8_CURRENT"] = (
                row["seed"],
                row["ordinary_count"],
                ruleset_from_dict(row["ruleset"]),
            )
    f86e = _load_json(root, "artifacts/f86e_anchor_placement_ablation/counterfactual_rulesets.json")
    for row in f86e["rows"]:
        if row["sample_id"] in SAMPLES and row["cell"] in ("ORTHO4_CURRENT", "ORTHO4_HOME", "FULL8_HOME"):
            result[row["sample_id"]][row["cell"]] = (
                row["seed"],
                row["ordinary_count"],
                ruleset_from_dict(row["ruleset"]),
            )
    return result


def _score(session: GameSession, player: int) -> float:
    if session.result.winner is None:
        return 0.5
    return 1.0 if session.result.winner == player else 0.0


def play_taped_game(compiled, tapes: dict[int, PolicyTape], seat_assignment: tuple[str, str], max_ply: int = 32) -> dict[str, Any]:
    session = GameSession(compiled)
    consumed = {"A": 0, "B": 0}
    branchings: list[int] = []
    while session.result.status.value == "ongoing" and len(session.history) < max_ply:
        actions = session.legal_actions()
        if not actions:
            break
        branchings.append(len(actions))
        actor = session.state.position.side_to_move
        policy_id = seat_assignment[actor]
        move_index = consumed[policy_id]
        action = actions[tapes[actor].choose_index(move_index, len(actions))]
        consumed[policy_id] += 1
        session.submit(action)
    return {
        "seat_assignment": {"player0": seat_assignment[0], "player1": seat_assignment[1]},
        "plies": len(session.history),
        "terminal_status": session.result.status.value,
        "winner": session.result.winner,
        "first_player_score": _score(session, 0),
        "branching_sequence": branchings,
        "policy_move_counts": consumed,
    }


def _summarize(games: list[dict[str, Any]]) -> dict[str, Any]:
    terminal: dict[str, int] = {}
    lengths = []
    branchings = []
    for game in games:
        status = game["terminal_status"]
        terminal[status] = terminal.get(status, 0) + 1
        lengths.append(game["plies"])
        branchings.extend(game["branching_sequence"])
    total = len(games)
    return {
        "played_game_count": total,
        "decisive_fraction": terminal.get("checkmate", 0) / total if total else 0.0,
        "checkmate_count": terminal.get("checkmate", 0),
        "stalemate_fraction": terminal.get("stalemate", 0) / total if total else 0.0,
        "stalemate_count": terminal.get("stalemate", 0),
        "repetition_fraction": terminal.get("repetition", 0) / total if total else 0.0,
        "repetition_count": terminal.get("repetition", 0),
        "ongoing_at_32_fraction": terminal.get("ongoing", 0) / total if total else 0.0,
        "ongoing_at_32_count": terminal.get("ongoing", 0),
        "terminal_distribution": terminal,
        "median_game_length": float(median(lengths)) if lengths else None,
        "median_branching": float(median(branchings)) if branchings else None,
        "forced_move_fraction": sum(count == 1 for count in branchings) / len(branchings) if branchings else 0.0,
        "branching_collapse_fraction": sum(count <= 2 for count in branchings) / len(branchings) if branchings else 0.0,
    }


def _comparison(games: list[dict[str, Any]], left: str, right: str) -> dict[str, Any]:
    rows = []
    for sample_id in SAMPLES:
        left_rows = [row for row in games if row["sample_id"] == sample_id and row["cell"] == left]
        right_rows = [row for row in games if row["sample_id"] == sample_id and row["cell"] == right]
        by_seat_left = {tuple(row["seat_assignment"].values()): row for row in left_rows}
        by_seat_right = {tuple(row["seat_assignment"].values()): row for row in right_rows}
        for seat_assignment in sorted(set(by_seat_left) & set(by_seat_right)):
            a = by_seat_left[seat_assignment]
            b = by_seat_right[seat_assignment]
            rows.append({
                "sample_id": sample_id,
                "seat_assignment": {"player0": seat_assignment[0], "player1": seat_assignment[1]},
                "left_terminal_status": a["terminal_status"],
                "right_terminal_status": b["terminal_status"],
                "terminal_category_changed": a["terminal_status"] != b["terminal_status"],
                "left_plies": a["plies"],
                "right_plies": b["plies"],
                "plies_delta_right_minus_left": b["plies"] - a["plies"],
                "left_branching_count": len(a["branching_sequence"]),
                "right_branching_count": len(b["branching_sequence"]),
            })
    return {"left": left, "right": right, "pairs": rows}


def _route(by_cell: dict[str, dict[str, Any]], comparisons: dict[str, dict[str, Any]]) -> list[str]:
    routes: list[str] = []
    full8 = comparisons["ORTHO4_CURRENT_vs_FULL8_CURRENT"]
    full8_ok = True
    for sample_id in SAMPLES:
        left = [row for row in full8["pairs"] if row["sample_id"] == sample_id]
        if not left or not all(
            row["right_terminal_status"] == "ongoing" and row["left_terminal_status"] != "stalemate"
            for row in left
        ):
            full8_ok = False
    if full8_ok:
        routes.append("FULL8_ESCAPE_CAPACITY_TOO_HIGH")
    else:
        routes.append("FULL8_VS_ORTHO4_TERMINATION_EFFECT_UNRESOLVED")

    placement_consistent = True
    for name in ("ORTHO4_HOME_vs_ORTHO4_CURRENT", "FULL8_HOME_vs_FULL8_CURRENT"):
        pair_rows = comparisons[name]["pairs"]
        improved = [
            row
            for row in pair_rows
            if row["left_terminal_status"] != "stalemate"
            and row["right_terminal_status"] == "stalemate"
        ]
        worsened = [
            row
            for row in pair_rows
            if row["left_terminal_status"] == "stalemate"
            and row["right_terminal_status"] != "stalemate"
        ]
        if not pair_rows or not improved or worsened:
            placement_consistent = False
    if placement_consistent:
        routes.append("ANCHOR_PLACEMENT_INTERACTION_OBSERVED")
    else:
        routes.append("PLACEMENT_EFFECT_UNRESOLVED")

    reversible = [by_cell[cell] for cell in CELLS]
    if all(row["decisive_fraction"] == 0.0 for row in reversible):
        routes.append("MATE_CAPACITY_REMAINS_LIMITING")
    return routes


def run(output_dir: Path, root: Path) -> dict[str, Any]:
    frozen = _load_rulesets(root)
    tapes_payload = {
        "schema_version": 1,
        "algorithm": "python_random_mt19937_random_floor_index_v1",
        "length": 32,
        "samples": {
            sample_id: {
                policy_id: {
                    "seed": tape.seed,
                    "uniforms": list(tape.uniforms),
                }
                for policy_id, tape in build_tapes(sample_id).items()
            }
            for sample_id in SAMPLES
        },
    }
    _write_json(output_dir / "policy_tapes.json", tapes_payload)

    games: list[dict[str, Any]] = []
    fingerprints: dict[str, dict[str, str]] = {}
    for sample_id in SAMPLES:
        tapes = build_tapes(sample_id)
        fingerprints[sample_id] = {}
        for cell in CELLS:
            seed, ordinary_count, ruleset = frozen[sample_id][cell]
            compiled = compile_ruleset(ruleset)
            fingerprints[sample_id][cell] = compiled.ruleset_fingerprint
            game = MinimalGeneratedGame(seed, ruleset.board_size, ordinary_count, ruleset, compiled)
            for seat_assignment in (("A", "B"), ("B", "A")):
                raw = play_taped_game(
                    compiled,
                    {0: tapes[seat_assignment[0]], 1: tapes[seat_assignment[1]]},
                    seat_assignment,
                    max_ply=32,
                )
                games.append({
                    "sample_id": sample_id,
                    "cell": cell,
                    "policy_tape_seeds": TAPE_SEEDS[sample_id],
                    "policy_tape_algorithm": tapes_payload["algorithm"],
                    **raw,
                })

    by_cell = {
        cell: _summarize([row for row in games if row["cell"] == cell])
        for cell in CELLS
    }
    comparisons = {
        "ORTHO4_CURRENT_vs_FULL8_CURRENT": _comparison(games, "ORTHO4_CURRENT", "FULL8_CURRENT"),
        "ORTHO4_HOME_vs_ORTHO4_CURRENT": _comparison(games, "ORTHO4_HOME", "ORTHO4_CURRENT"),
        "FULL8_HOME_vs_FULL8_CURRENT": _comparison(games, "FULL8_HOME", "FULL8_CURRENT"),
    }
    results = {
        "schema_version": 1,
        "sample_ids": list(SAMPLES),
        "cell_names": list(CELLS),
        "ruleset_fingerprints": fingerprints,
        "policy_tape_algorithm": tapes_payload["algorithm"],
        "policy_tape_seeds": TAPE_SEEDS,
        "quality_games": games,
        "played_game_count": len(games),
        "new_tactical_probe_compute": 0,
        "by_cell": by_cell,
        "pairwise_comparisons": comparisons,
        "routing": _route(by_cell, comparisons),
        "default_generator_changed": False,
        "no_ruleset_replacement": True,
        "no_seed_replacement": True,
        "f85_actual_compute": 0,
    }
    _write_json(output_dir / "results.json", results)
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/f86e_r1_common_policy_replay"))
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    result = run(args.output_dir, args.root)
    print(json.dumps({key: result[key] for key in ("played_game_count", "new_tactical_probe_compute", "routing")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
