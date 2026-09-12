"""Freeze a result-free, disjoint Western qualification-control PREP."""

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


PREP_PATH = ROOT / "docs/architecture/GENERICCHESS_F94_R5_WESTERN_QUALIFICATION_CONTROL_PREP.json"
P0_PREP_PATH = ROOT / "docs/architecture/GENERICCHESS_F94_R5_P0_DISJOINT_PILOT_PREP.json"
R5_PREP_PATH = ROOT / "docs/architecture/GENERICCHESS_F94_R5_R1_HORIZON_AWARE_PREP.json"
SCHEMA = "generic-chess-f94-r5-western-qualification-control-prep-v1"
EXPERIMENT = "GENERICCHESS-F94-R5-WESTERN-QUALIFICATION-CONTROL-V1"
TAPE_SEEDS = (9601, 9602, 9603)
DISJOINT_TAPE_SEEDS = (9401, 9402, 9403, 9501, 9502, 9503)
STRONGEST_NODES = 4096
WEAKEST_NODES = 256
MAX_DEPTH = 12
TT_MEGABYTES = 8
PAIR_COUNT = 1


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
            count=PAIR_COUNT,
            seed=seed,
            min_plies=2,
            max_plies=6,
        )
        for seed in TAPE_SEEDS
    )
    selected = []
    for seed, corpus in zip(TAPE_SEEDS, corpora):
        opening = corpus.openings[0]
        selected.append(
            {
                "tape_seed": seed,
                "corpus_id": corpus.corpus_id,
                "opening_count": len(corpus.openings),
                "selected_opening_index": opening.index,
                "selected_opening_seed": opening.opening_seed,
                "selected_target_plies": opening.target_plies,
                "selected_action_count": len(opening.actions),
                "selected_final_position_key": opening.final_position_key,
            }
        )
    if set(TAPE_SEEDS) & set(DISJOINT_TAPE_SEEDS):
        raise RuntimeError("qualification tape seeds overlap an existing protocol")
    payload = {
        "schema": SCHEMA,
        "status": "PREP_FROZEN",
        "experiment": EXPERIMENT,
        "source_sandbox_sha": _git_sha(root),
        "protocol_source_sha": _git_sha(root),
        "result_free": True,
        "not_public_builtin": True,
        "source_production_builder": "generic_chess.rules.western_chess.build_western_chess_ruleset",
        "source_production_fingerprint": PRODUCTION_RULESET_FINGERPRINT,
        "source_p0_prep_artifact": P0_PREP_PATH.relative_to(root).as_posix(),
        "source_p0_prep_artifact_sha256": _sha256(P0_PREP_PATH),
        "source_r5_prep_artifact": R5_PREP_PATH.relative_to(root).as_posix(),
        "source_r5_prep_artifact_sha256": _sha256(R5_PREP_PATH),
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
            "pair_count_per_tape": PAIR_COUNT,
            "tape_count": len(TAPE_SEEDS),
            "arena_invocations": len(TAPE_SEEDS),
            "arena_pairs": len(TAPE_SEEDS),
            "arena_games": len(TAPE_SEEDS) * 2,
            "action_traces": len(TAPE_SEEDS) * 2,
            "workers": 1,
        },
        "tape_seeds": list(TAPE_SEEDS),
        "disjoint_from_tape_seeds": list(DISJOINT_TAPE_SEEDS),
        "result_authority": "OBSERVED_NOT_POOLABLE; no Layer-D PASS",
        "opening_corpora": selected,
        "direction_rule": {
            "positive": "all three role-swapped pair scores > 0.5",
            "negative": "all three role-swapped pair scores < 0.5",
            "mixed_or_uncertain": "any tie or inconsistent tape signs",
            "depth_censor": "strongest-vs-weakest child completed-depth hit fraction >= 0.5",
            "horizon_censor": "strongest-vs-weakest max-ply hit fraction >= 0.5",
            "aggregation": "candidate_level_pooled_across_three_tapes",
        },
    }
    payload["prep_fingerprint"] = stable_sha256(payload)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    build_prep()
