"""Freeze the result-free F94 R6 Layer-D authority refresh protocol.

This module only derives identities and opening corpora.  It never compiles a
native engine and never calls Arena; the resulting JSON is the fixed sample
authority consumed by the executor after an independently reviewed freeze.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.openings import generate_arena_openings
from generic_chess.learning.serialization import stable_sha256
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.f94_r5_western_qualification_control import (
    QUALIFICATION_CONTROL_NAME,
    build_western_chess_qualification_control,
)

ROOT = Path(__file__).resolve().parents[1]
PREP_PATH = ROOT / "docs/architecture/GENERICCHESS_F94_R6_LAYER_D_AUTHORITY_REFRESH_PREP.json"
SCHEMA = "generic-chess-f94-r6-layer-d-authority-refresh-prep-v1"
EXPERIMENT = "GENERICCHESS-F94-R6-LAYER-D-AUTHORITY-REFRESH-V1"
RESULT_SCHEMA = "generic-chess-f94-r6-layer-d-authority-refresh-result-v1"
TAPE_SEEDS = (9801, 9802, 9803)
DISALLOWED_TAPE_SEEDS = (
    9401, 9402, 9403, 9501, 9502, 9503, 9601, 9602, 9603, 9701, 9702, 9703,
)
BUDGET_LADDER = (256, 1024, 4096)
MATCHUPS = (
    ("1024_vs_256", 1024, 256),
    ("4096_vs_1024", 4096, 1024),
    ("4096_vs_256", 4096, 256),
)
PAIRS_PER_TAPE = 6
TAPE_COUNT = 3
PAIRS_PER_MATCHUP = 18
GAMES_PER_MATCHUP = 36
TRACES_PER_MATCHUP = 36
INVOCATIONS_PER_CONTROL = 9
PAIRS_PER_CONTROL = 54
GAMES_PER_CONTROL = 108
TRACES_PER_CONTROL = 108
TOTAL_INVOCATIONS = 18
TOTAL_PAIRS = 108
TOTAL_GAMES = 216
TOTAL_TRACES = 216
MAX_DEPTH = 12
TT_MEGABYTES = 8
BOOTSTRAP_RESAMPLES = 10_000
CONFIDENCE_LEVEL = 0.95
BOOTSTRAP_SEEDS = {
    "1024_vs_256": 9801101,
    "4096_vs_1024": 9801102,
    "4096_vs_256": 9801103,
}


def _git_sha(root: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def _sha256(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _prep_fingerprint(payload: dict[str, Any]) -> str:
    unsigned = dict(payload)
    unsigned.pop("prep_fingerprint", None)
    return stable_sha256(unsigned)


def _control_rows() -> tuple[tuple[str, Any], ...]:
    return (
        (QUALIFICATION_CONTROL_NAME, build_western_chess_qualification_control()),
        ("standard_shogi", build_standard_shogi_ruleset()),
    )


def _opening_rows(compiled, seed: int) -> dict[str, Any]:
    corpus = generate_arena_openings(compiled, count=PAIRS_PER_TAPE, seed=seed, min_plies=2, max_plies=6)
    return {
        "tape_seed": seed,
        "corpus_id": corpus.corpus_id,
        "opening_count": len(corpus.openings),
        "openings": [
            {
                "index": opening.index,
                "opening_seed": opening.opening_seed,
                "target_plies": opening.target_plies,
                "action_count": len(opening.actions),
                "final_position_key": opening.final_position_key,
            }
            for opening in corpus.openings
        ],
    }


def build_prep(root: Path = ROOT, output: Path = PREP_PATH) -> dict[str, Any]:
    source_sha = _git_sha(root)
    controls = []
    for name, ruleset in _control_rows():
        compiled = compile_ruleset_for_execution(ruleset)
        profile = build_ruleset_profile(compiled, EvaluationConfig())
        checkpoint = LearnableMaterialCheckpoint.from_profile(compiled, profile)
        controls.append({
            "name": name,
            "ruleset_fingerprint": compiled.ruleset_fingerprint,
            "checkpoint_id": checkpoint.checkpoint_id,
            "evaluator_identity": checkpoint.evaluator_version,
            "max_ply": compiled.max_ply,
            "opening_corpora": [_opening_rows(compiled, seed) for seed in TAPE_SEEDS],
        })
    if set(TAPE_SEEDS) & set(DISALLOWED_TAPE_SEEDS):
        raise RuntimeError("R6 tapes overlap a disallowed historical protocol")
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "PREP_FROZEN",
        "experiment": EXPERIMENT,
        "result_schema": RESULT_SCHEMA,
        "source_sandbox_sha": source_sha,
        "protocol_source_sha": source_sha,
        "result_free": True,
        "layer_d_compute_authorized": False,
        "arena_executed": False,
        "boundary": {
            "a_c_prerequisite": "F86N-R1-V4-3",
            "short_circuit": "A/C prerequisite boundary remains zero Layer-D compute",
            "layer_d_compute_invocations": 0,
        },
        "controls": controls,
        "tape_seeds": list(TAPE_SEEDS),
        "disallowed_tape_seeds": list(DISALLOWED_TAPE_SEEDS),
        "budget_ladder": list(BUDGET_LADDER),
        "matchups": [
            {"name": name, "child_nodes_per_move": child, "parent_nodes_per_move": parent,
             "pairs_per_tape": PAIRS_PER_TAPE, "tape_count": TAPE_COUNT,
             "pair_count": PAIRS_PER_MATCHUP, "game_count": GAMES_PER_MATCHUP,
             "trace_count": TRACES_PER_MATCHUP, "bootstrap_seed": BOOTSTRAP_SEEDS[name]}
            for name, child, parent in MATCHUPS
        ],
        "budgets": {
            "invocations_per_control": INVOCATIONS_PER_CONTROL,
            "pairs_per_control": PAIRS_PER_CONTROL,
            "games_per_control": GAMES_PER_CONTROL,
            "traces_per_control": TRACES_PER_CONTROL,
            "total_invocations": TOTAL_INVOCATIONS,
            "total_pairs": TOTAL_PAIRS,
            "total_games": TOTAL_GAMES,
            "total_traces": TOTAL_TRACES,
            "max_depth": MAX_DEPTH,
            "tt_megabytes": TT_MEGABYTES,
            "workers": 1,
        },
        "classification": {
            "precedence": ["DEFER", "DEFER_DEPTH_CENSORED", "DEFER_HORIZON_CENSORED", "DEFER_NONMONOTONE_OR_UNCERTAIN", "STABLE_MONOTONE_POSITIVE"],
            "operational_statuses": ["EXPLICIT_CENSOR", "FALLBACK", "EVIDENCE_INTEGRITY_FAILURE", "OPERATIONALLY_UNRESOLVED"],
            "depth_fraction_threshold": 0.5,
            "horizon_fraction_threshold": 0.5,
            "positive_rule": "each matchup has three tape means > 0.5 and independent 18-pair 95% bootstrap CI lower > 0.5",
            "authority_rule": "both positive controls stable and boundary zero compute => CALIBRATION_READY",
        },
        "bootstrap": {
            "method": "percentile_bootstrap_mean_pair_score",
            "resamples": BOOTSTRAP_RESAMPLES,
            "confidence_level": CONFIDENCE_LEVEL,
            "sample_scope": "the current R6 matchup's 18 pair scores only",
            "historical_pools_enter_bootstrap": False,
        },
        "historical_exclusions": {
            "p0": False, "r2": False, "r3": False, "r5": False,
            "western_r5_old_940x": False, "qualification_pilot_960x": False,
            "stage1_970x": False,
        },
        "production_western_unchanged": True,
        "standard_shogi_positive_semantic_control": True,
        "fixed_sample_authority": True,
        "opening_identity_scope": "all control/tape opening identities prevalidated before first Arena invocation",
    }
    payload["prep_fingerprint"] = _prep_fingerprint(payload)
    output = Path(output)
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    build_prep()
