"""F150: evolve material values on the calibrated F149 deep-opening race."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import f149_shogi_material_score_race_deep_openings as race
from scripts.f145_shogi_material_only_fitness_signal_diagnosis import diagnostic_vectors
from scripts.f144_shogi_material_only_arena_evolution import (
    GEN0_SEED,
    TYPE_IDS,
    _ordering_values,
    _sanity,
    _sha,
    _vector_record,
    gen0_vector,
    mutate_vectors,
)

ROOT = Path(__file__).resolve().parents[1]
DISCRIMINATION_SEED = 1_500_101
SCREENING_SEEDS = {1: 1_501_001, 2: 1_501_002}
PROMOTION_SEEDS = {1: 1_502_001, 2: 1_502_002}
DISCRIMINATION_TARGET_PAIRS = 12
SCREENING_TARGET_PAIRS = 4
PROMOTION_TARGET_PAIRS = 24
DISCRIMINATION_POOL_OPENINGS = 128
COMMON_POOL_OPENINGS = 128
PROMOTION_POOL_OPENINGS = 256


def _screen_shared(compiled, champion, mutants, ordering_values, seed, workers):
    pool = race.opening_corpus(compiled, seed, COMMON_POOL_OPENINGS)
    selected, maps, invalid = [], {i: {} for i in range(6)}, []
    for start in range(0, len(pool), SCREENING_TARGET_PAIRS):
        wave = pool[start:start + SCREENING_TARGET_PAIRS]
        if len(wave) < SCREENING_TARGET_PAIRS:
            break
        all_rows = []
        for index, mutant in enumerate(mutants):
            rows = race._run_wave(wave, champion, mutant, ordering_values, workers)
            all_rows.append(rows)
            maps[index].update({row["opening_id"]: row for row in rows})
        for offset, opening in enumerate(wave):
            rows = [candidate[offset] for candidate in all_rows]
            if all(row["valid"] for row in rows):
                selected.append(opening.final_position_key)
                if len(selected) == SCREENING_TARGET_PAIRS:
                    records = []
                    for index, mutant in enumerate(mutants):
                        chosen = [maps[index][identity] for identity in selected]
                        records.append({"mutant_index": index, "vector": _vector_record(mutant), "result": race.summarize({"rows": chosen, "attempts": chosen, "invalid_pairs": 0}, 1_503_000 + index), "rows": chosen})
                    return records, {"shared_opening_ids": selected, "shared_opening_target_plies": [next(o.target_plies for o in pool if o.final_position_key == identity) for identity in selected], "invalid_attempts": invalid, "pool_opening_count": len(pool)}
            else:
                invalid.extend({"mutant_index": index, "pair_index": row["pair_index"], "valid": row["valid"]} for index, row in enumerate(rows) if not row["valid"])
    raise RuntimeError("F150 common screening opening pool exhausted")


def _promotion(compiled, champion, child, ordering_values, seed, workers, generation):
    result = race.run_pairs(champion, child, race.opening_corpus(compiled, seed, PROMOTION_POOL_OPENINGS), ordering_values, workers, PROMOTION_TARGET_PAIRS)
    return result, race.summarize(result, 1_504_000 + generation)


def _base_result(compiled, ordering_values, gen0, workers):
    return {
        "schema": "F150_SHOGI_MATERIAL_SCORE_RACE_DEEP_OPENING_EVOLUTION_V1",
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "type_ids": list(TYPE_IDS),
        "score_race": {"threshold": 10, "capture_points": 1, "check_points": 1, "capture_plus_check_points": 2, "safety_max_plies": 512, "score_independent_of_material_values": True, "valid_outcomes": ["score_threshold", "score_tiebreak", "checkmate", "perpetual_check", "declaration", "resignation"]},
        "opening_contract": {"min_plies": 16, "max_plies": 32, "evaluator_neutral": True},
        "search": {"max_nodes": 1000, "max_depth": 12, "qdepth": [4, 8], "tt_max_entries": 250000, "tuning": "SearchTuning()", "fixed_ordering_values": ordering_values, "fixed_ordering_sha256": _sha(ordering_values), "process_workers": workers},
        "f149_calibration": {"deep_opening_score_race_calibrated": True, "attempted_pair_count": 11, "attempted_games": 22, "valid_pair_count": 8, "valid_games": 16, "invalid_games": 6, "threshold_winning_games": 4, "score_tiebreak_games": 12, "formal_core_decisive_games": 0, "scored_outcome_fraction": 16 / 22, "self_pair_mean": 0.5},
        "gen0": {"seed": GEN0_SEED, "vector": _vector_record(gen0), "sanity": _sanity(gen0)},
    }


def run(*, output: Path, workers=4):
    compiled = race._compile()
    ordering_values = _ordering_values(compiled)
    gen0 = gen0_vector(GEN0_SEED)
    expected = (250, 634, 1000, 3195, 433, 1155, 3613, 658, 1351, 1822, 2299, 856, 240)
    if tuple(gen0) != expected or tuple(diagnostic_vectors()["Gen0"]) != expected:
        raise RuntimeError("Gen0 vector parity failure")
    m140 = tuple(diagnostic_vectors()["M140"])
    discr_openings = race.opening_corpus(compiled, DISCRIMINATION_SEED, DISCRIMINATION_POOL_OPENINGS)
    discr_run = race.run_pairs(gen0, m140, discr_openings, ordering_values, workers, DISCRIMINATION_TARGET_PAIRS)
    discrimination = race.summarize(discr_run, 1_505_101)
    discrimination["non_0_5_pair_count"] = sum(score != 0.5 for score in discrimination["pair_scores"])
    discrimination["acceptance"] = discrimination["valid_pair_count"] == DISCRIMINATION_TARGET_PAIRS and discrimination["non_0_5_pair_count"] >= 3
    base = _base_result(compiled, ordering_values, gen0, workers)
    base.update({"m140_diagnostic": {"seed": 1_440_401, "sigma": 1.40, "vector": _vector_record(m140)}, "discrimination": discrimination, "discrimination_rows": discr_run["rows"], "discrimination_attempts": discr_run["attempts"], "discrimination_openings": [race._opening_record(opening) for opening in discr_openings]})
    if not discrimination["acceptance"]:
        base["classification"] = "DEEP_OPENING_SCORE_RACE_INSUFFICIENT_MATERIAL_DISCRIMINATION"
        base["generations"] = []
        base["source_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        base["git_sha"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        output.write_text(json.dumps(base, indent=2, sort_keys=True), encoding="utf-8")
        return base
    champion, generations = gen0, []
    for generation in (1, 2):
        mutants = mutate_vectors(champion, generation)
        screening, meta = _screen_shared(compiled, champion, mutants, ordering_values, SCREENING_SEEDS[generation], workers)
        selected = max(screening, key=lambda row: (row["result"]["mean_pair_score"], row["result"]["child_better_pairs"], -row["mutant_index"]))
        selected_vector = tuple(selected["vector"]["values"])
        promotion_run, promotion = _promotion(compiled, champion, selected_vector, ordering_values, PROMOTION_SEEDS[generation], workers, generation)
        passed = promotion["mean_pair_score"] > 0.5 and promotion["bootstrap_95_ci"][0] > 0.5
        generations.append({"generation": generation, "parent": _vector_record(champion), "mutants": screening, "screening_meta": meta, "selected_mutant_index": selected["mutant_index"], "selected": _vector_record(selected_vector), "promotion": promotion, "promotion_rows": promotion_run["rows"], "promotion_attempts": promotion_run["attempts"], "promoted": passed})
        if not passed:
            break
        champion = selected_vector
    base["classification"] = "MATERIAL_ONLY_SCORE_RACE_GEN1_DOES_NOT_BEAT_GEN0" if not generations or not generations[0]["promoted"] else "MATERIAL_ONLY_SCORE_RACE_GEN1_PASSES_GEN2_DOES_NOT_BEAT_GEN1" if len(generations) < 2 or not generations[1]["promoted"] else "MATERIAL_ONLY_SCORE_RACE_GEN1_GEN2_IMPROVEMENT_ESTABLISHED"
    base.update({"generations": generations, "final_champion": _vector_record(champion), "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()})
    output.write_text(json.dumps(base, indent=2, sort_keys=True), encoding="utf-8")
    return base


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    result = run(output=args.output, workers=args.workers)
    print(json.dumps({"classification": result["classification"], "generations": len(result.get("generations", ()))}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
