"""Freeze and run the F94-R2 real strength-response calibration.

PREP generation is deliberately separate from RESULT execution.  The PREP
subcommand materializes all three evaluator-neutral opening corpora and
records checkpoint/evaluator identities before any Arena call is allowed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.benchmark.strength_response import (
    DEFAULT_BUDGETS,
    prepare_strength_response,
)
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.openings import generate_arena_openings
from generic_chess.rules.compiler import compile_ruleset_for_execution, compile_semantic_ruleset
from generic_chess.rules.compiler import compile_ruleset
sys.path.insert(0, str(ROOT))
from scripts.f87a_ruleset_qualification import _controls, _semantic_compiled


PREP_PATH = ROOT / "docs/architecture/GENERICCHESS_F94_R2_STRENGTH_RESPONSE_PREP.json"
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=PREP_PATH)
    args = parser.parse_args()
    payload = build_prep(ROOT, args.output)
    print(json.dumps({"status": payload["status"], "candidates": len(payload["candidates"]), "output": str(args.output)}, sort_keys=True))


if __name__ == "__main__":
    main()
