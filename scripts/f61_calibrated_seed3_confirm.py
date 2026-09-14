"""R27 fixed seed-59011 calibrated-child three-pair confirmation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.learning.arena import ArenaConfig, ArenaExecutionCaps, run_arena_game_resumable  # noqa: E402
from generic_chess.learning.nonlinear import CompactNonlinearResidual  # noqa: E402
from generic_chess.learning.openings import generate_arena_openings  # noqa: E402
from scripts import f50_generic_learnable_evaluator as f50  # noqa: E402
from scripts import f54_direct_capacity_and_gradient_geometry_diagnosis as f54  # noqa: E402
from scripts import f59_action_spectrum_diagnosis as f59  # noqa: E402
from scripts import f61_gen0_gen1_strength_triage as gen  # noqa: E402
from scripts import f61_pairwise_scale_calibration as cal  # noqa: E402
from scripts import f61_strength_first_triage as f61  # noqa: E402


RULESET = "B_CANONICAL_STANDARD_SHOGI"
PARENT_ID = "2c98cdd7c9e7b878decb15c2baf91b9d0150c65953e22481ce607d926ae43362"
EXPECTED_CHILD_ID = "eb3acd00eb74a268076301f58527b528b6befd500c037bddf5a44e2dab032368"
EXPECTED_MODEL_SHA = "a31fe98618519e2cf905302540f071cce48e7a3f9ab04775d8e11e00373f69ee"
TRAINING_SEED = 59011
ALPHA = 0.041187666769104674
PRIOR_PAIR_SCORES = [0.5]
OPENING_SEED = 620710
PAIRS = 3
OUT = ROOT / ".generic_chess_flow" / "f61-gen0-gen1-strength-triage" / "calibrated_seed3_confirm.json"


def _arena_caps() -> ArenaExecutionCaps:
    """Caps bound one R27 game to the approved resource envelope."""
    return ArenaExecutionCaps(
        per_game_wall_seconds=7200.0,
        per_game_nodes=400_000,
        per_game_plies=200,
        max_stage_games=6,
        max_concurrent_games=1,
        stage_wall_seconds=43_200.0,
        logical_cpu_count=2,
    )


def _reconstruct(compiled, parent):
    records = gen._d0_records(compiled, 620000, count=gen.ROOT_COUNT, smoke=False)
    original, training, roots, features, target_q = cal._fit_one_for_seed(compiled, parent, records, TRAINING_SEED, "PAIRWISE_RANKING")
    residual = CompactNonlinearResidual.from_dict(original.compact_nonlinear)
    prediction = residual.predict(features)
    calculated_alpha = float(np.dot(prediction, target_q - np.asarray([row.base_q for root in roots for row in root], dtype=float))) / float(np.dot(prediction, prediction))
    if not np.isclose(calculated_alpha, ALPHA, rtol=0.0, atol=1e-15):
        raise RuntimeError(f"fixed alpha mismatch: {calculated_alpha!r}")
    calibrated_model = CompactNonlinearResidual(**{**residual.__dict__, "output_weights": tuple(ALPHA * value for value in residual.output_weights), "output_bias": ALPHA * residual.output_bias})
    spec = {"candidate_id": "F61_D0_PAIRWISE_SEED_59011", "training_distribution": "D0_RANDOM_REACHABLE", "objective": "PAIRWISE_RANKING", "seed": TRAINING_SEED}
    child, payload = f61._candidate_checkpoint(parent, compiled, calibrated_model, spec)
    model_sha = f61.stable_sha256(payload)
    if child.checkpoint_id != EXPECTED_CHILD_ID or model_sha != EXPECTED_MODEL_SHA:
        raise RuntimeError(f"fixed calibrated child identity mismatch: {child.checkpoint_id} {model_sha}")
    return child, {"training": training, "calculated_alpha": calculated_alpha, "model_sha256": model_sha, "child_checkpoint_id": child.checkpoint_id}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-arena", action="store_true")
    args = parser.parse_args()
    compiled, native, _profile = f50._ruleset(RULESET)
    parent = f54._parent(RULESET)
    if parent.checkpoint_id != PARENT_ID:
        raise RuntimeError("unexpected parent checkpoint")
    child, identity = _reconstruct(compiled, parent)
    payload = {"schema": "generic-chess-f61-calibrated-seed3-confirm-v1", "ruleset": RULESET, "parent_checkpoint_id": parent.checkpoint_id, "fixed_candidate": identity, "prior_r15": {"opening_seed": 620705, "pair_scores": PRIOR_PAIR_SCORES, "mean_pair_score": 0.5, "child_better_pairs": 0, "tied_pairs": 1, "child_worse_pairs": 0, "game_wins": 1, "game_draws": 0, "game_losses": 1}}
    if args.run_arena:
        openings = generate_arena_openings(compiled, count=PAIRS, seed=OPENING_SEED, min_plies=2, max_plies=6)
        result = run_arena_game_resumable(compiled, native, parent, child, ArenaConfig(pairs=PAIRS, nodes_per_move=2_000, max_depth=12, tt_megabytes=8, opening_seed=OPENING_SEED, opening_count=PAIRS, min_plies=2, max_plies=6, workers=1), progress_dir=OUT.parent / "arena-progress-calibrated-seed3-r27b" / str(compiled.ruleset_fingerprint) / f"seed-{OPENING_SEED}", openings=openings, execution_caps=_arena_caps(), stop_on_decision=False)
        if result.status != "COMPLETE" or result.summary is None:
            raise RuntimeError(f"Arena incomplete: {result.status} {result.reason}")
        summary = result.summary
        new_scores = list(summary.pair_scores)
        combined = PRIOR_PAIR_SCORES + new_scores
        better = sum(score > 0.5 for score in combined)
        tied = sum(score == 0.5 for score in combined)
        worse = sum(score < 0.5 for score in combined)
        combined_mean = float(np.mean(combined))
        if combined_mean > 0.5 and better > worse:
            decision = "PROVISIONAL_INDEPENDENT_OPTIMIZER_SEED_REPRODUCTION_SUCCESS"
        elif combined_mean < 0.5 and worse > better:
            decision = "DIRECTIONAL_REPLICATION_FAILURE"
        else:
            decision = "INCONCLUSIVE"
        payload["new_block"] = {"opening_seed": OPENING_SEED, "pair_scores": new_scores, "mean_pair_score": summary.mean_pair_score, "child_better_pairs": summary.child_better_pairs, "tied_pairs": summary.tied_pairs, "child_worse_pairs": summary.child_worse_pairs, "game_wins": summary.game_wins, "game_draws": summary.game_draws, "game_losses": summary.game_losses}
        payload["combined_four_pair"] = {"pair_scores": combined, "mean_pair_score": combined_mean, "child_better_pairs": better, "tied_pairs": tied, "child_worse_pairs": worse, "game_wins": 1 + summary.game_wins, "game_draws": summary.game_draws, "game_losses": 1 + summary.game_losses, "decision": decision}
    else:
        payload["decision"] = "IDENTITY_VERIFIED_ARENA_PENDING"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=lambda value: value.item() if isinstance(value, np.generic) else str(value)) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=lambda value: value.item() if isinstance(value, np.generic) else str(value)))


if __name__ == "__main__":
    main()
