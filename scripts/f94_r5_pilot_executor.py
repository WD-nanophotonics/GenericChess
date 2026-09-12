"""Fail-closed executor for the disjoint F94-R5 P0 pilot.

This is a descriptive twelve-game probe.  It never calls the full R5
``measure_strength_response`` reducer and never produces Layer-D authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from time import perf_counter
from typing import Any, Callable, Mapping

from generic_chess.learning.arena import ArenaConfig, run_arena
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.openings import generate_arena_openings
from generic_chess.learning.serialization import stable_sha256
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.core.actions import action_to_dict
from scripts.f87a_ruleset_qualification import _controls
from scripts.f94_r2_strength_calibration import _ruleset_for
from scripts.f94_r5_pilot_prep import (
    BOUNDARY_NAME,
    MAX_DEPTH,
    PILOT_TAPE_SEEDS,
    PREP_PATH,
    SCHEMA,
    SOURCE_PREP_PATH,
    STRONGEST_NODES,
    WEAKEST_NODES,
)


ROOT = Path(__file__).resolve().parents[1]
RESULT_SCHEMA = "generic-chess-f94-r5-p0-disjoint-pilot-result-v1"
DEFAULT_RESULT_PATH = ROOT / ".generic_chess_flow/f94-r5-p0-disjoint-pilot-result.json"
PILOT_PREP_SHA256 = "fa2d2347cbc03b69a3d01294ddc1b0c50f003379ef18c971796041a8301c8cd0"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_sha(root: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def _prep_fingerprint(payload: dict[str, Any]) -> str:
    unsigned = dict(payload)
    unsigned.pop("pilot_prep_fingerprint", None)
    return stable_sha256(unsigned)


def _value(value: Any, key: str, default: Any = None) -> Any:
    return value.get(key, default) if isinstance(value, Mapping) else getattr(value, key, default)


def _game_record(game: Any, *, tape: dict[str, Any], matchup: str) -> dict[str, Any]:
    actions = []
    for action in _value(game, "actions", ()):
        actions.append(dict(action) if isinstance(action, Mapping) else action_to_dict(action))
    record = {
        "schema": "generic-chess-strength-response-action-trace-v1",
        "tape_id": tape["tape_seed"],
        "opening_corpus_id": tape["corpus_id"],
        "matchup": matchup,
        "game_index": int(_value(game, "child_owner", 0)),
        "pair_index": int(_value(game, "pair", 0)),
        "child_owner": int(_value(game, "child_owner", 0)),
        "budget_roles": {"parent_nodes_per_move": 256, "child_nodes_per_move": 4096},
        "termination_status": str(_value(game, "result", "")),
        "max_ply": tape["max_ply"],
        "max_ply_hit": str(_value(game, "result", "")) == "max_ply",
        "actual_plies": int(_value(game, "plies", 0)),
        "opening_position_key": _value(game, "opening_position_key"),
        "final_position_key": _value(game, "final_position_key"),
        "declaration_id": _value(game, "declaration_id"),
        "actions": actions,
    }
    required = (
        record["pair_index"], record["child_owner"], record["actual_plies"],
        record["opening_position_key"], record["final_position_key"], record["termination_status"],
    )
    if any(value is None or value == "" for value in required):
        raise RuntimeError("pilot game telemetry is incomplete")
    record["action_trace_sha256"] = stable_sha256(record)
    return record


def _summary_pairs(summary: Any) -> list[Any]:
    pairs = _value(summary, "pairs", ())
    if len(pairs) != 1:
        raise RuntimeError("pilot Arena must return exactly one role-swapped pair")
    return list(pairs)


def _classify(pair_score: float, games: list[dict[str, Any]], metrics: list[dict[str, Any]], max_ply: int) -> tuple[str, dict[str, Any]]:
    child_metrics = [row for row in metrics if row.get("engine_role") == "child"]
    depth_hits = sum(int(int(row.get("completed_depth", 0)) >= MAX_DEPTH) for row in child_metrics)
    depth_fraction = depth_hits / len(child_metrics) if child_metrics else 0.0
    horizon_hits = sum(int(row.get("max_ply_hit", False)) for row in games)
    horizon_fraction = horizon_hits / len(games) if games else 0.0
    fallback = any(bool(row.get("used_fallback")) for row in metrics)
    explicit_censor = any(bool(row.get("censor_flag")) for row in metrics) or any(
        bool(game.get("censor_flag")) for game in games
    )
    if explicit_censor:
        status = "EXPLICIT_CENSOR"
    elif fallback:
        status = "FALLBACK"
    elif depth_fraction >= 0.5:
        status = "DEPTH_CENSORED"
    elif horizon_fraction >= 0.5:
        status = "HORIZON_CENSORED"
    elif pair_score > 0.5:
        status = "POSITIVE_DIRECTION"
    elif pair_score < 0.5:
        status = "NEGATIVE_DIRECTION"
    else:
        status = "MIXED_OR_UNCERTAIN"
    return status, {
        "child_depth_ceiling": {"hits": depth_hits, "count": len(child_metrics), "fraction": depth_fraction},
        "strongest_vs_weakest_horizon": {"max_ply_hits": horizon_hits, "games": len(games), "fraction": horizon_fraction},
        "fallback": fallback,
        "explicit_censor": explicit_censor,
        "max_ply": max_ply,
    }


def load_frozen_prep(root: Path = ROOT, prep_path: Path = PREP_PATH) -> dict[str, Any]:
    path = Path(prep_path)
    if not path.is_absolute():
        path = root / path
    if _sha256(path) != PILOT_PREP_SHA256:
        raise RuntimeError("pilot PREP byte SHA256 mismatch")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != SCHEMA or payload.get("status") != "PILOT_PREP_FROZEN" or payload.get("result_free") is not True:
        raise RuntimeError("pilot PREP schema/status is invalid")
    if payload.get("non_poolable_with_r2_r3_r5") is not True:
        raise RuntimeError("pilot PREP must be explicitly non-poolable")
    if payload.get("pilot_prep_fingerprint") != _prep_fingerprint(payload):
        raise RuntimeError("pilot PREP fingerprint mismatch")
    if tuple(payload.get("pilot_tape_seeds", ())) != PILOT_TAPE_SEEDS:
        raise RuntimeError("pilot tape identity changed")
    if set(payload["pilot_tape_seeds"]) & set(payload["authoritative_r5_tape_seeds"]):
        raise RuntimeError("pilot tapes overlap authoritative R5 tapes")
    source = root / payload["source_r5_prep_artifact"]
    if _sha256(source) != payload["source_r5_prep_artifact_sha256"]:
        raise RuntimeError("pilot source R5 PREP SHA mismatch")
    frozen = json.loads(source.read_text(encoding="utf-8"))
    if frozen.get("status") != "PREP_FROZEN" or frozen.get("result_free") is not True:
        raise RuntimeError("pilot source R5 PREP is not frozen/result-free")
    return payload


def run_pilot(
    *,
    root: Path = ROOT,
    prep_path: Path = PREP_PATH,
    output: Path = DEFAULT_RESULT_PATH,
    arena_runner: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    prep_path = Path(prep_path)
    if not prep_path.is_absolute():
        prep_path = root / prep_path
    payload = load_frozen_prep(root, prep_path)
    source = json.loads((root / payload["source_r5_prep_artifact"]).read_text(encoding="utf-8"))
    source_rows = {row["name"]: row for row in source["candidates"]}
    controls = {row["name"]: row for row in _controls(root)}
    runner = arena_runner or run_arena
    candidates = []
    actual_invocations = actual_pairs = actual_games = actual_traces = 0
    for candidate in payload["candidates"]:
        name = candidate["name"]
        source_row = source_rows[name]
        identity = (
            candidate["ruleset_fingerprint"] == source_row["ruleset_fingerprint"]
            and candidate["checkpoint_id"] == source_row["checkpoint_id"]
            and candidate["evaluator_identity"] == source_row["evaluator_identity"]
        )
        if not identity:
            raise RuntimeError(f"{name} pilot identity does not match frozen R5 source")
        if candidate["layer_d_prerequisite"] != "READY":
            candidates.append({
                "name": name,
                "status": "PREREQUISITE_A_C_NOT_PASS",
                "arena_invocations": 0,
                "arena_pairs": 0,
                "arena_games": 0,
                "action_traces": 0,
                "tape_results": [],
            })
            continue
        control = controls[name]
        compiled, profile = _ruleset_for(control)
        checkpoint = LearnableMaterialCheckpoint.from_profile(compiled, profile)
        if checkpoint.checkpoint_id != candidate["checkpoint_id"] or compiled.ruleset_fingerprint != candidate["ruleset_fingerprint"]:
            raise RuntimeError(f"{name} compiled identity mismatch before pilot")
        native_rules = compile_native_semantic_rules(compiled)
        tape_results = []
        for tape in candidate["opening_corpora"]:
            corpus = generate_arena_openings(compiled, count=1, seed=tape["tape_seed"], min_plies=2, max_plies=6)
            if corpus.corpus_id != tape["corpus_id"]:
                raise RuntimeError(f"{name} pilot corpus identity changed")
            opening = corpus.openings[tape["selected_opening_index"]]
            if opening.opening_seed != tape["selected_opening_seed"] or opening.final_position_key != tape["selected_final_position_key"]:
                raise RuntimeError(f"{name} pilot opening identity changed")
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
                        tt_megabytes=8,
                        opening_seed=corpus.seed,
                        opening_count=1,
                        workers=1,
                    ),
                    openings=corpus,
                    capture_search_metrics=True,
                )
            except Exception as exc:
                tape_results.append({"tape_seed": tape["tape_seed"], "corpus_id": tape["corpus_id"], "status": "OPERATIONALLY_UNRESOLVED", "wall_seconds": perf_counter() - started, "error_type": type(exc).__name__, "error": str(exc)})
                break
            pair = _summary_pairs(summary)[0]
            owner0 = _value(pair, "game_child_owner0")
            owner1 = _value(pair, "game_child_owner1")
            if owner0 is None or owner1 is None:
                raise RuntimeError("pilot Arena pair lacks both role-swapped games")
            games = [_game_record(owner0, tape={**tape, "max_ply": candidate["prep"]["max_ply"]}, matchup="16x-vs-1x"), _game_record(owner1, tape={**tape, "max_ply": candidate["prep"]["max_ply"]}, matchup="16x-vs-1x")]
            if {game["child_owner"] for game in games} != {0, 1}:
                raise RuntimeError("pilot Arena pair is not seat-swapped")
            metrics = [dict(metric) for game in games for metric in _value(next((g for g in (owner0, owner1) if _value(g, "child_owner") == game["child_owner"]), owner0), "search_metrics", ())]
            pair_score = float(_value(pair, "child_pair_score"))
            status, descriptors = _classify(pair_score, games, metrics, candidate["prep"]["max_ply"])
            actual_pairs += 1
            actual_games += 2
            actual_traces += 2
            tape_results.append({
                "tape_seed": tape["tape_seed"],
                "corpus_id": tape["corpus_id"],
                "pair_score": pair_score,
                "status": status,
                "descriptors": descriptors,
                "wall_seconds": perf_counter() - started,
                "games": games,
            })
        scores = [row["pair_score"] for row in tape_results if "pair_score" in row]
        statuses = [row["status"] for row in tape_results]
        if any(status in {"EXPLICIT_CENSOR", "FALLBACK", "DEPTH_CENSORED", "HORIZON_CENSORED"} for status in statuses):
            direction = next(status for status in statuses if status in {"EXPLICIT_CENSOR", "FALLBACK", "DEPTH_CENSORED", "HORIZON_CENSORED"})
        elif len(scores) != 3:
            direction = "OPERATIONALLY_UNRESOLVED"
        elif all(score > 0.5 for score in scores):
            direction = "POSITIVE_DIRECTION"
        elif all(score < 0.5 for score in scores):
            direction = "NEGATIVE_DIRECTION"
        else:
            direction = "MIXED_OR_UNCERTAIN"
        candidates.append({
            "name": name,
            "ruleset_fingerprint": candidate["ruleset_fingerprint"],
            "checkpoint_id": candidate["checkpoint_id"],
            "evaluator_identity": candidate["evaluator_identity"],
            "pilot_prep_fingerprint": payload["pilot_prep_fingerprint"],
            "tape_results": tape_results,
            "arena_invocations": len(tape_results),
            "arena_pairs": len(scores),
            "arena_games": len(scores) * 2,
            "action_traces": len(scores) * 2,
            "pooled_pair_count": len(scores),
            "pooled_mean_pair_score": sum(scores) / len(scores) if scores else None,
            "direction": direction,
        })
    result = {
        "schema": RESULT_SCHEMA,
        "status": "PILOT_RESULT_COMPLETE" if (actual_invocations, actual_pairs, actual_games, actual_traces) == (6, 6, 12, 12) else "PILOT_RESULT_INCOMPLETE",
        "experiment": payload["experiment"],
        "pilot_prep_artifact": prep_path.relative_to(root).as_posix(),
        "pilot_prep_artifact_sha256": _sha256(prep_path),
        "pilot_prep_fingerprint": payload["pilot_prep_fingerprint"],
        "result_sandbox_sha": _git_sha(root),
        "candidates": candidates,
        "boundary_control": payload["boundary_control"],
        "derived_compute": {"arena_invocations": actual_invocations, "arena_pairs": actual_pairs, "arena_games": actual_games, "action_traces": actual_traces, "boundary_arena_invocations": 0},
        "not_layer_d_authority": True,
        "observed_not_poolable": True,
        "r2_observations_pooled": False,
        "r3_observations_pooled": False,
        "r5_observations_pooled": False,
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
        parser.error("pilot executor requires --result")
    run_pilot(prep_path=args.prep, output=args.result_output)


if __name__ == "__main__":
    main()
