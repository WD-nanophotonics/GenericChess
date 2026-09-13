"""F61 fixed-root Standard-Shogi candidate reconstruction and screen.

The script reconstructs the requested optimizer-seed model and 24 persisted roots,
fits the requested F61 objective, optionally applies the exact R11 no-intercept
scalar intervention, checks the four frozen openings, and (only with
``--run-arena``) runs a fresh Arena for the candidate.  No hidden weights, data,
parent evaluator, or search budget are changed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.ai.limits import SearchLimits  # noqa: E402
from generic_chess.learning.arena import ArenaConfig, run_arena_game_resumable  # noqa: E402
from generic_chess.learning.nonlinear import CompactNonlinearResidual  # noqa: E402
from generic_chess.learning.openings import generate_arena_openings  # noqa: E402
from generic_chess.native.semantic_engine import SemanticSearchEngine  # noqa: E402
from scripts import f59_action_spectrum_diagnosis as f59  # noqa: E402
from scripts import f61_gen0_gen1_strength_triage as gen  # noqa: E402
from scripts import f61_strength_first_triage as f61  # noqa: E402


RULESET = "B_CANONICAL_STANDARD_SHOGI"
TRAINING_SEED = 59012
OPENING_SEED = 620700
FRESH_ARENA_SEED = 620701
PAIRS = 4
NODES = 2_000
DEPTH = 12
TT_MB = 8
TOLERANCE = 1e-9
OUT = ROOT / ".generic_chess_flow" / "f61-gen0-gen1-strength-triage" / "pairwise_scale_calibration.json"


def _rms(values: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(values))))


def _stats(values: np.ndarray) -> dict[str, float]:
    return {
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "mean": float(np.mean(values)),
        "std": float(np.std(values)),
        "rms": _rms(values),
    }


def _action_text(action: dict | None) -> str:
    if action is None:
        return "none"
    return f"{action.get('actor_type_id')} {tuple(action['from'])}->{tuple(action['to'])}"


def _search_triplet(compiled, native, parent, original, calibrated, openings) -> list[dict]:
    rows = []
    for opening in openings.openings:
        record = {"action_history": [f59.action_to_dict(action) for action in opening.actions]}
        session = f59._session(compiled, record)
        results = []
        for checkpoint in (parent, original, calibrated):
            result = SemanticSearchEngine(
                compiled, native, checkpoint=checkpoint, tt_megabytes=TT_MB
            ).search(session, SearchLimits(max_depth=DEPTH, max_nodes=NODES, quiescence_max_depth=0))
            results.append({
                "action": None if result.action is None else f59.action_to_dict(result.action),
                "score": int(result.score),
                "nodes": int(result.nodes),
            })
        rows.append({
            "opening_id": opening.final_position_key,
            "parent": results[0],
            "original_child": results[1],
            "calibrated_child": results[2],
            "original_changed": results[0]["action"] != results[1]["action"],
            "calibrated_changed": results[0]["action"] != results[2]["action"],
            "calibrated_vs_original_changed": results[1]["action"] != results[2]["action"],
        })
    return rows


def _arena_payload(summary) -> dict:
    return {
        "pair_count": summary.pair_count,
        "pair_scores": list(summary.pair_scores),
        "mean_pair_score": summary.mean_pair_score,
        "child_better_pairs": summary.child_better_pairs,
        "tied_pairs": summary.tied_pairs,
        "child_worse_pairs": summary.child_worse_pairs,
        "game_wins": summary.game_wins,
        "game_draws": summary.game_draws,
        "game_losses": summary.game_losses,
        "bootstrap_low": summary.bootstrap_low,
        "bootstrap_high": summary.bootstrap_high,
    }


def _fit_one_for_seed(
    compiled, parent, records: list[dict], training_seed: int,
    objective: str = "PAIRWISE_RANKING",
):
    """Fit a seed-specific child while keeping the persisted roots seed-bound.

    The root checkpoint metadata is intentionally loaded through the generator
    module unchanged (its data was produced under seed 59012).  Only the
    optimizer initialization seed is varied here, using the exact F61 fit and
    checkpoint construction paths.
    """
    roots = []
    for record in records:
        spectrum = gen._load_root_checkpoint(compiled, parent, record, smoke=False)
        if spectrum is None:
            raise RuntimeError("missing persisted root checkpoint")
        usable = [row for row in spectrum if row.q_20k is not None]
        if len(usable) >= 2:
            roots.append(usable)
    if not roots:
        raise RuntimeError("D0 produced no trainable action spectra")
    features = np.vstack([row.features for root in roots for row in root])
    base = np.asarray([row.base_q for root in roots for row in root], dtype=float)
    target = np.asarray([row.q_20k for root in roots for row in root], dtype=float)
    groups = []
    cursor = 0
    for root in roots:
        groups.append(np.arange(cursor, cursor + len(root)))
        cursor += len(root)
    model = f61._fit_serializable(
        features, base, target, groups, objective, training_seed
    )
    spec = {
        "candidate_id": f"F61_D0_{objective}_SEED_{training_seed}",
        "training_distribution": "D0_RANDOM_REACHABLE",
        "objective": objective,
        "seed": training_seed,
    }
    child, model_payload = f61._candidate_checkpoint(parent, compiled, model, spec)
    return child, {
        "training_seed": training_seed,
        "training_roots": len(roots),
        "training_actions": int(len(features)),
        "objective": objective,
        "model_width": f61.MODEL_WIDTH,
        "regularization": f61.MODEL_REGULARIZATION,
        "model_sha256": f61.stable_sha256(model_payload),
    }, roots, features, target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--training-seed", type=int, default=TRAINING_SEED)
    parser.add_argument(
        "--objective", choices=("PAIRWISE_RANKING", "POINTWISE_Q"),
        default="PAIRWISE_RANKING",
    )
    parser.add_argument("--run-arena", action="store_true")
    parser.add_argument("--fresh-arena-seed", type=int, default=FRESH_ARENA_SEED)
    parser.add_argument("--arena-pairs", type=int, default=PAIRS)
    args = parser.parse_args()
    if args.arena_pairs < 1 or args.arena_pairs > PAIRS:
        raise ValueError(f"arena-pairs must be in [1, {PAIRS}]")

    compiled, native, parent, _ = gen._context(RULESET)
    records = gen._d0_records(compiled, 620000, count=gen.ROOT_COUNT, smoke=False)
    original_child, training, roots, features, target_q = _fit_one_for_seed(
        compiled, parent, records, args.training_seed, args.objective
    )
    base = np.asarray([row.base_q for root in roots for row in root], dtype=float)
    target = target_q - base
    residual = CompactNonlinearResidual.from_dict(original_child.compact_nonlinear)
    prediction = residual.predict(features)
    if args.objective == "PAIRWISE_RANKING":
        denominator = float(np.dot(prediction, prediction))
        alpha = float(np.dot(prediction, target) / denominator) if denominator else float("nan")
        if not np.isfinite(alpha) or alpha <= 0.0 or abs(alpha) <= TOLERANCE:
            raise RuntimeError(f"invalid scalar calibration alpha={alpha!r}")
        calibrated_model = CompactNonlinearResidual(
            **{
                **residual.__dict__,
                "output_weights": tuple(float(alpha) * w for w in residual.output_weights),
                "output_bias": float(alpha * residual.output_bias),
            }
        )
        spec = {
            "candidate_id": f"F61_D0_{args.objective}_SEED_{args.training_seed}",
            "training_distribution": "D0_RANDOM_REACHABLE",
            "objective": args.objective,
            "seed": args.training_seed,
        }
        calibrated_child, calibrated_payload = f61._candidate_checkpoint(
            parent, compiled, calibrated_model, spec
        )
        calibrated_prediction = alpha * prediction
        actual_calibrated_prediction = CompactNonlinearResidual.from_dict(
            calibrated_payload
        ).predict(features)
        prediction_error = float(
            np.max(np.abs(actual_calibrated_prediction - calibrated_prediction))
        )
        if not np.allclose(
            actual_calibrated_prediction, calibrated_prediction,
            rtol=1e-12, atol=1e-9,
        ):
            raise RuntimeError(
                "calibrated prediction is not alpha*original prediction: "
                f"max_error={prediction_error}"
            )
        calibration_payload = {
            "alpha": alpha,
            "formula": "sum(prediction * target_residual) / sum(prediction**2)",
            "post_calibration_residual": _stats(calibrated_prediction),
            "actual_prediction_max_abs_error": prediction_error,
        }
    else:
        alpha = None
        calibrated_child = original_child
        calibrated_payload = original_child.compact_nonlinear
        calibrated_prediction = prediction
        prediction_error = None
        calibration_payload = {
            "alpha": None,
            "formula": "none (POINTWISE_Q directly fits absolute residual)",
            "post_calibration_residual": _stats(prediction),
            "actual_prediction_max_abs_error": None,
        }
    frozen_openings = generate_arena_openings(
        compiled, count=PAIRS, seed=OPENING_SEED, min_plies=2, max_plies=6
    )
    search_rows = _search_triplet(
        compiled, native, parent, original_child, calibrated_child, frozen_openings
    )
    if not any(row["calibrated_changed"] for row in search_rows):
        raise RuntimeError("calibrated child is behaviorally identical to parent on all openings")

    ranking_rows = []
    offset = 0
    concordant = 0
    comparable = 0
    for root_index, root in enumerate(roots):
        count = len(root)
        root_target = target[offset:offset + count]
        root_prediction = prediction[offset:offset + count]
        root_concordant = 0
        root_comparable = 0
        for left in range(count):
            for right in range(left + 1, count):
                delta = root_target[left] - root_target[right]
                if abs(delta) <= TOLERANCE:
                    continue
                root_comparable += 1
                comparable += 1
                if np.sign(delta) == np.sign(root_prediction[left] - root_prediction[right]):
                    root_concordant += 1
                    concordant += 1
        ranking_rows.append({
            "root_index": root_index,
            "comparable_pairs": root_comparable,
            "concordant_pairs": root_concordant,
            "agreement": (root_concordant / root_comparable) if root_comparable else None,
        })
        offset += count
    calibration_payload.update({
        "prediction_to_target_rms_ratio": _rms(prediction) / _rms(target),
        "prediction_to_target_std_ratio": float(np.std(prediction) / np.std(target)),
        "pearson_correlation": float(np.corrcoef(prediction, target)[0, 1]),
    })
    payload = {
        "schema": "generic-chess-f61-candidate-screen-v1",
        "ruleset": RULESET,
        "objective": args.objective,
        "training_seed": args.training_seed,
        "parent_checkpoint_id": parent.checkpoint_id,
        "original_child_checkpoint_id": original_child.checkpoint_id,
        "calibrated_child_checkpoint_id": calibrated_child.checkpoint_id,
        "original_model_sha256": f61.stable_sha256(original_child.compact_nonlinear),
        "calibrated_model_sha256": f61.stable_sha256(calibrated_payload),
        "training": training,
        "training_actions": int(len(target)),
        "target_residual": _stats(target),
        "learned_residual": _stats(prediction),
        "calibration": {
            **calibration_payload,
            "ranking_agreement": {
                "concordant_pairs": concordant,
                "comparable_pairs": comparable,
                "agreement": concordant / comparable if comparable else None,
                "by_root": ranking_rows,
            },
        },
        "frozen_opening_search": {
            "opening_seed": OPENING_SEED,
            "nodes": NODES,
            "max_depth": DEPTH,
            "tt_megabytes": TT_MB,
            "rows": search_rows,
        },
    }
    if args.run_arena:
        arena_pairs = args.arena_pairs
        fresh_openings = generate_arena_openings(
            compiled, count=arena_pairs, seed=args.fresh_arena_seed, min_plies=2, max_plies=6
        )
        resumable = run_arena_game_resumable(
            compiled, native, parent, calibrated_child,
            ArenaConfig(
                pairs=arena_pairs, nodes_per_move=NODES, max_depth=DEPTH,
                tt_megabytes=TT_MB, opening_seed=args.fresh_arena_seed,
                opening_count=arena_pairs, min_plies=2, max_plies=6, workers=1,
            ),
            progress_dir=(OUT.parent / "arena-progress-calibrated" / str(compiled.ruleset_fingerprint) / f"seed-{args.fresh_arena_seed}"),
            openings=fresh_openings,
            stop_on_decision=False,
        )
        if resumable.status != "COMPLETE" or resumable.summary is None:
            raise RuntimeError(f"calibrated Arena incomplete: {resumable.status} {resumable.reason}")
        payload["fresh_arena"] = {
            "opening_seed": args.fresh_arena_seed,
            "arena_pairs": arena_pairs,
            "nodes": NODES,
            "max_depth": DEPTH,
            "tt_megabytes": TT_MB,
            **_arena_payload(resumable.summary),
        }
        payload["fresh_arena"]["directional_failure"] = (
            payload["fresh_arena"]["mean_pair_score"] < 0.5
            and payload["fresh_arena"]["child_worse_pairs"] > payload["fresh_arena"]["child_better_pairs"]
        )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
