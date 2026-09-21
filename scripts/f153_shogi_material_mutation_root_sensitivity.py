"""F153 causal probe for material mutation-to-search root sensitivity.

This is deliberately a root-search diagnostic.  It does not run games, train,
change the evaluator, or change the production search stack.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.core.actions import action_to_dict

from scripts import f149_shogi_material_score_race_deep_openings as race
from scripts.f144_shogi_material_only_arena_evolution import (
    GEN0_SEED,
    MUTATION_BASE_SEED,
    TYPE_IDS,
    MaterialOnlyEvaluator,
    _ordering_values,
    _player,
    _vector_record,
    canonicalize_vector,
    gen0_vector,
    mutate_vectors,
)
from scripts.f151_shogi_material_paired_score_microprobe import root_probe


ROOT = Path(__file__).resolve().parents[1]
WORK_ORDER = "GENERICCHESS_F153_SHOGI_MATERIAL_MUTATION_ROOT_SENSITIVITY"
F151_SEED = 1_510_101
F151_SENSITIVE_INDICES = (0, 8)
NEW_POSITION_SEEDS = tuple(range(1_530_101, 1_530_111))
OPENING_MIN_PLIES = 16
OPENING_MAX_PLIES = 32
POSITION_LIMITS = (4, 8, 12)
MUTANT_COUNT = 6
SIGMAS = (0.35, 0.70, 1.40)
LEVERAGE_CHANGE_MINIMUM = 3
LEVERAGE_MUTANT_MINIMUM = 2
LEVERAGE_POSITION_MINIMUM = 2
EXTREME_VECTOR = (1000, 1000, 1000, 1000, 1000, 1000, 100000000, 1000, 1000, 1000, 1000, 1000, 1000)


def _canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value) -> str:
    return hashlib.sha256(_canonical_json(value).encode()).hexdigest()


def mutation_vectors_at_sigma(champion: tuple[int, ...], sigma: float) -> tuple[tuple[int, ...], ...]:
    """Reuse the six F144 Gaussian directions at a requested amplitude."""
    if sigma not in SIGMAS:
        raise ValueError("unsupported mutation sigma")
    result: list[tuple[int, ...]] = []
    used = {tuple(champion)}
    for candidate_index in range(MUTANT_COUNT):
        rng = random.Random(MUTATION_BASE_SEED + 100 + candidate_index)
        while True:
            candidate = canonicalize_vector(
                value * math.exp(sigma * rng.gauss(0.0, 1.0)) for value in champion
            )
            if candidate not in used:
                used.add(candidate)
                result.append(candidate)
                break
    return tuple(result)


def artificial_extreme_vector() -> tuple[int, ...]:
    """A test-only rook-pressure vector used as a positive-control witness."""
    return EXTREME_VECTOR


def _record_probe(probe: dict) -> dict:
    return {
        "best_action": probe["best_action"],
        "best_action_key": probe["best_action_key"],
        "score": probe["score"],
        "completed_depth": probe["completed_depth"],
        "nodes": probe["nodes"],
        "qnodes": probe["qnodes"],
    }


def _new_session(compiled, opening):
    from generic_chess.session.session import GameSession

    session = GameSession(compiled)
    for action in opening.actions:
        session.submit(action)
    return session


def _one_ply_material(compiled, opening, values, ordering_values) -> dict:
    """Measure only immediate legal successors from the root position."""
    evaluator = MaterialOnlyEvaluator(tuple(values), ordering_values)
    root = _new_session(compiled, opening)
    root_side = root.state.position.side_to_move
    rows = []
    for action in root.legal_actions():
        child = _new_session(compiled, opening)
        child.submit(action)
        score = evaluator.evaluate(child.state)
        if child.state.position.side_to_move != root_side:
            score = -score
        rows.append((score, _canonical_json(action_to_dict(action)), action_to_dict(action)))
    rows.sort(key=lambda row: (-row[0], row[1]))
    best_score = rows[0][0] if rows else None
    margin = None if len(rows) < 2 else rows[0][0] - rows[1][0]
    return {
        "best_action": rows[0][2] if rows else None,
        "best_action_key": rows[0][1] if rows else None,
        "top2_material_margin": margin,
        "legal_successor_count": len(rows),
    }


def _position_rows(compiled, count: int = 4) -> list[dict]:
    if count not in POSITION_LIMITS:
        raise ValueError("position count must be one of the bounded probe limits")
    f151 = race.opening_corpus(compiled, F151_SEED, 32)
    by_index = {opening.index: opening for opening in f151}
    positions = []
    for index in F151_SENSITIVE_INDICES:
        opening = by_index[index]
        positions.append({"source": "F151", "seed": F151_SEED, "index": index, "opening": opening})
    for seed in NEW_POSITION_SEEDS[: count - len(F151_SENSITIVE_INDICES)]:
        opening = race.opening_corpus(compiled, seed, 1)[0]
        positions.append({"source": "new_fixed_seed", "seed": seed, "index": opening.index, "opening": opening})
    for item in positions:
        opening = item["opening"]
        if not OPENING_MIN_PLIES <= len(opening.actions) <= OPENING_MAX_PLIES:
            raise AssertionError("opening violates F149/F151 ply contract")
    return positions


def _position_record(item: dict) -> dict:
    opening = item["opening"]
    return {
        "source": item["source"],
        "seed": item["seed"],
        "opening_index": item["index"],
        "opening_id": opening.final_position_key,
        "actual_plies": len(opening.actions),
        "target_plies": opening.target_plies,
    }


def _stage(compiled, positions: list[dict], values_by_label: list[tuple[str, tuple[int, ...]]], ordering_values, include_static: bool = True) -> list[dict]:
    rows = []
    for item in positions:
        position = _position_record(item)
        opening = item["opening"]
        root_rows = []
        static_rows = []
        for label, values in values_by_label:
            probe = root_probe(compiled, opening, values, ordering_values)
            root_rows.append({"label": label, "vector_sha256": _sha(values), "search": _record_probe(probe)})
            if include_static:
                static = _one_ply_material(compiled, opening, values, ordering_values)
                static_rows.append({"label": label, "vector_sha256": _sha(values), "material": static})
        baseline = root_rows[0]["search"]["best_action_key"]
        for row in root_rows:
            row["action_differs_from_gen0"] = row["search"]["best_action_key"] != baseline
        if static_rows:
            static_baseline = static_rows[0]["material"]["best_action_key"]
            for row in static_rows:
                row["best_action_differs_from_gen0"] = row["material"]["best_action_key"] != static_baseline
        rows.append({"position": position, "root_searches": root_rows, "one_ply_material": static_rows})
    return rows


def leverage_summary(rows: list[dict], mutant_labels: tuple[str, ...] = tuple(f"mutant_{i}" for i in range(MUTANT_COUNT))) -> dict:
    changed = [
        (row["position"]["opening_id"], root["label"])
        for row in rows
        for root in row["root_searches"][1:]
        if root["action_differs_from_gen0"]
    ]
    mutants = {label for _, label in changed}
    positions = {position for position, _ in changed}
    if len(changed) == 0:
        classification = "NO_LEVERAGE"
    elif len(changed) >= LEVERAGE_CHANGE_MINIMUM and len(mutants) >= LEVERAGE_MUTANT_MINIMUM and len(positions) >= LEVERAGE_POSITION_MINIMUM:
        classification = "SUFFICIENT_LEVERAGE"
    else:
        classification = "SPARSE_LEVERAGE"
    return {
        "classification": classification,
        "changed_mutant_position_count": len(changed),
        "changed_mutants": sorted(mutants),
        "changed_positions": sorted(positions),
        "changes": [{"opening_id": position, "mutant": mutant} for position, mutant in changed],
    }


def run(*, output: Path) -> dict:
    compiled = race._compile()
    ordering_values = _ordering_values(compiled)
    gen0 = tuple(gen0_vector(GEN0_SEED))
    expected_gen0 = (250, 634, 1000, 3195, 433, 1155, 3613, 658, 1351, 1822, 2299, 856, 240)
    if gen0 != expected_gen0:
        raise RuntimeError("Gen0 vector parity failure")
    f144_mutants = tuple(mutate_vectors(gen0, generation=1))
    sigma035 = mutation_vectors_at_sigma(gen0, 0.35)
    if sigma035 != f144_mutants:
        raise RuntimeError("sigma-0.35 mutation directions do not match F144")
    labels = [("Gen0", gen0)] + [(f"mutant_{i}", vector) for i, vector in enumerate(sigma035)]
    stage_results = []
    positions = None
    rows = None
    summary = None
    for position_limit in POSITION_LIMITS:
        positions = _position_rows(compiled, position_limit)
        rows = _stage(compiled, positions, labels, ordering_values, include_static=position_limit == POSITION_LIMITS[0])
        summary = leverage_summary(rows)
        stage_results.append({"sigma": 0.35, "position_limit": position_limit, "root_rows": rows, "leverage": summary})
        if summary["classification"] == "SUFFICIENT_LEVERAGE":
            break
    if summary["classification"] != "SUFFICIENT_LEVERAGE":
        for sigma in SIGMAS[1:]:
            sigma_vectors = mutation_vectors_at_sigma(gen0, sigma)
            sigma_labels = [("Gen0", gen0)] + [(f"mutant_{i}", vector) for i, vector in enumerate(sigma_vectors)]
            rows = _stage(compiled, positions, sigma_labels, ordering_values, include_static=False)
            summary = leverage_summary(rows)
            stage_results.append({"sigma": sigma, "position_limit": len(positions), "root_rows": rows, "leverage": summary})
            if summary["classification"] == "SUFFICIENT_LEVERAGE":
                break
    result = {
        "schema": "F153_SHOGI_MATERIAL_MUTATION_ROOT_SENSITIVITY_V1",
        "work_order": WORK_ORDER,
        "classification": summary["classification"],
        "diagnostic_type": "CAUSAL_DIAGNOSTIC",
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "type_ids": list(TYPE_IDS),
        "unknown": "whether the F144 sigma-0.35 mutation directions change fixed ABP root decisions",
        "full_games_needed": False,
        "search": {"max_nodes": 1000, "max_depth": 12, "qdepth": [4, 8], "tt_max_entries": 250000, "tuning": "SearchTuning()", "fresh_player_and_tt_per_search": True},
        "gen0": {"seed": GEN0_SEED, **_vector_record(gen0)},
        "mutations": [{"label": label, "sigma": 0.35, **_vector_record(vector)} for label, vector in labels[1:]],
        "positions": [_position_record(item) for item in positions],
        "root_rows": rows,
        "stages": stage_results,
        "leverage": summary,
        "stage_limits": list(POSITION_LIMITS),
        "new_position_seeds": list(NEW_POSITION_SEEDS),
        "no_games_or_heavy": True,
        "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    }
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(output=args.output)
    print(json.dumps({"classification": result["classification"], "leverage": result["leverage"], "positions": result["positions"]}, sort_keys=True))


if __name__ == "__main__":
    main()
