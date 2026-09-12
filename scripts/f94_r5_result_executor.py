"""Fail-closed executor for the frozen F94-R5-R1 PREP (no CLI execution)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
PREP_PATH = ROOT / "docs/architecture/GENERICCHESS_F94_R5_R1_HORIZON_AWARE_PREP.json"
PREP_SHA256 = "7fe8ba521e437d011253b26a8f91bb2560ff3836db2e5b13a1bc9607719ac585"
RESULT_SCHEMA = "generic-chess-f94-r5-r1-result-v1"

from generic_chess.benchmark.strength_response import StrengthResponsePrep, measure_strength_response
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.openings import generate_arena_openings
from generic_chess.native.compiler import compile_native_semantic_rules
from scripts.f87a_ruleset_qualification import _controls
from scripts.f94_r2_strength_calibration import _ruleset_for
from scripts.f94_r5_horizon_aware_prep import AUTHORITY_PATH, TARGET_NAMES, _candidate


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _prep_object(row: dict[str, Any]) -> StrengthResponsePrep:
    data = dict(row["prep"]); supplied = data.pop("prep_fingerprint")
    prep = StrengthResponsePrep(**{**data, "budget_ladder": tuple(data["budget_ladder"]), "opening_seeds": tuple(data["opening_seeds"]), "tape_seeds": tuple(data["tape_seeds"]), "opening_corpus_ids": tuple(data["opening_corpus_ids"])})
    if prep.prep_fingerprint != supplied:
        raise RuntimeError("nested PREP fingerprint mismatch")
    return prep


def load_frozen_prep(root: Path = ROOT, prep_path: Path = PREP_PATH) -> dict[str, Any]:
    path = Path(prep_path)
    if not path.is_absolute(): path = root / path
    if _sha(path) != PREP_SHA256:
        raise RuntimeError("R5 PREP byte SHA256 mismatch")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "generic-chess-f94-r5-horizon-aware-prep-v2" or payload.get("status") != "PREP_FROZEN" or payload.get("result_free") is not True:
        raise RuntimeError("R5 PREP schema/status is invalid")
    if payload.get("r3_result_used") is not False:
        raise RuntimeError("R5 PREP must not consume R3 observations")
    if payload.get("source_sandbox_sha") != payload.get("protocol_source_sha"):
        raise RuntimeError("R5 PREP source/protocol binding mismatch")
    subprocess.check_call(["git", "cat-file", "-e", f"{payload['protocol_source_sha']}^{{commit}}"], cwd=root)
    authority = root / payload["qualification_authority"]["path"]
    if _sha(authority) != payload["qualification_authority"]["sha256"]:
        raise RuntimeError("R5 qualification authority SHA mismatch")
    controls = {row["name"]: row for row in _controls(root)}
    authority_rows = {row["name"]: row for row in json.loads(authority.read_text())["candidates"]}
    if [row["name"] for row in payload["candidates"]] != list(TARGET_NAMES):
        raise RuntimeError("R5 candidate identities/order mismatch")
    for frozen in payload["candidates"]:
        regenerated = _candidate(controls[frozen["name"]], authority_rows[frozen["name"]])
        if frozen != regenerated:
            raise RuntimeError("R5 frozen candidate/corpus identity mismatch")
        _prep_object(frozen)
    return payload


def run_result(*, root: Path = ROOT, prep_path: Path = PREP_PATH, arena_runner: Callable[..., Any] | None = None, native_compiler: Callable[[Any], Any] = compile_native_semantic_rules) -> dict[str, Any]:
    """Run only after external compute approval; tests inject a fake runner."""
    frozen = load_frozen_prep(root, prep_path)
    controls = {row["name"]: row for row in _controls(root)}
    candidates = []; invocations = pairs = games = traces = strongest_games = 0
    for row in frozen["candidates"]:
        prep = _prep_object(row)
        if row["layer_d_prerequisite"] == "SHORT_CIRCUIT":
            result = measure_strength_response(prep=prep, base_report=SimpleNamespace(layers={"A": row["layer_a_status"], "C": row["layer_c_status"]}))
        else:
            compiled, profile = _ruleset_for(controls[row["name"]]); checkpoint = LearnableMaterialCheckpoint.from_profile(compiled, profile)
            if (compiled.ruleset_fingerprint != row["ruleset_fingerprint"] or checkpoint.checkpoint_id != row["checkpoint_id"] or checkpoint.evaluator_version != row["evaluator_identity"]):
                raise RuntimeError("R5 execution identity mismatch before native compilation")
            corpora = tuple(generate_arena_openings(compiled, count=prep.pair_count, seed=seed, min_plies=2, max_plies=6) for seed in prep.tape_seeds)
            if tuple(c.corpus_id for c in corpora) != prep.opening_corpus_ids: raise RuntimeError("R5 corpus identity mismatch")
            if arena_runner is None: raise RuntimeError("R5 Arena execution requires separately approved runner")
            def tracked_runner(*args, **kwargs):
                nonlocal invocations
                invocations += 1
                return arena_runner(*args, **kwargs)
            result = measure_strength_response(compiled, native_compiler(compiled), checkpoint, checkpoint, prep, opening_corpora=corpora, arena_runner=tracked_runner, capture_search_metrics=True, base_report=SimpleNamespace(layers={"A": "PASS", "C": "PASS"}))
            trace = result.behavior_descriptors["action_trace_contract"]["value"]
            pairs += sum(len(row["pair_scores"]) for row in result.matchups.values())
            games += result.compute_usage["arena_games"]
            traces += len(trace["action_traces"])
            strongest_games += trace["strongest_vs_weakest_pooled_horizon"]["games"]
        candidates.append({"name": row["name"], "prep_fingerprint": prep.prep_fingerprint, "result": result.to_dict()})
    if (invocations, pairs, games, traces, strongest_games) != (18, 108, 216, 216, 72): raise RuntimeError("R5 actual compute counters are incomplete")
    executor_path = Path(__file__).relative_to(root).as_posix()
    return {"schema": RESULT_SCHEMA, "status": "RESULT_COMPLETE", "prep_artifact": Path(prep_path).relative_to(root).as_posix(), "prep_artifact_sha256": PREP_SHA256, "protocol_source_sha": frozen["protocol_source_sha"], "source_sandbox_sha": frozen["source_sandbox_sha"], "result_sandbox_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(), "result_executor_path": executor_path, "result_executor_sha256": _sha(root / executor_path), "derived_compute": {"arena_invocations": invocations, "arena_pairs": pairs, "arena_games": games, "action_traces": traces, "strongest_vs_weakest_games": strongest_games, "boundary_arena_invocations": 0}, "candidates": candidates, "r3_observations_used": False}
