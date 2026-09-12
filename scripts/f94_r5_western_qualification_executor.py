"""Fail-closed executor for the Western qualification-only control.

The executor is implemented and tested with injected Arena summaries in this
work package.  The real control pilot remains a separately authorized action;
this module never changes the public Western ruleset or produces Layer-D
authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from time import perf_counter
from typing import Any, Callable, Mapping

from generic_chess.core.actions import action_to_dict
from generic_chess.learning.arena import ArenaConfig, run_arena
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.openings import generate_arena_openings
from generic_chess.learning.serialization import stable_sha256
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.catalog import builtin_ruleset_names
from generic_chess.rules.schema import compute_fingerprint, ruleset_to_dict
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from scripts.f94_r5_pilot_executor import _classify, _game_record, _summary_pairs, _value
from scripts.f94_r5_western_qualification_control import (
    EVALUATOR_IDENTITY,
    QUALIFICATION_CHECKPOINT_ID,
    QUALIFICATION_CONTROL_NAME,
    QUALIFICATION_REPETITION_LIMIT,
    QUALIFICATION_RULESET_FINGERPRINT,
    PRODUCTION_RULESET_FINGERPRINT,
    build_western_chess_qualification_control,
)
from scripts.f94_r5_western_qualification_prep import (
    DISJOINT_TAPE_SEEDS,
    MAX_DEPTH,
    PREP_PATH,
    SCHEMA,
    STRONGEST_NODES,
    TAPE_SEEDS,
    TT_MEGABYTES,
    WEAKEST_NODES,
)


ROOT = Path(__file__).resolve().parents[1]
RESULT_SCHEMA = "generic-chess-f94-r5-western-qualification-control-result-v1"
DEFAULT_RESULT_PATH = ROOT / ".generic_chess_flow/f94-r5-western-qualification-control-result.json"
FROZEN_PREP_ARTIFACT = "docs/architecture/GENERICCHESS_F94_R5_WESTERN_QUALIFICATION_CONTROL_PREP.json"
FROZEN_PREP_SHA256 = "bf5b0189aec82766d1095be8ee3396e05e0a9ed8a029bbba e3312621c78286b2".replace(" ", "")
FROZEN_PROTOCOL_SHA = "eee600237685edf67be646e6d7eaa91b48b691ce"
FROZEN_SOURCE_ARTIFACTS = {
    "source_p0_prep_artifact": (
        "docs/architecture/GENERICCHESS_F94_R5_P0_DISJOINT_PILOT_PREP.json",
        "466044894331091d716bcdf709e5b3b780d133b861fa03cdfeb39ac0ca08a395",
    ),
    "source_r5_prep_artifact": (
        "docs/architecture/GENERICCHESS_F94_R5_R1_HORIZON_AWARE_PREP.json",
        "7fe8ba521e437d011253b26a8f91bb2560ff3836db2e5b13a1bc9607719ac585",
    ),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_sha(root: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def _prep_fingerprint(payload: dict[str, Any]) -> str:
    unsigned = dict(payload)
    unsigned.pop("prep_fingerprint", None)
    return stable_sha256(unsigned)


def _validate_frozen_prep_bytes(path: Path) -> None:
    if _sha256(path) != FROZEN_PREP_SHA256:
        raise RuntimeError("qualification PREP byte SHA256 mismatch")


def _validate_prep_identity(payload: dict[str, Any], root: Path) -> None:
    if payload.get("schema") != SCHEMA or payload.get("status") != "PREP_FROZEN":
        raise RuntimeError("qualification PREP schema/status is invalid")
    if payload.get("result_free") is not True or payload.get("not_public_builtin") is not True:
        raise RuntimeError("qualification PREP must be result-free and non-public")
    protocol_sha = payload.get("protocol_source_sha")
    if protocol_sha != FROZEN_PROTOCOL_SHA or payload.get("source_sandbox_sha") != FROZEN_PROTOCOL_SHA:
        raise RuntimeError("qualification PREP protocol/source SHA is not the frozen implementation commit")
    try:
        subprocess.check_call(["git", "cat-file", "-e", f"{protocol_sha}^{{commit}}"], cwd=root)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("qualification PREP protocol source commit is unavailable") from exc
    if payload.get("prep_fingerprint") != _prep_fingerprint(payload):
        raise RuntimeError("qualification PREP fingerprint mismatch")
    if tuple(payload.get("tape_seeds", ())) != TAPE_SEEDS:
        raise RuntimeError("qualification tape identity changed")
    if tuple(payload.get("disjoint_from_tape_seeds", ())) != DISJOINT_TAPE_SEEDS:
        raise RuntimeError("qualification disjoint seed boundary changed")
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
            raise RuntimeError(f"qualification PREP control identity mismatch: {key}")
    for source_key, (expected_path, expected_sha) in FROZEN_SOURCE_ARTIFACTS.items():
        if payload.get(source_key) != expected_path:
            raise RuntimeError(f"qualification source path mismatch: {source_key}")
        if payload.get(f"{source_key}_sha256") != expected_sha:
            raise RuntimeError(f"qualification source SHA field mismatch: {source_key}")
        source = root / expected_path
        if _sha256(source) != expected_sha:
            raise RuntimeError(f"qualification source bytes mismatch: {source_key}")


def load_frozen_prep(root: Path = ROOT, prep_path: Path = PREP_PATH) -> dict[str, Any]:
    path = Path(prep_path)
    if not path.is_absolute():
        path = root / path
    expected_path = (root / FROZEN_PREP_ARTIFACT).resolve()
    if path.resolve() != expected_path:
        raise RuntimeError("qualification PREP path is not the frozen artifact")
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
    return production


def _validated_openings(compiled, payload):
    rows = payload.get("opening_corpora", ())
    if len(rows) != len(TAPE_SEEDS):
        raise RuntimeError("qualification PREP must contain exactly three opening corpora")
    if tuple(row.get("tape_seed") for row in rows) != TAPE_SEEDS:
        raise RuntimeError("qualification opening tape order changed")
    if len({row.get("tape_seed") for row in rows}) != len(TAPE_SEEDS):
        raise RuntimeError("qualification opening tape IDs must be unique")
    validated = []
    for row in rows:
        if row.get("opening_count") != 1 or row.get("selected_opening_index") != 0:
            raise RuntimeError("qualification opening corpus count/index contract changed")
        corpus = generate_arena_openings(compiled, count=1, seed=row["tape_seed"], min_plies=2, max_plies=6)
        if corpus.corpus_id != row.get("corpus_id"):
            raise RuntimeError("qualification opening corpus identity changed")
        opening = corpus.openings[row["selected_opening_index"]]
        if opening.opening_seed != row.get("selected_opening_seed"):
            raise RuntimeError("qualification opening seed identity changed")
        if opening.final_position_key != row.get("selected_final_position_key"):
            raise RuntimeError("qualification opening final-position identity changed")
        validated.append((row, corpus))
    return validated


def run_qualification_control(
    *,
    root: Path = ROOT,
    prep_path: Path = PREP_PATH,
    output: Path = DEFAULT_RESULT_PATH,
    arena_runner: Callable[..., Any] | None = None,
    native_compiler: Callable[..., Any] | None = None,
) -> dict[str, Any]:
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
        raise RuntimeError("qualification compiled fingerprint mismatch")
    if checkpoint.checkpoint_id != QUALIFICATION_CHECKPOINT_ID:
        raise RuntimeError("qualification checkpoint mismatch")
    if checkpoint.evaluator_version != EVALUATOR_IDENTITY:
        raise RuntimeError("qualification evaluator identity mismatch before native compile")
    validated_openings = _validated_openings(compiled, payload)
    native_rules = (native_compiler or compile_native_semantic_rules)(compiled)
    runner = arena_runner or run_arena
    tape_results = []
    actual_invocations = actual_pairs = actual_games = actual_traces = 0
    candidate = payload["qualification_control"]
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
                    pairs=1,
                    nodes_per_move=STRONGEST_NODES,
                    parent_nodes_per_move=WEAKEST_NODES,
                    child_nodes_per_move=STRONGEST_NODES,
                    max_depth=MAX_DEPTH,
                    tt_megabytes=TT_MEGABYTES,
                    opening_seed=corpus.seed,
                    opening_count=1,
                    workers=1,
                ),
                openings=corpus,
                capture_search_metrics=True,
            )
        except Exception as exc:
            tape_results.append({
                "tape_seed": tape["tape_seed"],
                "corpus_id": tape["corpus_id"],
                "status": "OPERATIONALLY_UNRESOLVED",
                "wall_seconds": perf_counter() - started,
                "error_type": type(exc).__name__,
                "error": str(exc),
            })
            break
        pair = _summary_pairs(summary)[0]
        owner0 = _value(pair, "game_child_owner0")
        owner1 = _value(pair, "game_child_owner1")
        if owner0 is None or owner1 is None:
            raise RuntimeError("qualification Arena pair lacks both role-swapped games")
        games = [
            _game_record(owner0, tape={**tape, "max_ply": candidate["max_ply"]}, matchup=QUALIFICATION_CONTROL_NAME),
            _game_record(owner1, tape={**tape, "max_ply": candidate["max_ply"]}, matchup=QUALIFICATION_CONTROL_NAME),
        ]
        if {game["child_owner"] for game in games} != {0, 1}:
            raise RuntimeError("qualification Arena pair is not seat-swapped")
        metrics = [
            dict(metric)
            for game in games
            for metric in _value(
                next((g for g in (owner0, owner1) if _value(g, "child_owner") == game["child_owner"]), owner0),
                "search_metrics",
                (),
            )
        ]
        score = float(_value(pair, "child_pair_score"))
        status, descriptors = _classify(score, games, metrics, candidate["max_ply"])
        actual_pairs += 1
        actual_games += 2
        actual_traces += 2
        tape_results.append({
            "tape_seed": tape["tape_seed"],
            "corpus_id": tape["corpus_id"],
            "pair_score": score,
            "status": status,
            "descriptors": descriptors,
            "wall_seconds": perf_counter() - started,
            "games": games,
        })
    scores = [row["pair_score"] for row in tape_results if "pair_score" in row]
    statuses = [row["status"] for row in tape_results]
    depth_hits = sum(row.get("descriptors", {}).get("child_depth_ceiling", {}).get("hits", 0) for row in tape_results)
    depth_count = sum(row.get("descriptors", {}).get("child_depth_ceiling", {}).get("count", 0) for row in tape_results)
    horizon_hits = sum(row.get("descriptors", {}).get("strongest_vs_weakest_horizon", {}).get("max_ply_hits", 0) for row in tape_results)
    horizon_games = sum(row.get("descriptors", {}).get("strongest_vs_weakest_horizon", {}).get("games", 0) for row in tape_results)
    depth_fraction = depth_hits / depth_count if depth_count else 0.0
    horizon_fraction = horizon_hits / horizon_games if horizon_games else 0.0
    if "EXPLICIT_CENSOR" in statuses:
        direction = "EXPLICIT_CENSOR"
    elif "FALLBACK" in statuses:
        direction = "FALLBACK"
    elif len(scores) != len(TAPE_SEEDS) or "OPERATIONALLY_UNRESOLVED" in statuses:
        direction = "OPERATIONALLY_UNRESOLVED"
    elif depth_fraction >= 0.5:
        direction = "DEPTH_CENSORED"
    elif horizon_fraction >= 0.5:
        direction = "HORIZON_CENSORED"
    elif all(score > 0.5 for score in scores):
        direction = "POSITIVE_DIRECTION"
    elif all(score < 0.5 for score in scores):
        direction = "NEGATIVE_DIRECTION"
    else:
        direction = "MIXED_OR_UNCERTAIN"
    result = {
        "schema": RESULT_SCHEMA,
        "status": "QUALIFICATION_CONTROL_RESULT_COMPLETE" if (actual_invocations, actual_pairs, actual_games, actual_traces) == (3, 3, 6, 6) else "QUALIFICATION_CONTROL_RESULT_INCOMPLETE",
        "experiment": payload["experiment"],
        "prep_artifact": prep_path.relative_to(root).as_posix() if prep_path.is_relative_to(root) else str(prep_path),
        "prep_artifact_sha256": _sha256(prep_path),
        "prep_byte_sha256": _sha256(prep_path),
        "prep_fingerprint": payload["prep_fingerprint"],
        "protocol_source_sha": payload["protocol_source_sha"],
        "source_sandbox_sha": payload["source_sandbox_sha"],
        "result_sandbox_sha": _git_sha(root),
        "result_executor_path": Path(__file__).resolve().relative_to(root).as_posix(),
        "result_executor_sha256": _sha256(Path(__file__).resolve()),
        "qualification_control": candidate,
        "tape_results": tape_results,
        "pooled_pair_count": len(scores),
        "pooled_mean_pair_score": sum(scores) / len(scores) if scores else None,
        "pooled_censoring": {
            "child_depth_ceiling": {"hits": depth_hits, "count": depth_count, "fraction": depth_fraction},
            "strongest_vs_weakest_horizon": {"max_ply_hits": horizon_hits, "games": horizon_games, "fraction": horizon_fraction},
        },
        "direction": direction,
        "derived_compute": {
            "arena_invocations": actual_invocations,
            "arena_pairs": actual_pairs,
            "arena_games": actual_games,
            "action_traces": actual_traces,
        },
        "control_only": True,
        "not_layer_d_authority": True,
        "observed_not_poolable": True,
        "p0_observations_pooled": False,
        "r2_observations_pooled": False,
        "r3_observations_pooled": False,
        "r5_observations_pooled": False,
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
        parser.error("qualification executor requires --result")
    run_qualification_control(prep_path=args.prep, output=args.result_output)


if __name__ == "__main__":
    main()
