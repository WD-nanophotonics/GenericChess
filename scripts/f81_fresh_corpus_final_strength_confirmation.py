"""F81 fresh-corpus final strength confirmation harness."""

from __future__ import annotations

from dataclasses import asdict, replace
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.learning import arena as arena_module  # noqa: E402
from generic_chess.learning.arena import ArenaConfig, ArenaExecutionCaps, run_arena_game_resumable  # noqa: E402
from generic_chess.learning.openings import ArenaOpeningCorpus, generate_arena_openings  # noqa: E402
from generic_chess.learning.statistics import bootstrap_pair_mean_ci  # noqa: E402
from generic_chess.native import native_available  # noqa: E402
from scripts import f59_action_spectrum_diagnosis as f59  # noqa: E402
from scripts import f61_r2_fresh_strength as f61r2  # noqa: E402
from scripts import f77_trusted_pointwise_q_arena2_triage as f77  # noqa: E402
from scripts import f79_parent_anchored_full_residual_arena4 as f79  # noqa: E402


WORK_ORDER = "GENERICCHESS-F81-FRESH-CORPUS-FINAL-STRENGTH-CONFIRMATION"
BASELINE_SHA = "2513742e72258e9b6a20c5760c9f467de2b05891"
PARENT_SHA = f79.PARENT_SHA
CHILD_SHA = f79.CHILD_SHA
CANDIDATE_MODEL_SHA = "b4372d087d0e7760857efefd69413c97c8cf10b5b188dd704f5d1e308a4d32b6"
F80_EVIDENCE = ROOT / "artifacts" / "f80_parent_anchored_full_residual" / "arena8_strength_evidence.json"
F80_EVIDENCE_SHA = "438ddec64d1225488900f3a823fa0fd8a52a9dd60942b39d1f9f32dcb3b0ead0"
F80_REPORT = ROOT / "docs" / "architecture" / "GENERICCHESS_F80_R1_EXTENDED_PLY_FROZEN_ARENA8.md"
F80_REPORT_SHA = "e992fb9f7804d48878b3eb71a309d95f3979f8b55a775ecded9e6bff6ffcfd4b"
F79_EVIDENCE = ROOT / "artifacts" / "f79_parent_anchored_full_residual" / "arena4_strength_evidence.json"
F79_EVIDENCE_SHA = "888864459718cbc1d81cd0e4d1f9e3cae5e1eb116b9c3d05ca2f559e35fb9477"
F62_OUT = ROOT / ".generic_chess_flow" / "f62-learned-champion-repeatability"
F75_OPENINGS = ROOT / "artifacts" / "f75_parent_retained_arena" / "openings.json"
F77_OPENINGS = ROOT / "artifacts" / "f77_trusted_pointwise_q_arena" / "openings.json"
F78_OPENINGS = f79.F78_OPENINGS
LABEL = f79.LABEL
OPENING_SEED = 810501
OPENING_COUNT = 8
PAIRS = 8
NODES = 512
MAX_DEPTH = 12
TT_MEGABYTES = 8
CORPUS_PATH = ROOT / "artifacts" / "f81_final_confirmation" / "openings.json"
OUT = ROOT / ".generic_chess_flow" / "f81-fresh-corpus-final-strength-confirmation"
PROGRESS = OUT / "progress"
RESULT_PATH = OUT / "f81_results.json"


