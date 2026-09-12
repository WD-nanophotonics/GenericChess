"""Freeze the independent, result-free F94-R5 P0 pilot protocol.

The pilot is deliberately disjoint from the authoritative R5 opening corpora.
It answers only whether the frozen search/evaluator/environment combination is
worth a later, separately reviewed measurement.  It is never Layer-D
authority and must not be pooled with R2, R3, or the full R5 result.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.openings import generate_arena_openings
from generic_chess.learning.serialization import stable_sha256
from generic_chess.rules.schema import ruleset_from_dict
from scripts.f87a_ruleset_qualification import _controls
from scripts.f94_r2_strength_calibration import (
    BOUNDARY_NAME,
    TARGET_NAMES,
    TT_MEGABYTES,
    _ruleset_for,
)


PREP_PATH = ROOT / "docs/architecture/GENERICCHESS_F94_R5_P0_DISJOINT_PILOT_PREP.json"
SOURCE_PREP_PATH = ROOT / "docs/architecture/GENERICCHESS_F94_R5_R1_HORIZON_AWARE_PREP.json"
EXPERIMENT = "GENERICCHESS-F94-R5-P0-DISJOINT-PILOT"
SCHEMA = "generic-chess-f94-r5-p0-disjoint-pilot-prep-v1"
PILOT_TAPE_SEEDS = (9501, 9502, 9503)
AUTHORITATIVE_TAPE_SEEDS = (9401, 9402, 9403)
STRONGEST_NODES = 4096
WEAKEST_NODES = 256
MAX_DEPTH = 12
PAIR_COUNT = 1
EMPIRICAL_GATE = 0.5


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_sha(root: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def _ruleset_max_ply(control: dict[str, Any]) -> int:
    ruleset = control["builder"]() if "builder" in control else ruleset_from_dict(control["ruleset"])
    return int(ruleset.max_ply)


def _prep_fingerprint(payload: dict[str, Any]) -> str:
    unsigned = dict(payload)
    unsigned.pop("pilot_prep_fingerprint", None)
    return stable_sha256(unsigned)


def _candidate(
    root: Path,
    control: dict[str, Any],
    authority_row: dict[str, Any],
    source_row: dict[str, Any],
    authoritative_opening_seeds: set[int],
) -> dict[str, Any]:
    compiled, profile = _ruleset_for(control)
    checkpoint = LearnableMaterialCheckpoint.from_profile(compiled, profile)
    if compiled.ruleset_fingerprint != source_row["ruleset_fingerprint"]:
        raise RuntimeError(f"{control['name']} ruleset identity changed from frozen R5 PREP")
    if checkpoint.checkpoint_id != source_row["checkpoint_id"]:
        raise RuntimeError(f"{control['name']} checkpoint identity changed from frozen R5 PREP")
    if checkpoint.evaluator_version != source_row["evaluator_identity"]:
        raise RuntimeError(f"{control['name']} evaluator identity changed from frozen R5 PREP")
    source_prep = source_row["prep"]
    frozen_ids = {row["corpus_id"] for row in source_row["opening_corpora"]}
    pilot_corpora = tuple(
        generate_arena_openings(compiled, count=PAIR_COUNT, seed=seed, min_plies=2, max_plies=6)
        for seed in PILOT_TAPE_SEEDS
    )
    if any(corpus.corpus_id in frozen_ids for corpus in pilot_corpora):
        raise RuntimeError(f"{control['name']} pilot corpus overlaps authoritative R5 corpus")
    selected = []
    for seed, corpus in zip(PILOT_TAPE_SEEDS, pilot_corpora):
        opening = corpus.openings[0]
        if opening.opening_seed in authoritative_opening_seeds:
            raise RuntimeError(f"{control['name']} pilot opening overlaps authoritative R5 opening")
        selected.append({
            "tape_seed": seed,
            "corpus_id": corpus.corpus_id,
            "opening_count": len(corpus.openings),
            "selected_opening_index": opening.index,
            "selected_opening_seed": opening.opening_seed,
            "selected_target_plies": opening.target_plies,
            "selected_action_count": len(opening.actions),
            "selected_final_position_key": opening.final_position_key,
        })
    ready = authority_row["layer_a_status"] == "PASS" and authority_row["layer_c_status"] == "PASS"
    prep = {
        "schema": SCHEMA,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "candidate_fingerprint": checkpoint.checkpoint_id,
        "evaluator_identity": checkpoint.evaluator_version,
        "budget_ladder": [WEAKEST_NODES, STRONGEST_NODES],
        "strongest_nodes_per_move": STRONGEST_NODES,
        "weakest_nodes_per_move": WEAKEST_NODES,
        "max_depth": MAX_DEPTH,
        "max_ply": _ruleset_max_ply(control),
        "pair_count": PAIR_COUNT,
        "tape_seeds": list(PILOT_TAPE_SEEDS),
        "opening_corpus_ids": [row["corpus_id"] for row in selected],
        "child_ceiling_gate_fraction": EMPIRICAL_GATE,
        "horizon_hit_gate_fraction": EMPIRICAL_GATE,
        "workers": 1,
        "tt_megabytes": TT_MEGABYTES,
        "classification_rule": (
            "pilot-only direction: all three pair scores > 0.5 is POSITIVE_DIRECTION, "
            "all three < 0.5 is NEGATIVE_DIRECTION, otherwise MIXED_OR_UNCERTAIN; "
            "child-only depth-ceiling and strongest-vs-weakest max-ply fractions "
            "must each remain below 0.5; isolated hits are descriptors"
        ),
        "result_authority": "OBSERVED_NOT_POOLABLE",
    }
    prep["prep_fingerprint"] = stable_sha256(prep)
    return {
        "name": control["name"],
        "class": source_row["class"],
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "checkpoint_id": checkpoint.checkpoint_id,
        "evaluator_identity": checkpoint.evaluator_version,
        "layer_a_status": authority_row["layer_a_status"],
        "layer_c_status": authority_row["layer_c_status"],
        "layer_d_prerequisite": "READY" if ready else "SHORT_CIRCUIT",
        "source_r5_prep_fingerprint": source_prep["prep_fingerprint"],
        "prep": prep,
        "opening_corpora": selected,
    }


def build_prep(root: Path = ROOT, output: Path = PREP_PATH) -> dict[str, Any]:
    source = json.loads(SOURCE_PREP_PATH.read_text(encoding="utf-8"))
    if source.get("status") != "PREP_FROZEN" or source.get("result_free") is not True:
        raise RuntimeError("frozen R5 source PREP is not result-free")
    if tuple(source["budgets"]["tape_seeds"]) != AUTHORITATIVE_TAPE_SEEDS:
        raise RuntimeError("authoritative R5 tape identity changed")
    if set(PILOT_TAPE_SEEDS) & set(AUTHORITATIVE_TAPE_SEEDS):
        raise RuntimeError("pilot tape seeds must be disjoint from authoritative R5 seeds")
    authority_payload = json.loads(
        (root / source["qualification_authority"]["path"]).read_text(encoding="utf-8")
    )
    controls = {row["name"]: row for row in _controls(root)}
    source_rows = {row["name"]: row for row in source["candidates"]}
    authority_rows = {row["name"]: row for row in authority_payload["candidates"]}
    authoritative_opening_seeds = {
        seed
        for row in source["candidates"]
        for corpus in row["opening_corpora"]
        for seed in corpus["opening_seeds"]
    }
    candidates = [
        _candidate(root, controls[name], authority_rows[name], source_rows[name], authoritative_opening_seeds)
        for name in TARGET_NAMES
    ]
    payload = {
        "schema": SCHEMA,
        "status": "PILOT_PREP_FROZEN",
        "experiment": EXPERIMENT,
        "source_sandbox_sha": _git_sha(root),
        "protocol_source_sha": _git_sha(root),
        "source_r5_prep_artifact": SOURCE_PREP_PATH.relative_to(root).as_posix(),
        "source_r5_prep_artifact_sha256": _sha256(SOURCE_PREP_PATH),
        "qualification_authority": source["qualification_authority"],
        "result_free": True,
        "non_poolable_with_r2_r3_r5": True,
        "pilot_tape_seeds": list(PILOT_TAPE_SEEDS),
        "authoritative_r5_tape_seeds": list(AUTHORITATIVE_TAPE_SEEDS),
        "budgets": {
            "strongest_nodes_per_move": STRONGEST_NODES,
            "weakest_nodes_per_move": WEAKEST_NODES,
            "max_depth": MAX_DEPTH,
            "tt_megabytes": TT_MEGABYTES,
            "pair_count_per_tape": PAIR_COUNT,
            "tape_count_per_candidate": len(PILOT_TAPE_SEEDS),
            "ready_candidate_count": 2,
            "boundary_candidate_count": 1,
            "arena_invocations": 6,
            "arena_pairs": 6,
            "arena_games": 12,
            "action_traces": 12,
            "workers": 1,
        },
        "direction_rule": {
            "positive": "all three pilot tape pair scores > 0.5",
            "negative": "all three pilot tape pair scores < 0.5",
            "mixed_or_uncertain": "any tie or inconsistent tape signs",
            "depth_censor": "strongest-vs-weakest child completed-depth hit fraction >= 0.5",
            "horizon_censor": "strongest-vs-weakest max-ply hit fraction >= 0.5",
            "isolated_hits": "descriptor only; do not invalidate the pilot",
            "authority": "OBSERVED_NOT_POOLABLE; no Layer-D PASS",
        },
        "action_trace_contract": {
            "schema": "generic-chess-strength-response-action-trace-v1",
            "required_for_all_games": True,
            "fields": [
                "tape_id", "opening_corpus_id", "matchup", "game_index", "pair_index",
                "child_owner", "budget_roles", "termination_status", "max_ply", "max_ply_hit",
                "actual_plies", "opening_position_key", "final_position_key", "actions",
                "action_trace_sha256",
            ],
            "semantics": "pilot telemetry only; never pooled with authoritative R5 evidence",
        },
        "candidates": candidates,
        "boundary_control": {
            "name": BOUNDARY_NAME,
            "layer_a_status": "PASS",
            "layer_c_status": "DEFER",
            "prerequisite": "PREREQUISITE_A_C_NOT_PASS",
            "arena_invocations": 0,
            "native_compile": 0,
            "compute": 0,
        },
    }
    payload["pilot_prep_fingerprint"] = _prep_fingerprint(payload)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    build_prep()
