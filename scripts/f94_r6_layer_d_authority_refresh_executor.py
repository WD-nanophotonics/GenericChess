"""Fail-closed executor for the frozen, result-free R6 authority protocol."""

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
from generic_chess.core.actions import action_to_dict
from generic_chess.learning.arena import ArenaConfig, run_arena
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.openings import generate_arena_openings
from generic_chess.learning.serialization import stable_sha256
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.rules.catalog import builtin_ruleset_names
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import compute_fingerprint, ruleset_to_dict
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.f94_r5_western_qualification_control import (
    QUALIFICATION_CONTROL_NAME,
    PRODUCTION_RULESET_FINGERPRINT,
    QUALIFICATION_REPETITION_LIMIT,
    QUALIFICATION_RULESET_FINGERPRINT,
    build_western_chess_qualification_control,
)
from scripts.f94_r6_layer_d_authority_refresh_prep import (
    BOOTSTRAP_RESAMPLES, BOOTSTRAP_SEEDS, CONFIDENCE_LEVEL, DISALLOWED_TAPE_SEEDS,
    EXPERIMENT, GAMES_PER_MATCHUP, MATCHUPS, MAX_DEPTH, PAIRS_PER_MATCHUP,
    PAIRS_PER_TAPE, PREP_PATH, RESULT_SCHEMA, SCHEMA, TAPE_COUNT, TAPE_SEEDS, TOTAL_GAMES,
    TOTAL_INVOCATIONS, TOTAL_PAIRS, TOTAL_TRACES, TRACES_PER_MATCHUP, TT_MEGABYTES, WORKERS,
)

ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = ROOT / ".generic_chess_flow/f94-r6-layer-d-authority-refresh-result.json"
FROZEN_PREP_ARTIFACT = "docs/architecture/GENERICCHESS_F94_R6_LAYER_D_AUTHORITY_REFRESH_PREP.json"
# Filled after the two-step protocol/provenance freeze.
FROZEN_PROTOCOL_SHA = "1c21371c4ef9cc6b7c3e3a0833efcf0c833afdeb"
FROZEN_PREP_SHA256 = "f160c1052531b5763b17bf4ec085ae2b63d7828b4de5baef0c493980b2a54efb"


