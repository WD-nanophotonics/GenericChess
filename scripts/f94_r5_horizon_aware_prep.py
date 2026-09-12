"""Freeze the result-free F94-R5 horizon-aware Layer-D protocol.

This generator intentionally has no RESULT entry point and never imports or
interprets R3 observations.  Its only output is the next immutable PREP.
"""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.benchmark.strength_response import (
    ACTION_TRACE_SCHEMA,
    DEFAULT_BUDGETS,
    HORIZON_AWARE_PREP_SCHEMA,
    prepare_strength_response,
)
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.openings import generate_arena_openings
from generic_chess.rules.schema import ruleset_from_dict
from scripts.f87a_ruleset_qualification import _controls
from scripts.f94_r2_strength_calibration import (
    BOUNDARY_NAME,
    PAIR_COUNT,
    TARGET_NAMES,
    TAPE_SEEDS,
    TT_MEGABYTES,
    _ruleset_for,
)


PREP_PATH = ROOT / "docs/architecture/GENERICCHESS_F94_R5_R1_HORIZON_AWARE_PREP.json"
AUTHORITY_PATH = ROOT / "docs/architecture/GENERICCHESS_F94_R2_STRENGTH_RESPONSE_PREP.json"
EXPERIMENT = "GENERICCHESS-F94-R5-R1-HORIZON-AWARE-STRENGTH-PREP"
MAX_DEPTH = 12
EMPIRICAL_GATE = 0.5


def _git_sha(root: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()


def _ruleset_max_ply(control: dict[str, Any]) -> int:
    ruleset = control["builder"]() if "builder" in control else ruleset_from_dict(control["ruleset"])
    return int(ruleset.max_ply)


def _candidate(control: dict[str, Any], authority: dict[str, Any]) -> dict[str, Any]:
    compiled, profile = _ruleset_for(control)
    checkpoint = LearnableMaterialCheckpoint.from_profile(compiled, profile)
    corpora = tuple(
        generate_arena_openings(compiled, count=PAIR_COUNT, seed=seed, min_plies=2, max_plies=6)
        for seed in TAPE_SEEDS
    )
    prep = prepare_strength_response(
        compiled,
        evaluator_identity=checkpoint.evaluator_version,
        candidate_fingerprint=checkpoint.checkpoint_id,
        opening_corpora=corpora,
        budget_ladder=DEFAULT_BUDGETS,
        max_depth=MAX_DEPTH,
        max_ply=_ruleset_max_ply(control),
        pair_count=PAIR_COUNT,
        tape_seeds=TAPE_SEEDS,
        tt_megabytes=TT_MEGABYTES,
        schema=HORIZON_AWARE_PREP_SCHEMA,
        child_ceiling_gate_fraction=EMPIRICAL_GATE,
        horizon_hit_gate_fraction=EMPIRICAL_GATE,
    )
    return {
        "name": control["name"],
        "class": control["class"],
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "checkpoint_id": checkpoint.checkpoint_id,
        "evaluator_identity": checkpoint.evaluator_version,
        "layer_a_status": authority["layer_a_status"],
        "layer_c_status": authority["layer_c_status"],
        "layer_d_prerequisite": (
            "READY" if authority["layer_a_status"] == "PASS" and authority["layer_c_status"] == "PASS"
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
    authority_path = root / AUTHORITY_PATH.relative_to(ROOT)
    authority_payload = json.loads(authority_path.read_text(encoding="utf-8"))
    authority_rows = {row["name"]: row for row in authority_payload["candidates"]}
    payload = {
        "schema": "generic-chess-f94-r5-horizon-aware-prep-v2",
        "status": "PREP_FROZEN",
        "experiment": EXPERIMENT,
        "source_sandbox_sha": _git_sha(root),
        "protocol_source_sha": _git_sha(root),
        "qualification_authority": {
            "path": AUTHORITY_PATH.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(authority_path.read_bytes()).hexdigest(),
        },
        "result_free": True,
        "r3_result_used": False,
        "budgets": {
            "nodes_per_move": list(DEFAULT_BUDGETS),
            "max_depth": MAX_DEPTH,
            "tt_megabytes": TT_MEGABYTES,
            "pair_count_per_tape": PAIR_COUNT,
            "tape_seeds": list(TAPE_SEEDS),
            "arena_runs": len(TAPE_SEEDS) * 3,
        },
        "gates": {
            "child_only_ceiling_fraction": {
                "threshold": EMPIRICAL_GATE,
                "provenance": "GENERICCHESS_SPECIFIC_EMPIRICAL_GATE",
            },
            "strongest_vs_weakest_horizon_fraction": {
                "threshold": EMPIRICAL_GATE,
                "provenance": "GENERICCHESS_SPECIFIC_EMPIRICAL_GATE",
            },
        },
        "action_trace_contract": {
            "schema": ACTION_TRACE_SCHEMA,
            "required_for_all_games": True,
            "fields": [
                "tape_id", "opening_corpus_id", "matchup", "game_index",
                "pair_index", "child_owner", "budget_roles", "termination_status",
                "max_ply", "max_ply_hit", "actual_plies", "opening_position_key",
                "final_position_key", "actions", "action_trace_sha256",
            ],
            "semantics": "observational telemetry only; it does not alter search, TT, evaluator, or termination",
        },
        "candidates": [_candidate(controls[name], authority_rows[name]) for name in TARGET_NAMES],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    build_prep()