def _atomic_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _final_position_keys(path: Path) -> set[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {opening["final_position_key"] for opening in payload["corpus"]["openings"]}


def _f62_keys() -> set[str]:
    return {
        json.loads((F62_OUT / "progress" / "spectrum" / f"root-{index:03d}.json").read_text(encoding="utf-8"))["identity"]["record"]["position_key"]
        for index in range(96)
    }


def _load_or_make_corpus(compiled):
    if CORPUS_PATH.is_file():
        payload = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
        corpus = ArenaOpeningCorpus.from_dict(payload["corpus"])
        corpus.validate(compiled)
        if payload.get("corpus_id") != corpus.corpus_id or payload.get("seed") != OPENING_SEED:
            raise RuntimeError("F81 final corpus identity mismatch")
        if len(corpus.openings) != OPENING_COUNT:
            raise RuntimeError("F81 final corpus count mismatch")
        return corpus, payload
    corpus = generate_arena_openings(compiled, count=OPENING_COUNT, seed=OPENING_SEED, min_plies=2, max_plies=6)
    corpus.validate(compiled)
    keys = [opening.final_position_key for opening in corpus.openings]
    prior = {
        "f62": _f62_keys(),
        "f75": _final_position_keys(F75_OPENINGS),
        "f77": _final_position_keys(F77_OPENINGS),
        "f78": _final_position_keys(F78_OPENINGS),
    }
    overlaps = {name: sorted(set(keys) & values) for name, values in prior.items()}
    if len(set(keys)) != OPENING_COUNT:
        raise RuntimeError("F81 final corpus final-position identities are not unique")
    if any(overlaps.values()):
        raise RuntimeError(f"FINAL_CORPUS_OVERLAP: {overlaps}")
    payload = {
        "schema": "generic-chess-f81-final-confirmation-opening-corpus-v1",
        "corpus": corpus.to_dict(), "corpus_id": corpus.corpus_id,
        "seed": OPENING_SEED, "opening_count": OPENING_COUNT,
        "f62_overlap_count": len(overlaps["f62"]), "f75_overlap_count": len(overlaps["f75"]),
        "f77_overlap_count": len(overlaps["f77"]), "f78_overlap_count": len(overlaps["f78"]),
        "unique_final_position_count": len(set(keys)),
    }
    _atomic_json(CORPUS_PATH, payload)
    return corpus, payload


def _load_candidate(compiled):
    descriptor = json.loads((ROOT / "artifacts" / "f78_parent_anchored_full_residual" / "candidate.json").read_text(encoding="utf-8"))
    if descriptor["child_checkpoint_id"] != CHILD_SHA or descriptor["candidate_model_sha256"] != CANDIDATE_MODEL_SHA:
        raise RuntimeError("F81 candidate descriptor identity mismatch")
    gen1, candidate, _descriptor = f79._load_frozen_candidate(compiled)
    if gen1.checkpoint_id != PARENT_SHA or candidate.checkpoint_id != CHILD_SHA:
        raise RuntimeError("F81 candidate checkpoint round-trip identity mismatch")
    return gen1, candidate, descriptor


def _validate_prior_evidence() -> dict:
    if hashlib.sha256(F80_EVIDENCE.read_bytes()).hexdigest() != F80_EVIDENCE_SHA:
        raise RuntimeError("F81 F80 evidence content SHA mismatch")
    if hashlib.sha256(F80_REPORT.read_bytes()).hexdigest() != F80_REPORT_SHA:
        raise RuntimeError("F81 F80 report content SHA mismatch")
    if hashlib.sha256(F79_EVIDENCE.read_bytes()).hexdigest() != F79_EVIDENCE_SHA:
        raise RuntimeError("F81 F79 evidence content SHA mismatch")
    f80 = json.loads(F80_EVIDENCE.read_text(encoding="utf-8"))
    f79 = json.loads(F79_EVIDENCE.read_text(encoding="utf-8"))
    expected_f80 = {
        "schema": "generic-chess-f80-arena8-strength-evidence-v2",
        "work_order_baseline_sha": "f4fc8411079e25fe1cfeab1c9be79535881e4274",
        "execution_harness_checkpoint": "0fd011f9f34799fc087209a73538aacb61019e7b",
        "result_report_checkpoint": "fe1f395224df199fd0244dcf2da297032953c1c7",
        "source_checkpoint": "fe1f395224df199fd0244dcf2da297032953c1c7",
        "source_report_path": "docs/architecture/GENERICCHESS_F80_R1_EXTENDED_PLY_FROZEN_ARENA8.md",
        "source_report_sha256": F80_REPORT_SHA,
        "f79_evidence_path": "artifacts/f79_parent_anchored_full_residual/arena4_strength_evidence.json",
        "f79_evidence_sha256": F79_EVIDENCE_SHA,
    }
    for key, expected in expected_f80.items():
        if f80.get(key) != expected:
            raise RuntimeError(f"F81 F80 provenance mismatch for {key}")
    if f79.get("classification") != "PARENT_ANCHORED_FULL_RESIDUAL_ARENA4_SURVIVES":
        raise RuntimeError("F81 prior Arena4 classification is not SURVIVES")
    return {"f80": {"path": str(F80_EVIDENCE.relative_to(ROOT)), "content_sha256": F80_EVIDENCE_SHA}, "f79": {"path": str(F79_EVIDENCE.relative_to(ROOT)), "content_sha256": F79_EVIDENCE_SHA}, "f80_report": {"path": str(F80_REPORT.relative_to(ROOT)), "content_sha256": F80_REPORT_SHA}}


def _config_and_caps():
    config = ArenaConfig(
        pairs=PAIRS, nodes_per_move=NODES, parent_nodes_per_move=NODES,
        child_nodes_per_move=NODES, max_depth=MAX_DEPTH, tt_megabytes=TT_MEGABYTES,
        opening_seed=OPENING_SEED, opening_count=OPENING_COUNT,
        min_plies=2, max_plies=6, workers=4,
    )
    caps = ArenaExecutionCaps(
        per_game_wall_seconds=3600, per_game_nodes=262144,
        per_game_plies=512, max_stage_games=16, max_concurrent_games=4,
        stage_wall_seconds=3600,
    )
    return config, caps


def _validate_checkpointed_games(compiled, openings, config, caps):
    manifest_path = PROGRESS / "manifest.json"
    failures = []
    if not manifest_path.is_file():
        return {"game_files": 0, "search_rows": 0, "all_root_window_pruning_true": False, "missing_root_window_pruning_rows": 0, "max_nodes": 0, "contract_failures": ["progress manifest missing"]}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    identity = manifest["identity"]
    identity_sha = manifest["identity_sha256"]
    opening_rows = openings.to_dict()["openings"]
    valid_games = 0
    rows = []
    for path in sorted(PROGRESS.glob("game-*.json")):
        match = re.fullmatch(r"game-(\d{6})-owner-([01])\.json", path.name)
        if match is None:
            failures.append(f"invalid progress filename: {path.name}")
            continue
        pair_index, owner = int(match.group(1)), int(match.group(2))
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            expected = arena_module._game_progress_identity_for(identity, config, caps, opening_rows[pair_index], pair_index, owner, capture_search_metrics=True)
            game = arena_module._validate_game_progress(compiled, openings.openings[pair_index], payload, expected_identity=expected, identity_sha256=identity_sha, config=config, capture_search_metrics=True, pair_index=pair_index, child_owner=owner)
            rows.extend(game.search_metrics)
            valid_games += 1
        except Exception as exc:
            failures.append(f"checkpoint validation failed for {path.name}: {exc}")
    return {"game_files": valid_games, "search_rows": len(rows), "all_root_window_pruning_true": bool(rows) and all(row.get("root_window_pruning") is True for row in rows), "missing_root_window_pruning_rows": sum("root_window_pruning" not in row for row in rows), "max_nodes": max((int(row.get("nodes", 0)) for row in rows), default=0), "contract_failures": failures}


def _run_stage(compiled, native, gen1, candidate, openings):
    config, caps = _config_and_caps()
    first = run_arena_game_resumable(compiled, native, gen1, candidate, config, progress_dir=PROGRESS, openings=openings, capture_search_metrics=True, caps=caps, stage_id="f81-final-confirmation")
    checkpoint_validation = _validate_checkpointed_games(compiled, openings, config, caps)
    failures = list(checkpoint_validation["contract_failures"])
    summary = f77._summary_payload(first.summary)
    telemetry = f77._telemetry(first.summary) if first.summary is not None else {}
    replay_validation = None
    if first.status == "COMPLETE":
        replay = run_arena_game_resumable(compiled, native, gen1, candidate, config, progress_dir=PROGRESS, openings=openings, capture_search_metrics=True, caps=caps, stage_id="f81-final-confirmation")
        replay_summary = f77._summary_payload(replay.summary)
        replay_validation = {"status": replay.status, "completed_games": replay.completed_games, "completed_pairs": replay.completed_pairs, "summary_equal": summary == replay_summary}
        if replay.status != first.status or replay.completed_games != first.completed_games or replay.completed_pairs != first.completed_pairs or summary != replay_summary:
            failures.append("complete-stage replay status/count/summary differs")
        if first.effective_game_lanes != 4:
            failures.append("effective game lanes did not equal four")
        if telemetry and not telemetry.get("all_root_window_pruning_true", False):
            failures.append("root pruning telemetry was not true for every search")
        if telemetry.get("missing_root_window_pruning_rows", 0):
            failures.append("root pruning telemetry field was missing")
    return {"config": {"pairs": PAIRS, "total_games": 16, "source_opening_indices": list(range(OPENING_COUNT)), "nodes_per_move": NODES, "parent_nodes_per_move": NODES, "child_nodes_per_move": NODES, "max_depth": MAX_DEPTH, "tt_megabytes": TT_MEGABYTES, "workers": 4, "root_window_pruning": True, "execution_caps": asdict(caps)}, "run": {"status": first.status, "completed_games": first.completed_games, "completed_pairs": first.completed_pairs, "total_games": first.total_games, "reason": first.reason, "effective_game_lanes": first.effective_game_lanes}, "summary": summary, "telemetry": telemetry, "checkpoint_validation": checkpoint_validation, "replay_validation": replay_validation, "contract_failures": failures}


def run() -> dict:
    if not native_available():
        raise RuntimeError("F81 requires the native extension")
    compiled, native, _profile = f59._ruleset(LABEL)
    prior_evidence = _validate_prior_evidence()
    corpus, corpus_payload = _load_or_make_corpus(compiled)
    gen1, candidate, descriptor = _load_candidate(compiled)
    final_stage = _run_stage(compiled, native, gen1, candidate, corpus)
    failures = list(final_stage["contract_failures"])
    summary = final_stage["summary"]
    aggregate = None
    if summary is not None:
        scores = list(summary["pair_scores"])
        low, high = bootstrap_pair_mean_ci(scores)
        aggregate = {"pair_count": len(scores), "pair_scores": scores, "mean_pair_score": sum(scores) / len(scores), "child_better_pairs": summary["child_better_pairs"], "tied_pairs": summary["tied_pairs"], "child_worse_pairs": summary["child_worse_pairs"], "bootstrap_low": low, "bootstrap_high": high, "game_wins": summary["game_wins"], "game_draws": summary["game_draws"], "game_losses": summary["game_losses"], "completed_games": final_stage["run"]["completed_games"], "completed_pairs": final_stage["run"]["completed_pairs"]}
    if failures:
        classification = "HARNESS_MISMATCH"
    elif final_stage["run"]["status"] != "COMPLETE":
        classification = "PARENT_ANCHORED_FULL_RESIDUAL_FINAL_CONFIRMATION_UNRESOLVED"
    elif aggregate["mean_pair_score"] > 0.5 and aggregate["child_better_pairs"] > aggregate["child_worse_pairs"]:
        classification = "PARENT_ANCHORED_FULL_RESIDUAL_FINAL_CONFIRMED"
    else:
        classification = "PARENT_ANCHORED_FULL_RESIDUAL_FINAL_CONFIRMATION_REJECTED"
    result = {"schema": "generic-chess-f81-fresh-corpus-final-strength-confirmation-v1", "work_order": WORK_ORDER, "baseline_sha": BASELINE_SHA, "classification": classification, "parent_checkpoint_id": gen1.checkpoint_id, "child_checkpoint_id": candidate.checkpoint_id, "candidate_model_sha256": descriptor["candidate_model_sha256"], "opening_corpus": corpus_payload, "prior_evidence": prior_evidence, "final_stage": final_stage, "aggregate_fresh_arena8": aggregate, "contract_failures": failures, "champion_before": PARENT_SHA, "champion_after": CHILD_SHA if classification == "PARENT_ANCHORED_FULL_RESIDUAL_FINAL_CONFIRMED" else PARENT_SHA, "code_provenance": {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in ("scripts/f81_fresh_corpus_final_strength_confirmation.py", "generic_chess/learning/arena.py", "generic_chess/learning/openings.py", "generic_chess/native/semantic_engine.py")}}
    _atomic_json(RESULT_PATH, result)
    return result


def main() -> None:
    result = run()
    aggregate = result["aggregate_fresh_arena8"] or {}
    print(json.dumps({"classification": result["classification"], "parent_checkpoint_id": result["parent_checkpoint_id"], "child_checkpoint_id": result["child_checkpoint_id"], "fresh_pair_scores": aggregate.get("pair_scores"), "fresh_mean_pair_score": aggregate.get("mean_pair_score"), "better": aggregate.get("child_better_pairs"), "tied": aggregate.get("tied_pairs"), "worse": aggregate.get("child_worse_pairs"), "game_wins": aggregate.get("game_wins"), "game_draws": aggregate.get("game_draws"), "game_losses": aggregate.get("game_losses"), "contract_failures": result["contract_failures"]}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
