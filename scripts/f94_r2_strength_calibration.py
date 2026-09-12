"""Freeze and run the F94-R2 real strength-response calibration.

PREP generation is deliberately separate from RESULT execution.  The PREP
subcommand materializes all three evaluator-neutral opening corpora and
records checkpoint/evaluator identities before any Arena call is allowed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.benchmark.strength_response import (
    DEFAULT_BUDGETS,
    StrengthResponsePrep,
    prepare_strength_response,
    measure_strength_response,
)
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.openings import generate_arena_openings
from generic_chess.learning.arena import ArenaConfig, run_arena
from generic_chess.learning.statistics import bootstrap_pair_mean_ci
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.learning.serialization import stable_sha256
from generic_chess.rules.compiler import compile_ruleset_for_execution, compile_semantic_ruleset
from generic_chess.rules.compiler import compile_ruleset
sys.path.insert(0, str(ROOT))
from scripts.f87a_ruleset_qualification import _controls, _semantic_compiled


PREP_PATH = ROOT / "docs/architecture/GENERICCHESS_F94_R2_STRENGTH_RESPONSE_PREP.json"
RESULT_PATH = ROOT / ".generic_chess_flow" / "f94-r2-strength-response-result.json"
STAGE0_PREP_PATH = ROOT / "docs/architecture/GENERICCHESS_F94_R2_STAGE0_PREP.json"
STAGE0_RESULT_PATH = ROOT / ".generic_chess_flow" / "f94-r2-stage0-result.json"
R3_PREP_PATH = ROOT / "docs/architecture/GENERICCHESS_F94_R3_NONBINDING_DEPTH_CALIBRATION_PREP.json"
EXPERIMENT = "GENERICCHESS-F94-R2-REAL-STRENGTH-CALIBRATION"
TAPE_SEEDS = (9401, 9402, 9403)
PAIR_COUNT = 6
MAX_DEPTH = 12
TT_MEGABYTES = 8
BOUNDARY_NAME = "F86N-R1 boundary V4-3"
TARGET_NAMES = ("Built-in Western Chess", "Built-in Standard Shogi", BOUNDARY_NAME)


def _ruleset_for(control: dict[str, Any]):
    if "builder" in control:
        ruleset = control["builder"]()
    else:
        from generic_chess.rules.schema import ruleset_from_dict

        ruleset = ruleset_from_dict(control["ruleset"])
    if control["name"] == BOUNDARY_NAME:
        compiled = compile_ruleset(ruleset, allow_semantic_actions=bool(ruleset.semantic_actions))
    else:
        compiled = _semantic_compiled(control)
    profile = build_ruleset_profile(
        compile_ruleset_for_execution(ruleset), EvaluationConfig()
    )
    return compiled, profile


def _git_sha() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _prep_candidate(control: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    compiled, profile = _ruleset_for(control)
    checkpoint = LearnableMaterialCheckpoint.from_profile(compiled, profile)
    corpora = tuple(
        generate_arena_openings(
            compiled,
            count=PAIR_COUNT,
            seed=seed,
            min_plies=2,
            max_plies=6,
        )
        for seed in TAPE_SEEDS
    )
    prep = prepare_strength_response(
        compiled,
        evaluator_identity=checkpoint.evaluator_version,
        candidate_fingerprint=checkpoint.checkpoint_id,
        opening_corpora=corpora,
        budget_ladder=DEFAULT_BUDGETS,
        max_depth=MAX_DEPTH,
        pair_count=PAIR_COUNT,
        tape_seeds=TAPE_SEEDS,
        tt_megabytes=TT_MEGABYTES,
    )
    return {
        "name": control["name"],
        "class": control["class"],
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "checkpoint_id": checkpoint.checkpoint_id,
        "evaluator_identity": checkpoint.evaluator_version,
        "layer_a_status": report["layers"]["A"],
        "layer_c_status": report["layers"]["C"],
        "layer_d_prerequisite": (
            "READY" if report["layers"]["A"] == "PASS" and report["layers"]["C"] == "PASS"
            else "SHORT_CIRCUIT"
        ),
        "prep": prep.to_dict(),
        "opening_corpora": [
            {
                "tape_seed": seed,
                "corpus_id": corpus.corpus_id,
                "opening_count": len(corpus.openings),
                "opening_seeds": [opening.opening_seed for opening in corpus.openings],
            }
            for seed, corpus in zip(TAPE_SEEDS, corpora)
        ],
    }


def build_prep(root: Path = ROOT, output: Path = PREP_PATH) -> dict[str, Any]:
    controls = {control["name"]: control for control in _controls(root)}
    reports = json.loads(
        (root / "artifacts/f87a_ruleset_qualification/reports.json").read_text(encoding="utf-8")
    )
    candidates = []
    for name in TARGET_NAMES:
        candidates.append(_prep_candidate(controls[name], reports[name]))
    payload = {
        "schema": "generic-chess-f94-r2-prep-v1",
        "status": "PREP_FROZEN",
        "experiment": EXPERIMENT,
        "source_sandbox_sha": _git_sha(),
        "budgets": {
            "nodes_per_move": list(DEFAULT_BUDGETS),
            "max_depth": MAX_DEPTH,
            "tt_megabytes": TT_MEGABYTES,
            "pair_count_per_tape": PAIR_COUNT,
            "tape_seeds": list(TAPE_SEEDS),
            "arena_runs": len(TAPE_SEEDS) * 3,
        },
        "candidates": candidates,
        "result_free": True,
        "classification_rule": "pooled strongest-vs-weakest positive, monotone adjacent response, no fallback, high-budget depth-ceiling fraction below 0.5, no mixed tape aggregate",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def _sha256_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _load_frozen_prep(path: Path = PREP_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if (
        payload.get("schema") != "generic-chess-f94-r2-prep-v1"
        or payload.get("status") != "PREP_FROZEN"
        or payload.get("experiment") != EXPERIMENT
        or payload.get("result_free") is not True
    ):
        raise RuntimeError("F94-R2 RESULT requires the frozen result-free PREP artifact")
    if payload.get("budgets", {}).get("arena_runs") != 9:
        raise RuntimeError("F94-R2 PREP arena-run budget is not frozen at 9")
    if [row.get("name") for row in payload.get("candidates", [])] != list(TARGET_NAMES):
        raise RuntimeError("F94-R2 PREP candidate set/order does not match the frozen protocol")
    return payload


def _assert_regenerated_matches(
    frozen: dict[str, Any], regenerated: dict[str, Any]
) -> None:
    for key in (
        "name",
        "class",
        "ruleset_fingerprint",
        "checkpoint_id",
        "evaluator_identity",
        "layer_a_status",
        "layer_c_status",
        "layer_d_prerequisite",
        "opening_corpora",
    ):
        if frozen.get(key) != regenerated.get(key):
            raise RuntimeError(f"F94-R2 frozen identity mismatch: {key}")
    if frozen.get("prep") != regenerated.get("prep"):
        raise RuntimeError("F94-R2 PREP fingerprint or frozen parameters changed")


def run_result(root: Path = ROOT, prep_path: Path = PREP_PATH, output: Path | None = None) -> dict[str, Any]:
    """Execute only the already frozen RESULT; never regenerate PREP output."""

    prep_path = Path(prep_path)
    if not prep_path.is_absolute():
        prep_path = root / prep_path
    if output is not None:
        output = Path(output)
    frozen = _load_frozen_prep(prep_path)
    controls = {control["name"]: control for control in _controls(root)}
    reports = json.loads(
        (root / "artifacts/f87a_ruleset_qualification/reports.json").read_text(encoding="utf-8")
    )
    candidate_results: list[dict[str, Any]] = []
    total_arena_invocations = 0
    total_arena_games = 0
    for frozen_candidate in frozen["candidates"]:
        name = frozen_candidate["name"]
        control = controls[name]
        regenerated = _prep_candidate(control, reports[name])
        _assert_regenerated_matches(frozen_candidate, regenerated)
        compiled, profile = _ruleset_for(control)
        checkpoint = LearnableMaterialCheckpoint.from_profile(compiled, profile)
        prep_data = dict(frozen_candidate["prep"])
        prep_data.pop("prep_fingerprint", None)
        prep = StrengthResponsePrep(**{
            **prep_data,
            "budget_ladder": tuple(prep_data["budget_ladder"]),
            "opening_seeds": tuple(prep_data["opening_seeds"]),
            "tape_seeds": tuple(prep_data["tape_seeds"]),
            "opening_corpus_ids": tuple(prep_data["opening_corpus_ids"]),
        })
        corpora = tuple(
            generate_arena_openings(
                compiled,
                count=prep.pair_count,
                seed=seed,
                min_plies=2,
                max_plies=6,
            )
            for seed in prep.tape_seeds
        )
        actual_corpus_ids = tuple(corpus.corpus_id for corpus in corpora)
        if actual_corpus_ids != prep.opening_corpus_ids:
            raise RuntimeError(f"{name} regenerated corpus identity does not match PREP")
        base_report = SimpleNamespace(layers={"A": reports[name]["layers"]["A"], "C": reports[name]["layers"]["C"]})
        if frozen_candidate["layer_d_prerequisite"] != "READY":
            result = measure_strength_response(
                compiled=compiled,
                prep=prep,
                base_report=base_report,
            )
            total_arena_invocations += 0
        else:
            native_rules = compile_native_semantic_rules(compiled)

            def runner(compiled_arg, native_arg, parent_arg, child_arg, config, corpus, *, capture_search_metrics):
                return run_arena(
                    compiled_arg,
                    native_arg,
                    parent_arg,
                    child_arg,
                    config,
                    openings=corpus,
                    capture_search_metrics=capture_search_metrics,
                )

            result = measure_strength_response(
                compiled=compiled,
                native_rules=native_rules,
                parent=checkpoint,
                child=checkpoint,
                prep=prep,
                opening_corpora=corpora,
                arena_runner=runner,
                capture_search_metrics=True,
                base_report=base_report,
            )
            total_arena_invocations += len(prep.tape_seeds) * 3
            total_arena_games += result.compute_usage["arena_games"]
        candidate_results.append({
            "name": name,
            "class": frozen_candidate["class"],
            "ruleset_fingerprint": frozen_candidate["ruleset_fingerprint"],
            "checkpoint_id": frozen_candidate["checkpoint_id"],
            "evaluator_identity": frozen_candidate["evaluator_identity"],
            "layer_a_status": frozen_candidate["layer_a_status"],
            "layer_c_status": frozen_candidate["layer_c_status"],
            "layer_d_prerequisite": frozen_candidate["layer_d_prerequisite"],
            "regenerated_corpus_ids": list(actual_corpus_ids),
            "prep_fingerprint": prep.prep_fingerprint,
            "result": result.to_dict(),
        })
    payload = {
        "schema": "generic-chess-f94-r2-result-v1",
        "status": "RESULT_COMPLETE",
        "experiment": EXPERIMENT,
        "prep_artifact": prep_path.relative_to(root).as_posix(),
        "prep_artifact_sha256": _sha256_bytes(prep_path),
        "prep_source_sandbox_sha": frozen["source_sandbox_sha"],
        "result_sandbox_sha": _git_sha(),
        "budgets": frozen["budgets"],
        "derived_compute": {
            "arena_invocations": total_arena_invocations,
            "arena_games": total_arena_games,
            "boundary_arena_invocations": 0,
        },
        "candidates": candidate_results,
        "no_tuning": True,
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def _stage0_fingerprint(payload: dict[str, Any]) -> str:
    unsigned = dict(payload)
    unsigned.pop("stage0_prep_fingerprint", None)
    return stable_sha256(unsigned)


def _r3_prep_fingerprint(payload: dict[str, Any]) -> str:
    unsigned = dict(payload)
    unsigned.pop("r3_prep_fingerprint", None)
    return stable_sha256(unsigned)


def build_stage0_prep(
    root: Path = ROOT,
    source_path: Path = PREP_PATH,
    output: Path = STAGE0_PREP_PATH,
) -> dict[str, Any]:
    """Create the separate, result-free one-pair Stage-0 PREP authority."""

    source_path = Path(source_path)
    if not source_path.is_absolute():
        source_path = root / source_path
    output = Path(output)
    source = _load_frozen_prep(source_path)
    controls = {control["name"]: control for control in _controls(root)}
    reports = json.loads(
        (root / "artifacts/f87a_ruleset_qualification/reports.json").read_text(encoding="utf-8")
    )
    candidates: list[dict[str, Any]] = []
    for source_candidate in source["candidates"]:
        name = source_candidate["name"]
        control = controls[name]
        regenerated = _prep_candidate(control, reports[name])
        _assert_regenerated_matches(source_candidate, regenerated)
        compiled, _profile = _ruleset_for(control)
        corpora = tuple(
            generate_arena_openings(
                compiled,
                count=source_candidate["prep"]["pair_count"],
                seed=seed,
                min_plies=2,
                max_plies=6,
            )
            for seed in source_candidate["prep"]["tape_seeds"]
        )
        source_rows = source_candidate["opening_corpora"]
        if tuple(corpus.corpus_id for corpus in corpora) != tuple(row["corpus_id"] for row in source_rows):
            raise RuntimeError(f"{name} Stage-0 corpus identity does not match source PREP")
        selected = []
        for corpus, source_row in zip(corpora, source_rows):
            opening = corpus.openings[0]
            if opening.opening_seed != source_row["opening_seeds"][0]:
                raise RuntimeError(f"{name} Stage-0 opening seed does not match source PREP")
            selected.append({
                "tape_seed": corpus.seed,
                "corpus_id": corpus.corpus_id,
                "selected_opening_index": opening.index,
                "selected_opening_seed": opening.opening_seed,
                "selected_target_plies": opening.target_plies,
                "selected_action_count": len(opening.actions),
                "selected_final_position_key": opening.final_position_key,
            })
        candidates.append({
            "name": name,
            "class": source_candidate["class"],
            "ruleset_fingerprint": source_candidate["ruleset_fingerprint"],
            "checkpoint_id": source_candidate["checkpoint_id"],
            "evaluator_identity": source_candidate["evaluator_identity"],
            "layer_a_status": source_candidate["layer_a_status"],
            "layer_c_status": source_candidate["layer_c_status"],
            "layer_d_prerequisite": source_candidate["layer_d_prerequisite"],
            "source_prep_fingerprint": source_candidate["prep"]["prep_fingerprint"],
            "opening_corpora": selected,
        })
    payload = {
        "schema": "generic-chess-f94-r2-stage0-prep-v1",
        "status": "STAGE0_PREP_FROZEN",
        "experiment": "GENERICCHESS-F94-R2-STAGE0-RUNTIME-CALIBRATION",
        "source_prep_artifact": _artifact_path(root, source_path),
        "source_prep_artifact_sha256": _sha256_bytes(source_path),
        "source_prep_source_sandbox_sha": source["source_sandbox_sha"],
        "budgets": {
            "strongest_nodes_per_move": 4096,
            "weakest_nodes_per_move": 256,
            "max_depth": 12,
            "tt_megabytes": 8,
            "pair_count_per_tape": 1,
            "tape_count_per_candidate": 3,
            "ready_candidate_count": 2,
            "arena_invocations": 6,
            "arena_games": 12,
            "workers": 1,
        },
        "direction_rule": {
            "positive": "all three tape pair scores > 0.5",
            "negative": "all three tape pair scores < 0.5",
            "mixed_or_uncertain": "any tape pair score == 0.5 or tape score signs are inconsistent",
            "override_precedence": [
                "DEPTH_CENSORED",
                "FALLBACK",
                "OPERATIONALLY_UNRESOLVED",
                "POSITIVE_DIRECTION",
                "NEGATIVE_DIRECTION",
                "MIXED_OR_UNCERTAIN",
            ],
            "ci": "descriptive pooled effect interval only; three paired observations are not formal significance authority",
        },
        "candidates": candidates,
        "boundary_control": {
            "name": "F86N-R1 boundary V4-3",
            "layer_a_status": "PASS",
            "layer_c_status": "DEFER",
            "prerequisite": "PREREQUISITE_A_C_NOT_PASS",
            "arena_invocations": 0,
            "compute": 0,
        },
        "result_free": True,
    }
    payload["stage0_prep_fingerprint"] = _stage0_fingerprint(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def build_r3_nonbinding_depth_calibration_prep(
    root: Path = ROOT,
    source_path: Path = STAGE0_PREP_PATH,
    output: Path = R3_PREP_PATH,
) -> dict[str, Any]:
    """Freeze an independent R3 protocol without running Arena.

    R2 is prior protocol-calibration evidence only.  R3 deliberately retains
    its own result-free PREP identity so no R2 observation can be pooled into a
    later R3 result.
    """

    source_path = Path(source_path)
    if not source_path.is_absolute():
        source_path = root / source_path
    output = Path(output)
    r2 = _load_stage0_prep(source_path)
    r2_budgets = r2["budgets"]
    if r2_budgets.get("max_depth") != 12:
        raise RuntimeError("R3 calibration requires the observed R2 depth-12 protocol")
    if (
        r2_budgets.get("strongest_nodes_per_move") != 4096
        or r2_budgets.get("weakest_nodes_per_move") != 256
        or r2_budgets.get("pair_count_per_tape") != 1
        or r2_budgets.get("tape_count_per_candidate") != 3
        or r2_budgets.get("workers") != 1
    ):
        raise RuntimeError("R3 calibration requires the frozen R2 measurement design")

    budgets = dict(r2_budgets)
    budgets["max_depth"] = 64
    payload = {
        "schema": "generic-chess-f94-r3-nonbinding-depth-calibration-prep-v1",
        "status": "R3_PREP_FROZEN",
        "experiment": "GENERICCHESS-F94-R3-NONBINDING-DEPTH-CALIBRATION",
        "source_r2_stage0_prep_artifact": _artifact_path(root, source_path),
        "source_r2_stage0_prep_artifact_sha256": _sha256_bytes(source_path),
        "source_r2_stage0_prep_fingerprint": r2["stage0_prep_fingerprint"],
        "r2_protocol_calibration": {
            "classification": "OBSERVED_NOT_POOLABLE",
            "reason": "R2 was observed before R3; its paired observations are protocol-calibration evidence only and must not be combined with any R3 sample.",
            "runtime_closeout_artifact": "docs/architecture/GENERICCHESS_F94_R2_STAGE0_RUNTIME_CLOSEOUT.md",
            "runtime_closeout_sandbox_sha": "fa03e3608fe3a3ed129f6caf40980860ef197ef8",
        },
        "budgets": budgets,
        "direction_rule": r2["direction_rule"],
        "candidates": r2["candidates"],
        "boundary_control": r2["boundary_control"],
        "design_change_from_r2": {
            "field": "max_depth",
            "r2_value": 12,
            "r3_value": 64,
            "reason": "The node budget, not a fixed shallow depth ceiling, must be the active search constraint for this calibration.",
        },
        "execution_authority": "NONE: this PREP does not authorize Arena, Heavy, Stage 1, the 216-game schedule, tuning, or any adjacent compute.",
        "result_free": True,
    }
    payload["r3_prep_fingerprint"] = _r3_prep_fingerprint(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def _stage0_status(pair_score: float, metrics: list[dict[str, Any]]) -> str:
    if any(int(row.get("completed_depth", 0)) >= MAX_DEPTH for row in metrics):
        return "DEPTH_CENSORED"
    if any(bool(row.get("used_fallback")) for row in metrics):
        return "FALLBACK"
    if pair_score > 0.5:
        return "POSITIVE_DIRECTION"
    if pair_score < 0.5:
        return "NEGATIVE_DIRECTION"
    return "MIXED_OR_UNCERTAIN"


def _stage0_overall_direction(statuses: list[str], scores: list[float]) -> str:
    """Apply the frozen Stage-0 override precedence before direction."""

    if "DEPTH_CENSORED" in statuses:
        return "DEPTH_CENSORED"
    if "FALLBACK" in statuses:
        return "FALLBACK"
    if "OPERATIONALLY_UNRESOLVED" in statuses or len(scores) != 3:
        return "OPERATIONALLY_UNRESOLVED"
    if all(score > 0.5 for score in scores):
        return "POSITIVE_DIRECTION"
    if all(score < 0.5 for score in scores):
        return "NEGATIVE_DIRECTION"
    return "MIXED_OR_UNCERTAIN"


def _load_stage0_prep(path: Path = STAGE0_PREP_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if (
        payload.get("schema") != "generic-chess-f94-r2-stage0-prep-v1"
        or payload.get("status") != "STAGE0_PREP_FROZEN"
        or payload.get("result_free") is not True
        or payload.get("stage0_prep_fingerprint") != _stage0_fingerprint(payload)
    ):
        raise RuntimeError("Stage-0 RESULT requires an untampered frozen staged PREP")
    if payload.get("budgets", {}).get("arena_invocations") != 6:
        raise RuntimeError("Stage-0 PREP arena invocation budget is not frozen at 6")
    return payload


def run_stage0(
    root: Path = ROOT,
    prep_path: Path = STAGE0_PREP_PATH,
    output: Path = STAGE0_RESULT_PATH,
) -> dict[str, Any]:
    """Run the bounded strongest-vs-weakest Stage-0 probe."""

    prep_path = Path(prep_path)
    if not prep_path.is_absolute():
        prep_path = root / prep_path
    output = Path(output)
    staged = _load_stage0_prep(prep_path)
    source_path = root / staged["source_prep_artifact"]
    if _sha256_bytes(source_path) != staged["source_prep_artifact_sha256"]:
        raise RuntimeError("Stage-0 source PREP artifact SHA does not match frozen authority")
    source = _load_frozen_prep(source_path)
    if source["source_sandbox_sha"] != staged["source_prep_source_sandbox_sha"]:
        raise RuntimeError("Stage-0 source PREP sandbox SHA does not match frozen authority")
    controls = {control["name"]: control for control in _controls(root)}
    reports = json.loads(
        (root / "artifacts/f87a_ruleset_qualification/reports.json").read_text(encoding="utf-8")
    )
    candidate_results: list[dict[str, Any]] = []
    actual_invocations = 0
    actual_games = 0
    for staged_candidate in staged["candidates"]:
        name = staged_candidate["name"]
        source_candidate = next(row for row in source["candidates"] if row["name"] == name)
        if staged_candidate["layer_d_prerequisite"] != "READY":
            if (
                staged_candidate["ruleset_fingerprint"] != source_candidate["ruleset_fingerprint"]
                or staged_candidate["checkpoint_id"] != source_candidate["checkpoint_id"]
                or staged_candidate["evaluator_identity"] != source_candidate["evaluator_identity"]
                or staged_candidate["source_prep_fingerprint"] != source_candidate["prep"]["prep_fingerprint"]
            ):
                raise RuntimeError(f"{name} Stage-0 prerequisite identity does not match source PREP")
            candidate_results.append({
                "name": name,
                "class": staged_candidate["class"],
                "ruleset_fingerprint": staged_candidate["ruleset_fingerprint"],
                "checkpoint_id": staged_candidate["checkpoint_id"],
                "evaluator_identity": staged_candidate["evaluator_identity"],
                "source_prep_fingerprint": staged_candidate["source_prep_fingerprint"],
                "stage0_prep_fingerprint": staged["stage0_prep_fingerprint"],
                "layer_a_status": staged_candidate["layer_a_status"],
                "layer_c_status": staged_candidate["layer_c_status"],
                "layer_d_prerequisite": staged_candidate["layer_d_prerequisite"],
                "status": "PREREQUISITE_A_C_NOT_PASS",
                "arena_invocations": 0,
                "arena_games": 0,
                "tape_results": [],
            })
            continue
        control = controls[name]
        regenerated = _prep_candidate(control, reports[name])
        _assert_regenerated_matches(source_candidate, regenerated)
        if (
            staged_candidate["ruleset_fingerprint"] != source_candidate["ruleset_fingerprint"]
            or staged_candidate["checkpoint_id"] != source_candidate["checkpoint_id"]
            or staged_candidate["evaluator_identity"] != source_candidate["evaluator_identity"]
            or staged_candidate["source_prep_fingerprint"] != source_candidate["prep"]["prep_fingerprint"]
        ):
            raise RuntimeError(f"{name} Stage-0 identity does not match source PREP")
        compiled, profile = _ruleset_for(control)
        checkpoint = LearnableMaterialCheckpoint.from_profile(compiled, profile)
        native_rules = compile_native_semantic_rules(compiled)
        tape_results: list[dict[str, Any]] = []
        candidate_invocations = 0
        candidate_games = 0
        for staged_tape in staged_candidate["opening_corpora"]:
            corpus = generate_arena_openings(
                compiled,
                count=source_candidate["prep"]["pair_count"],
                seed=staged_tape["tape_seed"],
                min_plies=2,
                max_plies=6,
            )
            if corpus.corpus_id != staged_tape["corpus_id"]:
                raise RuntimeError(f"{name} Stage-0 corpus identity changed")
            opening = corpus.openings[staged_tape["selected_opening_index"]]
            if (
                opening.opening_seed != staged_tape["selected_opening_seed"]
                or opening.final_position_key != staged_tape["selected_final_position_key"]
                or len(opening.actions) != staged_tape["selected_action_count"]
            ):
                raise RuntimeError(f"{name} Stage-0 selected opening identity changed")
            from time import perf_counter

            started = perf_counter()
            actual_invocations += 1
            candidate_invocations += 1
            try:
                summary = run_arena(
                    compiled,
                    native_rules,
                    checkpoint,
                    checkpoint,
                    ArenaConfig(
                        pairs=1,
                        nodes_per_move=4096,
                        parent_nodes_per_move=256,
                        child_nodes_per_move=4096,
                        max_depth=12,
                        tt_megabytes=8,
                        opening_seed=corpus.seed,
                        opening_count=1,
                        workers=1,
                    ),
                    openings=corpus,
                    capture_search_metrics=True,
                )
            except Exception as exc:
                tape_results.append({
                    "tape_seed": corpus.seed,
                    "corpus_id": corpus.corpus_id,
                    "selected_opening": {
                        "index": opening.index,
                        "opening_seed": opening.opening_seed,
                        "target_plies": opening.target_plies,
                        "action_count": len(opening.actions),
                        "final_position_key": opening.final_position_key,
                    },
                    "status": "OPERATIONALLY_UNRESOLVED",
                    "wall_seconds": perf_counter() - started,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                })
                break
            wall_seconds = perf_counter() - started
            pair = summary.pairs[0]
            games = [pair.game_child_owner0, pair.game_child_owner1]
            actual_games += len(games)
            candidate_games += len(games)
            metrics = [metric for game in games for metric in game.search_metrics]
            searched_nodes = sum(int(metric.get("nodes", 0)) for metric in metrics)
            search_seconds = sum(float(metric.get("elapsed_seconds", 0.0)) for metric in metrics)
            tape_results.append({
                "tape_seed": corpus.seed,
                "corpus_id": corpus.corpus_id,
                "selected_opening": {
                    "index": opening.index,
                    "opening_seed": opening.opening_seed,
                    "target_plies": opening.target_plies,
                    "action_count": len(opening.actions),
                    "final_position_key": opening.final_position_key,
                },
                "pair_score": pair.child_pair_score,
                "role_swap_games": [
                    {
                        "child_owner": game.child_owner,
                        "winner": game.winner,
                        "result": game.result,
                        "plies": game.plies,
                        "search_metrics": list(game.search_metrics),
                    }
                    for game in games
                ],
                "actual_searched_nodes": searched_nodes,
                "nps": searched_nodes / search_seconds if search_seconds > 0 else None,
                "wall_seconds": wall_seconds,
                "max_completed_depth": max(
                    (int(metric.get("completed_depth", 0)) for metric in metrics),
                    default=0,
                ),
                "fallback": any(bool(metric.get("used_fallback")) for metric in metrics),
                "status": _stage0_status(pair.child_pair_score, metrics),
            })
        scores = [float(row["pair_score"]) for row in tape_results]
        differences = [score - 0.5 for score in scores]
        statuses = [row["status"] for row in tape_results]
        direction = _stage0_overall_direction(statuses, scores)
        candidate_results.append({
            "name": name,
            "class": staged_candidate["class"],
            "ruleset_fingerprint": staged_candidate["ruleset_fingerprint"],
            "checkpoint_id": staged_candidate["checkpoint_id"],
            "evaluator_identity": staged_candidate["evaluator_identity"],
            "source_prep_fingerprint": staged_candidate["source_prep_fingerprint"],
            "stage0_prep_fingerprint": staged["stage0_prep_fingerprint"],
            "tape_results": tape_results,
            "arena_invocations": candidate_invocations,
            "arena_games": candidate_games,
            "pooled_pair_count": len(scores),
            "pooled_mean_pair_score": sum(scores) / len(scores) if scores else None,
            "pooled_effect": sum(differences) / len(differences) if differences else None,
            "descriptive_pooled_effect_ci": list(
                bootstrap_pair_mean_ci(
                    differences,
                    confidence=0.95,
                    resamples=10000,
                    seed=271828,
                ) if differences else (None, None)
            ),
            "direction": direction,
        })
    payload = {
        "schema": "generic-chess-f94-r2-stage0-result-v1",
        "status": (
            "STAGE0_RESULT_COMPLETE"
            if actual_invocations == staged["budgets"]["arena_invocations"]
            and actual_games == staged["budgets"]["arena_games"]
            else "STAGE0_RESULT_INCOMPLETE"
        ),
        "experiment": "GENERICCHESS-F94-R2-STAGE0-RUNTIME-CALIBRATION",
        "stage0_prep_artifact": _artifact_path(root, prep_path),
        "stage0_prep_artifact_sha256": _sha256_bytes(prep_path),
        "stage0_prep_fingerprint": staged["stage0_prep_fingerprint"],
        "source_prep_source_sandbox_sha": staged["source_prep_source_sandbox_sha"],
        "result_sandbox_sha": _git_sha(),
        "candidates": candidate_results,
        "boundary_control": staged["boundary_control"],
        "derived_compute": {
            "arena_invocations": actual_invocations,
            "arena_games": actual_games,
            "boundary_arena_invocations": 0,
        },
        "not_layer_d_authority": True,
        "no_tuning": True,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", action="store_true")
    parser.add_argument("--stage0-prep", action="store_true")
    parser.add_argument("--r3-prep", action="store_true")
    parser.add_argument("--stage0", action="store_true")
    parser.add_argument("--output", type=Path, default=PREP_PATH)
    parser.add_argument("--prep", type=Path, default=PREP_PATH)
    parser.add_argument("--result-output", type=Path, default=RESULT_PATH)
    parser.add_argument("--stage0-prep-output", type=Path, default=STAGE0_PREP_PATH)
    parser.add_argument("--r3-source-prep", type=Path, default=STAGE0_PREP_PATH)
    parser.add_argument("--r3-prep-output", type=Path, default=R3_PREP_PATH)
    parser.add_argument("--stage0-result-output", type=Path, default=STAGE0_RESULT_PATH)
    args = parser.parse_args()
    if args.stage0_prep:
        payload = build_stage0_prep(ROOT, args.prep, args.stage0_prep_output)
        print(json.dumps({"status": payload["status"], "candidates": len(payload["candidates"]), "output": str(args.stage0_prep_output)}, sort_keys=True))
    elif args.r3_prep:
        payload = build_r3_nonbinding_depth_calibration_prep(ROOT, args.r3_source_prep, args.r3_prep_output)
        print(json.dumps({"status": payload["status"], "candidates": len(payload["candidates"]), "output": str(args.r3_prep_output)}, sort_keys=True))
    elif args.stage0:
        payload = run_stage0(ROOT, args.prep, args.stage0_result_output)
        print(json.dumps({"status": payload["status"], "candidates": len(payload["candidates"]), "output": str(args.stage0_result_output), "arena_invocations": payload["derived_compute"]["arena_invocations"]}, sort_keys=True))
    elif args.result:
        payload = run_result(ROOT, args.prep, args.result_output)
        print(json.dumps({"status": payload["status"], "candidates": len(payload["candidates"]), "output": str(args.result_output), "arena_invocations": payload["derived_compute"]["arena_invocations"]}, sort_keys=True))
    else:
        payload = build_prep(ROOT, args.output)
        print(json.dumps({"status": payload["status"], "candidates": len(payload["candidates"]), "output": str(args.output)}, sort_keys=True))


if __name__ == "__main__":
    main()
