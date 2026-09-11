"""Run the fixed, cheap F86C minimal-generator viability probe."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from generic_chess.benchmark.game_quality import measure_game_quality
from generic_chess.benchmark.minimal_generator import generate_minimal_game
from generic_chess.rules.schema import ruleset_to_dict


SAMPLES = (
    ("V4-2", 4, 861401, 2),
    ("V4-3", 4, 861402, 3),
    ("V4-4", 4, 861403, 4),
    ("V4-5", 4, 861404, 5),
    ("V5-2", 5, 861501, 2),
    ("V5-3", 5, 861502, 3),
    ("V5-4", 5, 861503, 4),
    ("V5-5", 5, 861504, 5),
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def run(output_dir: Path) -> dict[str, object]:
    frozen_rows = []
    generated = []
    for sample_id, board_size, seed, ordinary_count in SAMPLES:
        row = {
            "sample_id": sample_id,
            "board_size": board_size,
            "seed": seed,
            "ordinary_count": ordinary_count,
        }
        try:
            game = generate_minimal_game(seed, board_size=board_size, ordinary_count=ordinary_count)
        except Exception as exc:  # the failure is durable and the seed is not replaced
            row.update({"generation_status": "GENERATION_FAILURE", "error": str(exc)})
            frozen_rows.append(row)
            continue
        row.update({
            "generation_status": "OK",
            "ruleset_fingerprint": game.ruleset_fingerprint,
            "ruleset": ruleset_to_dict(game.ruleset),
        })
        frozen_rows.append(row)
        generated.append((sample_id, game))
    _write_json(output_dir / "rulesets.json", {"schema_version": 1, "sample": frozen_rows})

    quality = []
    quality_games = []
    for sample_id, game in generated:
        raw_games: list[dict[str, object]] = []
        profile = measure_game_quality(
            game,
            trajectory_count=1,
            max_ply=32,
            seed=game.seed + 2000,
            raw_games=raw_games,
        )
        quality.append({"sample_id": sample_id, **profile.to_dict()})
        quality_games.extend({"sample_id": sample_id, **row} for row in raw_games)

    terminal = Counter(row["terminal_status"] for row in quality_games)
    winner_games = sum(row["winner"] is not None for row in quality_games)
    total_games = len(quality_games)
    results = {
        "schema_version": 1,
        "sample_ids": [sample_id for sample_id, _, _, _ in SAMPLES],
        "generated_ruleset_count": len(generated),
        "generation_failure_count": len(SAMPLES) - len(generated),
        "quality_pair_count": len(quality_games) // 2,
        "played_game_count": total_games,
        "quality_games": quality_games,
        "quality": quality,
        "terminal_distribution": dict(sorted(terminal.items())),
        "decisive_fraction": winner_games / total_games if total_games else 0.0,
        "stalemate_fraction": terminal["stalemate"] / total_games if total_games else 0.0,
        "repetition_fraction": terminal["repetition"] / total_games if total_games else 0.0,
        "max_ply_unresolved_fraction": terminal["ongoing"] / total_games if total_games else 0.0,
        "tactical_probe_position_count": len(quality),
        "tactical_probe_nodes": sum(row["tactical_probe_nodes"] for row in quality),
        "f85_actual_compute": 0,
        "routing": (
            "GENERATOR_DISTRIBUTION_STALEMATE_DOMINATED"
            if total_games and terminal["stalemate"] / total_games >= 0.75
            else "GENERATOR_VIABILITY_SUPPORTED"
            if winner_games / total_games >= 0.25
            else "VIABILITY_UNRESOLVED"
        ),
    }
    _write_json(output_dir / "results.json", results)
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/f86c_generator_viability"))
    args = parser.parse_args()
    result = run(args.output_dir)
    print(json.dumps({key: result[key] for key in (
        "generated_ruleset_count", "generation_failure_count", "played_game_count",
        "decisive_fraction", "stalemate_fraction", "tactical_probe_nodes", "routing",
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
