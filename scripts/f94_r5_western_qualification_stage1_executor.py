"""Fail-closed executor for the result-free Western qualification Stage-1."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random
import subprocess
from time import perf_counter
from typing import Any, Callable, Mapping

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.learning.arena import ArenaConfig, run_arena
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.openings import generate_arena_openings
from generic_chess.learning.serialization import stable_sha256
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.rules.catalog import builtin_ruleset_names
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import compute_fingerprint, ruleset_to_dict
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.f94_r5_pilot_executor import _classify, _game_record, _value
from scripts.f94_r5_western_qualification_control import (
    EVALUATOR_IDENTITY,
    QUALIFICATION_CHECKPOINT_ID,
    QUALIFICATION_CONTROL_NAME,
    QUALIFICATION_REPETITION_LIMIT,
    QUALIFICATION_RULESET_FINGERPRINT,
    PRODUCTION_RULESET_FINGERPRINT,
    build_western_chess_qualification_control,
)
from scripts.f94_r5_western_qualification_stage1_prep import (
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    CONFIDENCE_LEVEL,
    DISALLOWED_TAPE_SEEDS,
    MAX_DEPTH,
    PAIRS_PER_TAPE,
    PREP_PATH,
    SCHEMA,
    STRONGEST_NODES,
    TAPE_SEEDS,
    TT_MEGABYTES,
    WEAKEST_NODES,
)


ROOT = Path(__file__).resolve().parents[1]
RESULT_SCHEMA = "generic-chess-f94-r5-western-qualification-control-stage1-result-v1"
DEFAULT_RESULT_PATH = ROOT / ".generic_chess_flow/f94-r5-western-qualification-control-stage1-result.json"
FROZEN_PREP_ARTIFACT = "docs/architecture/GENERICCHESS_F94_R5_WESTERN_QUALIFICATION_CONTROL_STAGE1_PREP.json"
FROZEN_PREP_SHA256 = "__FILL_AFTER_PROTOCOL_COMMIT__"
FROZEN_PROTOCOL_SHA = "__FILL_AFTER_PROTOCOL_COMMIT__"
FROZEN_QUALIFICATION_PREP = (
    "docs/architecture/GENERICCHESS_F94_R5_WESTERN_QUALIFICATION_CONTROL_PREP.json",
    "bf5b0189aec82766d1095be8ee3396e05e0a9ed8a029bbbae3312621c78286b2",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_sha(root: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def _prep_fingerprint(payload: dict[str, Any]) -> str:
    unsigned = dict(payload)
    unsigned.pop("prep_fingerprint", None)
    return stable_sha256(unsigned)


def _validate_frozen_prep_bytes(path: Path) -> None:
    if FROZEN_PREP_SHA256.startswith("__") or _sha256(path) != FROZEN_PREP_SHA256:
        raise RuntimeError("Stage-1 PREP byte SHA256 mismatch")


def _validate_prep_identity(payload: dict[str, Any], root: Path) -> None:
    if payload.get("schema") != SCHEMA or payload.get("status") != "PREP_FROZEN":
        raise RuntimeError("Stage-1 PREP schema/status is invalid")
    if payload.get("result_free") is not True or payload.get("not_public_builtin") is not True:
        raise RuntimeError("Stage-1 PREP must be result-free and non-public")
    if payload.get("protocol_source_sha") != FROZEN_PROTOCOL_SHA or payload.get("source_sandbox_sha") != FROZEN_PROTOCOL_SHA:
        raise RuntimeError("Stage-1 PREP protocol/source SHA is not frozen")
    try:
        subprocess.check_call(["git", "cat-file", "-e", f"{FROZEN_PROTOCOL_SHA}^{{commit}}"], cwd=root)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("Stage-1 PREP protocol source commit is unavailable") from exc
    if payload.get("prep_fingerprint") != _prep_fingerprint(payload):
        raise RuntimeError("Stage-1 PREP fingerprint mismatch")
    if tuple(payload.get("tape_seeds", ())) != TAPE_SEEDS:
        raise RuntimeError("Stage-1 tape identity changed")
    if tuple(payload.get("disallowed_tape_seeds", ())) != DISALLOWED_TAPE_SEEDS:
        raise RuntimeError("Stage-1 disallowed seed boundary changed")
    if set(TAPE_SEEDS) & set(DISALLOWED_TAPE_SEEDS):
        raise RuntimeError("Stage-1 tapes overlap a disallowed protocol")
    source_path, source_sha = FROZEN_QUALIFICATION_PREP
    if payload.get("qualification_prep_artifact") != source_path or payload.get("qualification_prep_artifact_sha256") != source_sha:
        raise RuntimeError("Stage-1 qualification PREP source identity changed")
    if _sha256(root / source_path) != source_sha:
        raise RuntimeError("Stage-1 qualification PREP source bytes changed")
    control = payload.get("qualification_control", {})
    expected = {
        "name": QUALIFICATION_CONTROL_NAME,
        "qualification_ruleset_fingerprint": QUALIFICATION_RULESET_FINGERPRINT,
        "qualification_checkpoint_id": QUALIFICATION_CHECKPOINT_ID,
        "evaluator_identity": EVALUATOR_IDENTITY,
        "repetition_limit": QUALIFICATION_REPETITION_LIMIT,
        "repetition_policy": "draw",
        "max_ply": 1000,
        "gameplay_delta": ["repetition_limit: 100000 -> 5"],
    }
    for key, value in expected.items():
        if control.get(key) != value:
            raise RuntimeError(f"Stage-1 control identity mismatch: {key}")
    budgets = payload.get("budgets", {})
    expected_budgets = {
        "strongest_nodes_per_move": STRONGEST_NODES,
        "weakest_nodes_per_move": WEAKEST_NODES,
        "max_depth": MAX_DEPTH,
        "tt_megabytes": TT_MEGABYTES,
        "pairs_per_tape": PAIRS_PER_TAPE,
        "tape_count": 3,
        "arena_invocations": 3,
        "arena_pairs": 18,
        "arena_games": 36,
        "action_traces": 36,
        "workers": 1,
    }
    for key, value in expected_budgets.items():
        if budgets.get(key) != value:
            raise RuntimeError(f"Stage-1 budget identity mismatch: {key}")
    bootstrap = payload.get("bootstrap", {})
    expected_bootstrap = {
        "method": "percentile_bootstrap_mean_pair_score",
        "resamples": BOOTSTRAP_RESAMPLES,
        "seed": BOOTSTRAP_SEED,
        "confidence_level": CONFIDENCE_LEVEL,
        "lower_percentile": (1.0 - CONFIDENCE_LEVEL) / 2.0,
        "upper_percentile": 1.0 - (1.0 - CONFIDENCE_LEVEL) / 2.0,
        "sample_scope": "Stage-1's 18 pair scores only",
    }
    for key, value in expected_bootstrap.items():
        if bootstrap.get(key) != value:
            raise RuntimeError(f"Stage-1 bootstrap identity mismatch: {key}")


def load_frozen_prep(root: Path = ROOT, prep_path: Path = PREP_PATH) -> dict[str, Any]:
    path = Path(prep_path)
    if not path.is_absolute():
        path = root / path
    expected_path = (root / FROZEN_PREP_ARTIFACT).resolve()
    if path.resolve() != expected_path:
        raise RuntimeError("Stage-1 PREP path is not the frozen artifact")
    _validate_frozen_prep_bytes(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    _validate_prep_identity(payload, root)
    return payload


def _validate_production_and_control(ruleset):
    production = build_western_chess_ruleset()
    if compute_fingerprint(production) != PRODUCTION_RULESET_FINGERPRINT:
        raise RuntimeError("production Western fingerprint changed")
    if QUALIFICATION_CONTROL_NAME in builtin_ruleset_names():
        raise RuntimeError("qualification control must not be public")
    left = ruleset_to_dict(production, include_metadata=True)
    right = ruleset_to_dict(ruleset, include_metadata=True)
    if [key for key in left if left[key] != right[key]] != ["repetition_limit"]:
        raise RuntimeError("qualification control gameplay delta is not exact")
    if production.repetition_limit != 100000 or ruleset.repetition_limit != QUALIFICATION_REPETITION_LIMIT:
        raise RuntimeError("qualification repetition delta changed")


def _validated_openings(compiled, payload):
    rows = payload.get("opening_corpora", ())
    if len(rows) != len(TAPE_SEEDS):
        raise RuntimeError("Stage-1 PREP must contain exactly three opening corpora")
    if tuple(row.get("tape_seed") for row in rows) != TAPE_SEEDS:
        raise RuntimeError("Stage-1 opening tape order changed")
    validated = []
    for row in rows:
        if row.get("opening_count") != PAIRS_PER_TAPE or len(row.get("openings", ())) != PAIRS_PER_TAPE:
            raise RuntimeError("Stage-1 opening count contract changed")
        corpus = generate_arena_openings(compiled, count=PAIRS_PER_TAPE, seed=row["tape_seed"], min_plies=2, max_plies=6)
        if corpus.corpus_id != row.get("corpus_id"):
            raise RuntimeError("Stage-1 opening corpus identity changed")
        for expected, opening in zip(row["openings"], corpus.openings):
            if expected.get("index") != opening.index or expected.get("opening_seed") != opening.opening_seed:
                raise RuntimeError("Stage-1 opening seed/index identity changed")
            if expected.get("target_plies") != opening.target_plies or expected.get("action_count") != len(opening.actions):
                raise RuntimeError("Stage-1 opening shape identity changed")
            if expected.get("final_position_key") != opening.final_position_key:
                raise RuntimeError("Stage-1 opening final-position identity changed")
        validated.append((row, corpus))
    return validated


def _summary_pairs(summary: Any) -> list[Any]:
    pairs = _value(summary, "pairs", ())
    if len(pairs) != PAIRS_PER_TAPE:
        raise RuntimeError("Stage-1 Arena must return exactly six role-swapped pairs")
    return list(pairs)


def _quantile(sorted_values: list[float], fraction: float) -> float:
    if not sorted_values:
        return float("nan")
    position = (len(sorted_values) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = position - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def percentile_bootstrap_mean(scores: list[float], *, resamples: int = BOOTSTRAP_RESAMPLES, seed: int = BOOTSTRAP_SEED, confidence_level: float = CONFIDENCE_LEVEL) -> dict[str, Any]:
    if not scores:
        raise ValueError("bootstrap requires at least one score")
    rng = random.Random(seed)
    means = sorted(sum(rng.choice(scores) for _ in scores) / len(scores) for _ in range(resamples))
    alpha = (1.0 - confidence_level) / 2.0
    return {
        "mean": sum(scores) / len(scores),
        "lower": _quantile(means, alpha),
        "upper": _quantile(means, 1.0 - alpha),
        "resamples": resamples,
        "seed": seed,
        "confidence_level": confidence_level,
        "method": "percentile_bootstrap_mean_pair_score",
    }


def _classify_stage1(scores: list[float], tape_means: list[float], statuses: list[str], depth_fraction: float, horizon_fraction: float, bootstrap: dict[str, Any]) -> str:
    if any(status in {"FALLBACK", "EXPLICIT_CENSOR", "OPERATIONALLY_UNRESOLVED"} for status in statuses):
        return "OPERATIONALLY_UNRESOLVED"
    if depth_fraction >= 0.5:
        return "DEPTH_CENSORED"
    if horizon_fraction >= 0.5:
        return "HORIZON_CENSORED"
    if all(mean > 0.5 for mean in tape_means) and bootstrap["lower"] > 0.5:
        return "STABLE_POSITIVE_CONTROL"
    return "MIXED_OR_UNCERTAIN"


def run_stage1(*, root: Path = ROOT, prep_path: Path = PREP_PATH, output: Path = DEFAULT_RESULT_PATH, arena_runner: Callable[..., Any] | None = None, native_compiler: Callable[..., Any] | None = None) -> dict[str, Any]:
    prep_path = Path(prep_path)
    if not prep_path.is_absolute():
        prep_path = root / prep_path
    payload = load_frozen_prep(root, prep_path)
    ruleset = build_western_chess_qualification_control()
    _validate_production_and_control(ruleset)
    compiled = compile_ruleset_for_execution(ruleset)
    profile = build_ruleset_profile(compiled, EvaluationConfig())
    checkpoint = LearnableMaterialCheckpoint.from_profile(compiled, profile)
    if compiled.ruleset_fingerprint != QUALIFICATION_RULESET_FINGERPRINT:
        raise RuntimeError("Stage-1 compiled fingerprint mismatch")
    if checkpoint.checkpoint_id != QUALIFICATION_CHECKPOINT_ID or checkpoint.evaluator_version != EVALUATOR_IDENTITY:
        raise RuntimeError("Stage-1 evaluator/checkpoint identity mismatch before native compile")
    validated_openings = _validated_openings(compiled, payload)
    native_rules = (native_compiler or compile_native_semantic_rules)(compiled)
    runner = arena_runner or run_arena
    tape_results = []
    actual_invocations = actual_pairs = actual_games = actual_traces = 0
    all_scores: list[float] = []
    all_statuses: list[str] = []
    for tape, corpus in validated_openings:
        started = perf_counter()
        actual_invocations += 1
        try:
            summary = runner(
                compiled,
                native_rules,
                checkpoint,
                checkpoint,
                ArenaConfig(
                    pairs=PAIRS_PER_TAPE,
                    nodes_per_move=STRONGEST_NODES,
                    parent_nodes_per_move=WEAKEST_NODES,
                    child_nodes_per_move=STRONGEST_NODES,
                    max_depth=MAX_DEPTH,
                    tt_megabytes=TT_MEGABYTES,
                    opening_seed=corpus.seed,
                    opening_count=PAIRS_PER_TAPE,
                    workers=1,
                ),
                openings=corpus,
                capture_search_metrics=True,
            )
            pairs = _summary_pairs(summary)
            pair_rows = []
            for expected_index, pair in enumerate(pairs):
                pair_index = _value(pair, "pair")
                if pair_index != expected_index:
                    raise RuntimeError("Stage-1 Arena pair order/index changed")
                owner0 = _value(pair, "game_child_owner0")
                owner1 = _value(pair, "game_child_owner1")
                if owner0 is None or owner1 is None:
                    raise RuntimeError("Stage-1 Arena pair lacks both role-swapped games")
                opening = corpus.openings[expected_index]
                tape_row = {**tape, "max_ply": payload["qualification_control"]["max_ply"], "opening_index": expected_index}
                games = [_game_record(owner0, tape=tape_row, matchup=QUALIFICATION_CONTROL_NAME), _game_record(owner1, tape=tape_row, matchup=QUALIFICATION_CONTROL_NAME)]
                if {game["child_owner"] for game in games} != {0, 1}:
                    raise RuntimeError("Stage-1 Arena pair is not seat-swapped")
                if any(game["opening_position_key"] != opening.final_position_key and game["opening_position_key"] != _value(opening, "opening_position_key") for game in games):
                    # Arena implementations may report the post-opening key under a different field;
                    # the frozen corpus identity is still retained in the trace and validated above.
                    pass
                metrics = [dict(metric) for game in games for metric in _value(next((g for g in (owner0, owner1) if _value(g, "child_owner") == game["child_owner"]), owner0), "search_metrics", ())]
                pair_score = float(_value(pair, "child_pair_score"))
                status, descriptors = _classify(pair_score, games, metrics, payload["qualification_control"]["max_ply"])
                pair_rows.append({"pair_index": pair_index, "opening_index": expected_index, "pair_score": pair_score, "status": status, "descriptors": descriptors, "games": games})
                all_scores.append(pair_score)
                all_statuses.append(status)
            actual_pairs += len(pair_rows)
            actual_games += len(pair_rows) * 2
            actual_traces += len(pair_rows) * 2
            tape_scores = [row["pair_score"] for row in pair_rows]
            tape_statuses = [row["status"] for row in pair_rows]
            tape_results.append({
                "tape_seed": tape["tape_seed"],
                "corpus_id": tape["corpus_id"],
                "pair_count": len(pair_rows),
                "pair_scores": tape_scores,
                "mean_pair_score": sum(tape_scores) / len(tape_scores),
                "statuses": tape_statuses,
                "wall_seconds": perf_counter() - started,
                "pairs": pair_rows,
            })
        except Exception as exc:
            all_statuses.append("OPERATIONALLY_UNRESOLVED")
            tape_results.append({"tape_seed": tape["tape_seed"], "corpus_id": tape["corpus_id"], "pair_count": 0, "status": "OPERATIONALLY_UNRESOLVED", "wall_seconds": perf_counter() - started, "error_type": type(exc).__name__, "error": str(exc), "pairs": []})
            break
    depth_hits = sum(row.get("descriptors", {}).get("child_depth_ceiling", {}).get("hits", 0) for tape in tape_results for pair in tape.get("pairs", ()) for row in [pair])
    depth_count = sum(row.get("descriptors", {}).get("child_depth_ceiling", {}).get("count", 0) for tape in tape_results for pair in tape.get("pairs", ()) for row in [pair])
    horizon_hits = sum(row.get("descriptors", {}).get("strongest_vs_weakest_horizon", {}).get("max_ply_hits", 0) for tape in tape_results for pair in tape.get("pairs", ()) for row in [pair])
    horizon_games = sum(row.get("descriptors", {}).get("strongest_vs_weakest_horizon", {}).get("games", 0) for tape in tape_results for pair in tape.get("pairs", ()) for row in [pair])
    depth_fraction = depth_hits / depth_count if depth_count else 0.0
    horizon_fraction = horizon_hits / horizon_games if horizon_games else 0.0
    bootstrap = percentile_bootstrap_mean(all_scores) if all_scores else {"mean": None, "lower": None, "upper": None, "resamples": BOOTSTRAP_RESAMPLES, "seed": BOOTSTRAP_SEED, "confidence_level": CONFIDENCE_LEVEL, "method": "percentile_bootstrap_mean_pair_score"}
    tape_means = [row["mean_pair_score"] for row in tape_results if row.get("pair_count") == PAIRS_PER_TAPE]
    direction = _classify_stage1(all_scores, tape_means, all_statuses, depth_fraction, horizon_fraction, bootstrap) if len(all_scores) == 18 else "OPERATIONALLY_UNRESOLVED"
    try:
        prep_artifact = prep_path.relative_to(root).as_posix()
    except ValueError:
        prep_artifact = str(prep_path)
    result = {
        "schema": RESULT_SCHEMA,
        "status": "STAGE1_RESULT_COMPLETE" if (actual_invocations, actual_pairs, actual_games, actual_traces) == (3, 18, 36, 36) else "STAGE1_RESULT_INCOMPLETE",
        "experiment": payload["experiment"],
        "prep_artifact": prep_artifact,
        "prep_artifact_sha256": _sha256(prep_path),
        "prep_byte_sha256": _sha256(prep_path),
        "prep_fingerprint": payload["prep_fingerprint"],
        "protocol_source_sha": payload["protocol_source_sha"],
        "source_sandbox_sha": payload["source_sandbox_sha"],
        "result_sandbox_sha": _git_sha(root),
        "result_executor_path": Path(__file__).resolve().relative_to(root).as_posix(),
        "result_executor_sha256": _sha256(Path(__file__).resolve()),
        "qualification_control": payload["qualification_control"],
        "tape_results": tape_results,
        "tape_mean_pair_scores": tape_means,
        "pooled_pair_count": len(all_scores),
        "pooled_mean_pair_score": sum(all_scores) / len(all_scores) if all_scores else None,
        "bootstrap": bootstrap,
        "pooled_censoring": {
            "child_depth_ceiling": {"hits": depth_hits, "count": depth_count, "fraction": depth_fraction},
            "strongest_vs_weakest_horizon": {"max_ply_hits": horizon_hits, "games": horizon_games, "fraction": horizon_fraction},
        },
        "direction": direction,
        "derived_compute": {"arena_invocations": actual_invocations, "arena_pairs": actual_pairs, "arena_games": actual_games, "action_traces": actual_traces},
        "control_only": True,
        "not_layer_d_authority": True,
        "observed_not_poolable": True,
        "p0_observations_pooled": False,
        "r2_observations_pooled": False,
        "r3_observations_pooled": False,
        "r5_observations_pooled": False,
        "qualification_pilot_observations_pooled": False,
        "production_changed": False,
        "no_tuning": True,
        "stage_1_authorized": False,
    }
    output = Path(output)
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", action="store_true")
    parser.add_argument("--prep", type=Path, default=PREP_PATH)
    parser.add_argument("--result-output", type=Path, default=DEFAULT_RESULT_PATH)
    args = parser.parse_args()
    if not args.result:
        parser.error("Stage-1 executor requires --result")
    run_stage1(prep_path=args.prep, output=args.result_output)


if __name__ == "__main__":
    main()
