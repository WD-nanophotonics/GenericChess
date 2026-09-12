"""Freeze the result-free Western qualification-control Stage-1 PREP."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.openings import generate_arena_openings
from generic_chess.learning.serialization import stable_sha256
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_to_dict
from scripts.f94_r5_western_qualification_control import (
    QUALIFICATION_CONTROL_NAME,
    QUALIFICATION_CHECKPOINT_ID,
    QUALIFICATION_RULESET_FINGERPRINT,
    QUALIFICATION_REPETITION_LIMIT,
    PRODUCTION_RULESET_FINGERPRINT,
    build_western_chess_qualification_control,
)


PREP_PATH = ROOT / "docs/architecture/GENERICCHESS_F94_R5_WESTERN_QUALIFICATION_CONTROL_STAGE1_PREP.json"
QUALIFICATION_PREP_PATH = ROOT / "docs/architecture/GENERICCHESS_F94_R5_WESTERN_QUALIFICATION_CONTROL_PREP.json"
SCHEMA = "generic-chess-f94-r5-western-qualification-control-stage1-prep-v1"
EXPERIMENT = "GENERICCHESS-F94-R5-WESTERN-QUALIFICATION-CONTROL-STAGE1-V1"
TAPE_SEEDS = (9701, 9702, 9703)
DISALLOWED_TAPE_SEEDS = (9401, 9402, 9403, 9501, 9502, 9503, 9601, 9602, 9603)
STRONGEST_NODES = 4096
WEAKEST_NODES = 256
MAX_DEPTH = 12
TT_MEGABYTES = 8
PAIRS_PER_TAPE = 6
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 9701001
CONFIDENCE_LEVEL = 0.95


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_sha(root: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def _ruleset_delta(production, control) -> list[str]:
    left = ruleset_to_dict(production, include_metadata=True)
    right = ruleset_to_dict(control, include_metadata=True)
    return sorted(key for key in left if left[key] != right[key])


def build_prep(root: Path = ROOT, output: Path = PREP_PATH) -> dict[str, Any]:
    production = __import__(
        "generic_chess.rules.western_chess", fromlist=["build_western_chess_ruleset"]
    ).build_western_chess_ruleset()
    control = build_western_chess_qualification_control()
    if _ruleset_delta(production, control) != ["repetition_limit"]:
        raise RuntimeError("qualification control must have exactly one gameplay delta")
    production_compiled = compile_ruleset_for_execution(production)
    control_compiled = compile_ruleset_for_execution(control)
    if production_compiled.ruleset_fingerprint != PRODUCTION_RULESET_FINGERPRINT:
        raise RuntimeError("production Western fingerprint changed")
    if control_compiled.ruleset_fingerprint != QUALIFICATION_RULESET_FINGERPRINT:
        raise RuntimeError("qualification control fingerprint changed")
    profile = build_ruleset_profile(control_compiled, EvaluationConfig())
    checkpoint = LearnableMaterialCheckpoint.from_profile(control_compiled, profile)
    if checkpoint.checkpoint_id != QUALIFICATION_CHECKPOINT_ID:
        raise RuntimeError("qualification checkpoint identity changed")
    corpora = tuple(
        generate_arena_openings(
            control_compiled,
            count=PAIRS_PER_TAPE,
            seed=seed,
            min_plies=2,
            max_plies=6,
        )
        for seed in TAPE_SEEDS
    )
    selected = []
    for seed, corpus in zip(TAPE_SEEDS, corpora):
        openings = []
        for opening in corpus.openings:
            openings.append(
                {
                    "index": opening.index,
                    "opening_seed": opening.opening_seed,
                    "target_plies": opening.target_plies,
                    "action_count": len(opening.actions),
                    "final_position_key": opening.final_position_key,
                }
            )
        selected.append(
            {
                "tape_seed": seed,
                "corpus_id": corpus.corpus_id,
                "opening_count": len(corpus.openings),
                "openings": openings,
            }
        )
    if set(TAPE_SEEDS) & set(DISALLOWED_TAPE_SEEDS):
        raise RuntimeError("Stage-1 tape seeds overlap a disallowed protocol")
    payload = {
        "schema": SCHEMA,
        "status": "PREP_FROZEN",
        "experiment": EXPERIMENT,
        "source_sandbox_sha": _git_sha(root),
        "protocol_source_sha": _git_sha(root),
        "result_free": True,
        "not_public_builtin": True,
        "qualification_prep_artifact": QUALIFICATION_PREP_PATH.relative_to(root).as_posix(),
        "qualification_prep_artifact_sha256": _sha256(QUALIFICATION_PREP_PATH),
        "source_production_builder": "generic_chess.rules.western_chess.build_western_chess_ruleset",
        "source_production_fingerprint": PRODUCTION_RULESET_FINGERPRINT,
        "qualification_control": {
            "name": QUALIFICATION_CONTROL_NAME,
            "production_ruleset_fingerprint": PRODUCTION_RULESET_FINGERPRINT,
            "qualification_ruleset_fingerprint": QUALIFICATION_RULESET_FINGERPRINT,
            "qualification_checkpoint_id": checkpoint.checkpoint_id,
            "evaluator_identity": checkpoint.evaluator_version,
            "repetition_limit": QUALIFICATION_REPETITION_LIMIT,
            "repetition_policy": control.repetition_policy,
            "max_ply": control.max_ply,
            "gameplay_delta": ["repetition_limit: 100000 -> 5"],
        },
        "budgets": {
            "strongest_nodes_per_move": STRONGEST_NODES,
            "weakest_nodes_per_move": WEAKEST_NODES,
            "max_depth": MAX_DEPTH,
            "tt_megabytes": TT_MEGABYTES,
            "pairs_per_tape": PAIRS_PER_TAPE,
            "tape_count": len(TAPE_SEEDS),
            "arena_invocations": len(TAPE_SEEDS),
            "arena_pairs": len(TAPE_SEEDS) * PAIRS_PER_TAPE,
            "arena_games": len(TAPE_SEEDS) * PAIRS_PER_TAPE * 2,
            "action_traces": len(TAPE_SEEDS) * PAIRS_PER_TAPE * 2,
            "workers": 1,
        },
        "tape_seeds": list(TAPE_SEEDS),
        "disallowed_tape_seeds": list(DISALLOWED_TAPE_SEEDS),
        "result_authority": "OBSERVED_NOT_POOLABLE; no Layer-D PASS",
        "opening_corpora": selected,
        "bootstrap": {
            "method": "percentile_bootstrap_mean_pair_score",
            "resamples": BOOTSTRAP_RESAMPLES,
            "seed": BOOTSTRAP_SEED,
            "confidence_level": CONFIDENCE_LEVEL,
            "lower_percentile": (1.0 - CONFIDENCE_LEVEL) / 2.0,
            "upper_percentile": 1.0 - (1.0 - CONFIDENCE_LEVEL) / 2.0,
            "sample_scope": "Stage-1's 18 pair scores only",
        },
        "direction_rule": {
            "unresolved": "fallback, explicit censor, or operational failure",
            "depth_censor": "pooled strongest-vs-weakest child completed-depth hit fraction >= 0.5",
            "horizon_censor": "pooled strongest-vs-weakest max-ply hit fraction >= 0.5",
            "stable_positive_control": "all three tape means > 0.5 and independent 18-pair 95% bootstrap CI lower > 0.5",
            "mixed_or_uncertain": "any tape mean <= 0.5 or pooled CI lower <= 0.5",
            "aggregation": "candidate_level_pooled_across_18_stage1_pairs; old pilots excluded",
        },
    }
    payload["prep_fingerprint"] = stable_sha256(payload)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    build_prep()