def _value(value: Any, key: str, default: Any = None) -> Any:
    return value.get(key, default) if isinstance(value, Mapping) else getattr(value, key, default)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_sha(root: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def _prep_fingerprint(payload: dict[str, Any]) -> str:
    unsigned = dict(payload)
    unsigned.pop("prep_fingerprint", None)
    return stable_sha256(unsigned)


def percentile_bootstrap_mean(scores: list[float], *, resamples: int = BOOTSTRAP_RESAMPLES,
                              seed: int, confidence_level: float = CONFIDENCE_LEVEL) -> dict[str, Any]:
    if len(scores) != PAIRS_PER_MATCHUP:
        raise ValueError("R6 bootstrap requires exactly 18 current-matchup pair scores")
    rng = random.Random(seed)
    means = sorted(sum(rng.choice(scores) for _ in scores) / len(scores) for _ in range(resamples))
    alpha = (1.0 - confidence_level) / 2.0
    def q(fraction: float) -> float:
        pos = (len(means) - 1) * fraction
        lo, hi = int(pos), min(int(pos) + 1, len(means) - 1)
        return means[lo] * (1.0 - (pos - lo)) + means[hi] * (pos - lo)
    return {"mean": sum(scores) / len(scores), "lower": q(alpha), "upper": q(1 - alpha),
            "resamples": resamples, "seed": seed, "confidence_level": confidence_level,
            "method": "percentile_bootstrap_mean_pair_score", "sample_count": len(scores)}


def _game_record(game: Any, *, tape: Mapping[str, Any], matchup: str, parent: int, child: int) -> dict[str, Any]:
    actions = [dict(a) if isinstance(a, Mapping) else action_to_dict(a) for a in _value(game, "actions", ())]
    record = {
        "schema": "generic-chess-r6-action-trace-v1", "tape_id": tape["tape_seed"],
        "opening_corpus_id": tape["corpus_id"], "matchup": matchup,
        "pair_index": int(_value(game, "pair", 0)), "child_owner": int(_value(game, "child_owner", 0)),
        "budget_roles": {"parent_nodes_per_move": parent, "child_nodes_per_move": child},
        "termination_status": str(_value(game, "result", "")),
        "max_ply": int(tape.get("max_ply", 1000)),
        "max_ply_hit": str(_value(game, "result", "")) == "max_ply",
        "actual_plies": int(_value(game, "plies", 0)),
        "opening_position_key": _value(game, "opening_position_key"),
        "final_position_key": _value(game, "final_position_key"),
        "declaration_id": _value(game, "declaration_id"), "actions": actions,
    }
    if (record["opening_position_key"] in (None, "") or record["final_position_key"] in (None, "")
            or record["termination_status"] == "" or record["actual_plies"] != len(actions)):
        raise RuntimeError("R6 evidence-integrity failure: incomplete action trace")
    record["action_trace_sha256"] = stable_sha256(record)
    return record


def _summary_pairs(summary: Any) -> list[Any]:
    pairs = _value(summary, "pairs", ())
    if len(pairs) != PAIRS_PER_TAPE:
        raise RuntimeError("R6 Arena must return exactly six role-swapped pairs per invocation")
    return list(pairs)


def _validate_search_telemetry(game: Any, *, parent_budget: int, child_budget: int) -> list[dict[str, Any]]:
    """Validate role-aware search telemetry before a game's score is usable."""
    raw = _value(game, "search_metrics", ())
    if not raw:
        raise RuntimeError("R6 evidence-integrity failure: search_metrics is empty")
    rows: list[dict[str, Any]] = []
    roles: set[str] = set()
    for metric in raw:
        if not isinstance(metric, Mapping):
            raise RuntimeError("R6 evidence-integrity failure: malformed search telemetry row")
        role = metric.get("engine_role")
        if role not in {"child", "parent"}:
            raise RuntimeError("R6 evidence-integrity failure: invalid engine_role")
        completed_depth = metric.get("completed_depth")
        used_fallback = metric.get("used_fallback")
        nodes_budget = metric.get("nodes_budget")
        if isinstance(completed_depth, bool) or not isinstance(completed_depth, int) or completed_depth < 0:
            raise RuntimeError("R6 evidence-integrity failure: invalid completed_depth")
        if not isinstance(used_fallback, bool):
            raise RuntimeError("R6 evidence-integrity failure: invalid used_fallback")
        if isinstance(nodes_budget, bool) or not isinstance(nodes_budget, int) or nodes_budget <= 0:
            raise RuntimeError("R6 evidence-integrity failure: invalid nodes_budget")
        expected = child_budget if role == "child" else parent_budget
        if nodes_budget != expected:
            raise RuntimeError("R6 evidence-integrity failure: role budget mismatch")
        roles.add(role)
        rows.append(dict(metric))
    if roles != {"child", "parent"}:
        raise RuntimeError("R6 evidence-integrity failure: incomplete role-aware telemetry")
    return rows


def _validate_western_runtime_guards() -> None:
    production = build_western_chess_ruleset()
    control = build_western_chess_qualification_control()
    if compute_fingerprint(production) != PRODUCTION_RULESET_FINGERPRINT:
        raise RuntimeError("production Western fingerprint changed")
    if compute_fingerprint(control) != QUALIFICATION_RULESET_FINGERPRINT:
        raise RuntimeError("qualification control fingerprint changed")
    if QUALIFICATION_CONTROL_NAME in builtin_ruleset_names():
        raise RuntimeError("qualification control must remain non-public")
    left = ruleset_to_dict(production, include_metadata=True)
    right = ruleset_to_dict(control, include_metadata=True)
    if [key for key in left if left[key] != right[key]] != ["repetition_limit"]:
        raise RuntimeError("qualification control gameplay delta changed")
    if production.repetition_limit != 100000 or control.repetition_limit != QUALIFICATION_REPETITION_LIMIT:
        raise RuntimeError("qualification repetition threshold changed")


def _validate_frozen_prep(payload: dict[str, Any], root: Path, path: Path) -> None:
    if payload.get("schema") != SCHEMA or payload.get("status") != "PREP_FROZEN" or payload.get("result_free") is not True:
        raise RuntimeError("R6 PREP schema/status/result-free contract is invalid")
    if payload.get("experiment") != EXPERIMENT or payload.get("fixed_sample_authority") is not True:
        raise RuntimeError("R6 PREP experiment identity is invalid")
    if FROZEN_PROTOCOL_SHA.startswith("__") or payload.get("protocol_source_sha") != FROZEN_PROTOCOL_SHA or payload.get("source_sandbox_sha") != FROZEN_PROTOCOL_SHA:
        raise RuntimeError("R6 PREP protocol/source SHA is not frozen")
    if FROZEN_PREP_SHA256.startswith("__") or _sha256(path) != FROZEN_PREP_SHA256:
        raise RuntimeError("R6 PREP byte SHA256 mismatch")
    subprocess.check_call(["git", "cat-file", "-e", f"{FROZEN_PROTOCOL_SHA}^{{commit}}"], cwd=root)
    if payload.get("prep_fingerprint") != _prep_fingerprint(payload):
        raise RuntimeError("R6 PREP fingerprint mismatch")
    if tuple(payload.get("tape_seeds", ())) != TAPE_SEEDS or tuple(payload.get("disallowed_tape_seeds", ())) != DISALLOWED_TAPE_SEEDS:
        raise RuntimeError("R6 tape boundary changed")
    if set(TAPE_SEEDS) & set(DISALLOWED_TAPE_SEEDS):
        raise RuntimeError("R6 tape boundary overlaps historical seeds")
    boundary = payload.get("boundary", {})
    if payload.get("layer_d_compute_authorized") is not False or boundary.get("layer_d_compute_invocations") != 0:
        raise RuntimeError("R6 boundary must short-circuit Layer-D compute")
    controls = payload.get("controls", ())
    if tuple(row.get("name") for row in controls) != (QUALIFICATION_CONTROL_NAME, "standard_shogi"):
        raise RuntimeError("R6 control names/order changed")
    matchup_rows = payload.get("matchups", ())
    expected_matchups = tuple((name, child, parent) for name, child, parent in MATCHUPS)
    actual_matchups = tuple((row.get("name"), row.get("child_nodes_per_move"), row.get("parent_nodes_per_move")) for row in matchup_rows)
    if actual_matchups != expected_matchups:
        raise RuntimeError("R6 matchup budgets/order changed")
    if any(row.get("pairs_per_tape") != PAIRS_PER_TAPE or row.get("tape_count") != 3 or row.get("pair_count") != PAIRS_PER_MATCHUP or row.get("game_count") != GAMES_PER_MATCHUP or row.get("trace_count") != TRACES_PER_MATCHUP or row.get("bootstrap_seed") != BOOTSTRAP_SEEDS[row["name"]] for row in matchup_rows):
        raise RuntimeError("R6 matchup accounting/bootstrap identity changed")
    budgets = payload.get("budgets", {})
    expected_budget = {"invocations_per_control": 9, "pairs_per_control": 54, "games_per_control": 108, "traces_per_control": 108, "total_invocations": TOTAL_INVOCATIONS, "total_pairs": TOTAL_PAIRS, "total_games": TOTAL_GAMES, "total_traces": TOTAL_TRACES, "max_depth": MAX_DEPTH, "tt_megabytes": TT_MEGABYTES, "workers": WORKERS}
    if any(budgets.get(key) != value for key, value in expected_budget.items()):
        raise RuntimeError("R6 total accounting/budget identity changed")
    bootstrap = payload.get("bootstrap", {})
    if bootstrap.get("method") != "percentile_bootstrap_mean_pair_score" or bootstrap.get("resamples") != BOOTSTRAP_RESAMPLES or bootstrap.get("confidence_level") != CONFIDENCE_LEVEL or bootstrap.get("historical_pools_enter_bootstrap") is not False:
        raise RuntimeError("R6 bootstrap configuration changed")


def load_frozen_prep(root: Path = ROOT, prep_path: Path = PREP_PATH) -> dict[str, Any]:
    path = Path(prep_path)
    if not path.is_absolute():
        path = root / path
    if path.resolve() != (root / FROZEN_PREP_ARTIFACT).resolve():
        raise RuntimeError("R6 PREP path is not the frozen artifact")
    payload = json.loads(path.read_text(encoding="utf-8"))
    _validate_frozen_prep(payload, root, path)
    return payload


def _control_builders() -> dict[str, Callable[[], Any]]:
    return {QUALIFICATION_CONTROL_NAME: build_western_chess_qualification_control,
            "standard_shogi": build_standard_shogi_ruleset}


def validated_openings(payload: dict[str, Any]) -> list[tuple[dict[str, Any], Any, Any]]:
    """Validate every corpus before the caller may invoke Arena even once."""
    result = []
    builders = _control_builders()
    for control in payload["controls"]:
        compiled = compile_ruleset_for_execution(builders[control["name"]]())
        if compiled.ruleset_fingerprint != control["ruleset_fingerprint"]:
            raise RuntimeError(f"{control['name']} ruleset fingerprint changed")
        for row in control["opening_corpora"]:
            if row["tape_seed"] not in TAPE_SEEDS or len(row["openings"]) != PAIRS_PER_TAPE:
                raise RuntimeError("R6 opening count/tape identity changed")
            corpus = generate_arena_openings(compiled, count=PAIRS_PER_TAPE, seed=row["tape_seed"], min_plies=2, max_plies=6)
            if corpus.corpus_id != row["corpus_id"]:
                raise RuntimeError("R6 opening corpus identity changed")
            for expected, opening in zip(row["openings"], corpus.openings):
                if expected.get("index") != opening.index or expected.get("opening_seed") != opening.opening_seed or expected.get("target_plies") != opening.target_plies or expected.get("action_count") != len(opening.actions) or expected.get("final_position_key") != opening.final_position_key:
                    raise RuntimeError("R6 opening identity changed")
            result.append((control, compiled, (row, corpus)))
    return result


def classify_matchup(*, scores: list[float], tape_means: list[float], statuses: list[str], depth_fraction: float,
                     horizon_fraction: float, bootstrap: dict[str, Any], strongest_vs_weakest: bool = False) -> str:
    if any(status in {"EXPLICIT_CENSOR", "FALLBACK", "EVIDENCE_INTEGRITY_FAILURE", "OPERATIONALLY_UNRESOLVED"} for status in statuses):
        return "DEFER"
    if depth_fraction >= 0.5:
        return "DEFER_DEPTH_CENSORED"
    if strongest_vs_weakest and horizon_fraction >= 0.5:
        return "DEFER_HORIZON_CENSORED"
    if len(scores) != PAIRS_PER_MATCHUP or len(tape_means) != TAPE_COUNT or any(mean <= 0.5 for mean in tape_means) or bootstrap.get("lower", 0.0) <= 0.5:
        return "DEFER_NONMONOTONE_OR_UNCERTAIN"
    return "PASS"


def classify_control(matchups: list[dict[str, Any]], statuses: list[str]) -> str:
    if any(status in {"DEFER", "DEFER_DEPTH_CENSORED", "DEFER_HORIZON_CENSORED", "DEFER_NONMONOTONE_OR_UNCERTAIN"} for status in statuses):
        return "DEFER_NONMONOTONE_OR_UNCERTAIN"
    if len(matchups) == 3 and all(row.get("classification") == "PASS" for row in matchups):
        return "STABLE_MONOTONE_POSITIVE"
    return "DEFER_NONMONOTONE_OR_UNCERTAIN"


def run_r6(*, root: Path = ROOT, prep_path: Path = PREP_PATH, output: Path = RESULT_PATH,
           arena_runner: Callable[..., Any] | None = None,
           native_compiler: Callable[..., Any] | None = None) -> dict[str, Any]:
    prep_path = Path(prep_path)
    if not prep_path.is_absolute():
        prep_path = root / prep_path
    payload = load_frozen_prep(root, prep_path)
    # These guards run before any native compiler or Arena selection.
    _validate_western_runtime_guards()
    # This call validates all opening identities before the runner is selected.
    openings = validated_openings(payload)
    runner = arena_runner or run_arena
    native_compiler = native_compiler or compile_native_semantic_rules
    by_control: dict[str, Any] = {}
    total = {"arena_invocations": 0, "arena_pairs": 0, "arena_games": 0, "action_traces": 0}
    control_entries = {control["name"]: (control, compiled) for control, compiled, _ in openings}
    for control, compiled in control_entries.values():
        name = control["name"]
        profile = build_ruleset_profile(compiled, EvaluationConfig())
        checkpoint = LearnableMaterialCheckpoint.from_profile(compiled, profile)
        if name == QUALIFICATION_CONTROL_NAME and compiled.ruleset_fingerprint != QUALIFICATION_RULESET_FINGERPRINT:
            raise RuntimeError("qualification control compiled fingerprint changed")
        if checkpoint.checkpoint_id != control["checkpoint_id"] or checkpoint.evaluator_version != control["evaluator_identity"]:
            raise RuntimeError(f"{name} evaluator/checkpoint identity changed")
        native_rules = native_compiler(compiled)
        rows_by_tape = {(row["tape_seed"]): (row, corpus) for c, _, (row, corpus) in openings if c["name"] == name}
        matchup_rows = []
        control_statuses = []
        for matchup_name, child_nodes, parent_nodes in MATCHUPS:
            scores: list[float] = []
            statuses: list[str] = []
            tape_results = []
            depth_hits = depth_count = horizon_hits = horizon_games = 0
            for seed in TAPE_SEEDS:
                tape, corpus = rows_by_tape[seed]
                started = perf_counter()
                invocation_scores: list[float] = []
                invocation_statuses: list[str] = []
                invocation_pair_rows: list[dict[str, Any]] = []
                invocation_depth_hits = invocation_depth_count = 0
                invocation_horizon_hits = invocation_horizon_games = 0
                try:
                    summary = runner(compiled, native_rules, checkpoint, checkpoint,
                        ArenaConfig(pairs=PAIRS_PER_TAPE, nodes_per_move=child_nodes,
                                    parent_nodes_per_move=parent_nodes, child_nodes_per_move=child_nodes,
                                    max_depth=MAX_DEPTH, tt_megabytes=TT_MEGABYTES,
                                    opening_seed=seed, opening_count=PAIRS_PER_TAPE, workers=WORKERS),
                        openings=corpus, capture_search_metrics=True)
                    pairs = _summary_pairs(summary)
                    pair_rows = []
                    for index, pair in enumerate(pairs):
                        owner0, owner1 = _value(pair, "game_child_owner0"), _value(pair, "game_child_owner1")
                        opening = corpus.openings[index]
                        if _value(pair, "pair_index") != index or _value(pair, "opening_id") != opening.final_position_key or owner0 is None or owner1 is None:
                            raise RuntimeError("R6 pair/opening identity failure")
                        games = []
                        for game in (owner0, owner1):
                            if _value(game, "pair") != index or _value(game, "opening_id") != opening.final_position_key or _value(game, "opening_position_key") != opening.final_position_key:
                                raise RuntimeError("R6 game/opening identity failure")
                            telemetry = _validate_search_telemetry(game, parent_budget=parent_nodes, child_budget=child_nodes)
                            row = _game_record(game, tape={**tape, "max_ply": control["max_ply"]}, matchup=matchup_name, parent=parent_nodes, child=child_nodes)
                            games.append(row)
                            invocation_horizon_hits += int(row["max_ply_hit"]); invocation_horizon_games += 1
                        if {row["child_owner"] for row in games} != {0, 1}:
                            raise RuntimeError("R6 role swap identity failure")
                        metrics = [dict(metric) for game in (owner0, owner1) for metric in _value(game, "search_metrics", ())]
                        depth_child = [m for m in metrics if m.get("engine_role") == "child"]
                        invocation_depth_hits += sum(int(int(m.get("completed_depth", 0)) >= MAX_DEPTH) for m in depth_child); invocation_depth_count += len(depth_child)
                        score = float(_value(pair, "child_pair_score")); invocation_scores.append(score)
                        pair_status = "EXPLICIT_CENSOR" if any(bool(m.get("censor_flag")) for m in metrics) else ("FALLBACK" if any(bool(m.get("used_fallback")) for m in metrics) else ("POSITIVE_DIRECTION" if score > 0.5 else "NEGATIVE_DIRECTION" if score < 0.5 else "MIXED_OR_UNCERTAIN"))
                        invocation_statuses.append(pair_status)
                        invocation_pair_rows.append({"pair_index": index, "pair_score": score, "status": pair_status, "games": games, "trace_hashes": [game["action_trace_sha256"] for game in games]})
                    # Commit an invocation atomically: malformed telemetry above
                    # contributes no score, pair, game, trace, or censor count.
                    scores.extend(invocation_scores); statuses.extend(invocation_statuses)
                    pair_rows = invocation_pair_rows
                    depth_hits += invocation_depth_hits; depth_count += invocation_depth_count
                    horizon_hits += invocation_horizon_hits; horizon_games += invocation_horizon_games
                    tape_results.append({"tape_seed": seed, "pair_count": len(pair_rows), "mean_pair_score": sum(invocation_scores) / PAIRS_PER_TAPE, "pairs": pair_rows, "wall_seconds": perf_counter() - started})
                    total["arena_pairs"] += len(pair_rows); total["arena_games"] += len(pair_rows) * 2; total["action_traces"] += len(pair_rows) * 2
                except Exception as exc:
                    statuses.append("EVIDENCE_INTEGRITY_FAILURE" if isinstance(exc, RuntimeError) else "OPERATIONALLY_UNRESOLVED")
                    tape_results.append({"tape_seed": seed, "pair_count": 0, "status": statuses[-1], "error": str(exc), "error_type": type(exc).__name__, "wall_seconds": perf_counter() - started})
                    break
                total["arena_invocations"] += 1
            tape_means = [row["mean_pair_score"] for row in tape_results if row.get("pair_count") == PAIRS_PER_TAPE]
            bootstrap = percentile_bootstrap_mean(scores, seed=BOOTSTRAP_SEEDS[matchup_name]) if len(scores) == PAIRS_PER_MATCHUP else {"mean": None, "lower": None, "upper": None, "seed": BOOTSTRAP_SEEDS[matchup_name], "resamples": BOOTSTRAP_RESAMPLES}
            classification = classify_matchup(scores=scores, tape_means=tape_means, statuses=statuses, depth_fraction=depth_hits / depth_count if depth_count else 0.0, horizon_fraction=horizon_hits / horizon_games if horizon_games else 0.0, bootstrap=bootstrap, strongest_vs_weakest=matchup_name == "4096_vs_256")
            control_statuses.append(classification)
            matchup_rows.append({"name": matchup_name, "pair_count": len(scores), "tape_mean_pair_scores": tape_means, "bootstrap": bootstrap, "pooled_censoring": {"child_depth_ceiling_fraction": depth_hits / depth_count if depth_count else 0.0, "strongest_vs_weakest_horizon_fraction": horizon_hits / horizon_games if horizon_games else 0.0}, "classification": classification, "statuses": statuses, "tape_results": tape_results})
        by_control[name] = {"matchups": matchup_rows, "classification": classify_control(matchup_rows, control_statuses), "invocations": len(matchup_rows) * TAPE_COUNT}
    authority = "CALIBRATION_READY" if all(row["classification"] == "STABLE_MONOTONE_POSITIVE" for row in by_control.values()) else "DEFER_CONTROL_NOT_READY"
    complete = (total["arena_invocations"], total["arena_pairs"], total["arena_games"], total["action_traces"]) == (TOTAL_INVOCATIONS, TOTAL_PAIRS, TOTAL_GAMES, TOTAL_TRACES)
    result = {"schema": RESULT_SCHEMA, "status": "R6_RESULT_COMPLETE" if complete else "R6_RESULT_INCOMPLETE", "experiment": EXPERIMENT, "prep_artifact": FROZEN_PREP_ARTIFACT, "prep_artifact_sha256": _sha256(prep_path), "prep_fingerprint": payload["prep_fingerprint"], "protocol_source_sha": payload["protocol_source_sha"], "result_sandbox_sha": _git_sha(root), "controls": by_control, "authority": authority, "boundary": {"a_c_prerequisite": "F86N-R1-V4-3", "layer_d_compute_authorized": False, "layer_d_compute_invocations": 0}, "derived_compute": total, "fixed_sample_authority": True, "pooled": False, "p0_observations_pooled": False, "r2_observations_pooled": False, "r3_observations_pooled": False, "r5_observations_pooled": False, "qualification_pilot_observations_pooled": False, "stage1_observations_pooled": False, "production_western_changed": False}
    output = Path(output)
    if not output.is_absolute(): output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--result", action="store_true"); parser.add_argument("--prep", type=Path, default=PREP_PATH); parser.add_argument("--result-output", type=Path, default=RESULT_PATH); args = parser.parse_args()
    if not args.result: parser.error("R6 executor requires --result")
    run_r6(prep_path=args.prep, output=args.result_output)


if __name__ == "__main__": main()
