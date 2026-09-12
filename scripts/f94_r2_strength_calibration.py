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
from generic_chess.learning.arena import run_arena
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.rules.compiler import compile_ruleset_for_execution, compile_semantic_ruleset
from generic_chess.rules.compiler import compile_ruleset
sys.path.insert(0, str(ROOT))
from scripts.f87a_ruleset_qualification import _controls, _semantic_compiled


PREP_PATH = ROOT / "docs/architecture/GENERICCHESS_F94_R2_STRENGTH_RESPONSE_PREP.json"
RESULT_PATH = ROOT / ".generic_chess_flow" / "f94-r2-strength-response-result.json"
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", action="store_true")
    parser.add_argument("--output", type=Path, default=PREP_PATH)
    parser.add_argument("--prep", type=Path, default=PREP_PATH)
    parser.add_argument("--result-output", type=Path, default=RESULT_PATH)
    args = parser.parse_args()
    if args.result:
        payload = run_result(ROOT, args.prep, args.result_output)
        print(json.dumps({"status": payload["status"], "candidates": len(payload["candidates"]), "output": str(args.result_output), "arena_invocations": payload["derived_compute"]["arena_invocations"]}, sort_keys=True))
    else:
        payload = build_prep(ROOT, args.output)
        print(json.dumps({"status": payload["status"], "candidates": len(payload["candidates"]), "output": str(args.output)}, sort_keys=True))


if __name__ == "__main__":
    main()
