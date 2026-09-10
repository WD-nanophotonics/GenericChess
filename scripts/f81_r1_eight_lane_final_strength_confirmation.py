"""F81-R1 eight-lane fresh-corpus final strength confirmation harness."""

from __future__ import annotations

from dataclasses import asdict
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
from generic_chess.learning.openings import ArenaOpeningCorpus  # noqa: E402
from generic_chess.learning.statistics import bootstrap_pair_mean_ci  # noqa: E402
from generic_chess.native import native_available  # noqa: E402
from scripts import f59_action_spectrum_diagnosis as f59  # noqa: E402
from scripts import f77_trusted_pointwise_q_arena2_triage as f77  # noqa: E402
from scripts import f81_fresh_corpus_final_strength_confirmation as f81  # noqa: E402


WORK_ORDER = "GENERICCHESS-F81-R1-EIGHT-LANE-FRESH-CORPUS-FINAL-CONFIRMATION"
BASELINE_SHA = "ef9a165ddebc8206e61327c196dc0baec2b9bd75"
PARENT_SHA = f81.PARENT_SHA
CHILD_SHA = f81.CHILD_SHA
CANDIDATE_MODEL_SHA = f81.CANDIDATE_MODEL_SHA
CORPUS_PATH = ROOT / "artifacts" / "f81_final_confirmation" / "openings.json"
CORPUS_ID = "67b9dafc51a618645c3328228c30a8744cc8f988395a7d54d382b65276dc935c"
OUT = ROOT / ".generic_chess_flow" / "f81-r1-eight-lane-final-confirmation"
PROGRESS = OUT / "progress"
RESULT_PATH = OUT / "f81_r1_results.json"
ARTIFACT_PATH = ROOT / "artifacts" / "f81_final_confirmation" / "final_strength_evidence.json"
LABEL = f81.LABEL


def _atomic_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _load_frozen_corpus(compiled):
    payload = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    corpus = ArenaOpeningCorpus.from_dict(payload["corpus"])
    corpus.validate(compiled)
    if payload.get("corpus_id") != CORPUS_ID or corpus.corpus_id != CORPUS_ID:
        raise RuntimeError("F81-R1 frozen corpus identity mismatch")
    if payload.get("seed") != 810501 or payload.get("opening_count") != 8 or len(corpus.openings) != 8:
        raise RuntimeError("F81-R1 frozen corpus shape mismatch")
    if payload.get("unique_final_position_count") != 8:
        raise RuntimeError("F81-R1 frozen corpus is not unique")
    if any(payload.get(key) != 0 for key in ("f62_overlap_count", "f75_overlap_count", "f77_overlap_count", "f78_overlap_count")):
        raise RuntimeError("F81-R1 frozen corpus overlap is nonzero")
    return corpus, payload


def _config_and_caps():
    config = ArenaConfig(
        pairs=8,
        nodes_per_move=512,
        parent_nodes_per_move=512,
        child_nodes_per_move=512,
        max_depth=12,
        tt_megabytes=8,
        opening_seed=810501,
        opening_count=8,
        min_plies=2,
        max_plies=6,
        workers=8,
    )
    caps = ArenaExecutionCaps(
        per_game_wall_seconds=3600,
        per_game_nodes=262144,
        per_game_plies=512,
        max_stage_games=16,
        max_concurrent_games=8,
        stage_wall_seconds=3600,
    )
    return config, caps


def _validate_checkpointed_games(compiled, openings, config, caps):
    manifest_path = PROGRESS / "manifest.json"
    failures = []
    if not manifest_path.is_file():
        return {"game_files": 0, "search_rows": 0, "all_root_window_pruning_true": False, "missing_root_window_pruning_rows": 0, "max_nodes": 0, "contract_failures": ["progress manifest missing"]}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
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
            expected = arena_module._game_progress_identity_for(manifest["identity"], config, caps, opening_rows[pair_index], pair_index, owner, capture_search_metrics=True)
            game = arena_module._validate_game_progress(compiled, openings.openings[pair_index], payload, expected_identity=expected, identity_sha256=manifest["identity_sha256"], config=config, capture_search_metrics=True, pair_index=pair_index, child_owner=owner)
            rows.extend(game.search_metrics)
            valid_games += 1
        except Exception as exc:
            failures.append(f"checkpoint validation failed for {path.name}: {exc}")
    return {"game_files": valid_games, "search_rows": len(rows), "all_root_window_pruning_true": bool(rows) and all(row.get("root_window_pruning") is True for row in rows), "missing_root_window_pruning_rows": sum("root_window_pruning" not in row for row in rows), "max_nodes": max((int(row.get("nodes", 0)) for row in rows), default=0), "contract_failures": failures}


def _run_stage(compiled, native, gen1, candidate, openings):
    config, caps = _config_and_caps()
    if (os.cpu_count() or 1) < 8:
        raise RuntimeError("F81-R1 compute blocker: os.cpu_count() < 8")
    if caps.game_lanes(config.pairs, config.workers) != 8:
        raise RuntimeError("F81-R1 compute blocker: effective game lanes are not eight")
    first = run_arena_game_resumable(compiled, native, gen1, candidate, config, progress_dir=PROGRESS, openings=openings, capture_search_metrics=True, caps=caps, stage_id="f81-r1-eight-lane-final-confirmation")
    checkpoint_validation = _validate_checkpointed_games(compiled, openings, config, caps)
    failures = list(checkpoint_validation["contract_failures"])
    summary = f77._summary_payload(first.summary)
    telemetry = f77._telemetry(first.summary) if first.summary is not None else {}
    replay_validation = None
    if first.status == "COMPLETE":
        replay = run_arena_game_resumable(compiled, native, gen1, candidate, config, progress_dir=PROGRESS, openings=openings, capture_search_metrics=True, caps=caps, stage_id="f81-r1-eight-lane-final-confirmation")
        replay_summary = f77._summary_payload(replay.summary)
        replay_validation = {"status": replay.status, "completed_games": replay.completed_games, "completed_pairs": replay.completed_pairs, "summary_equal": summary == replay_summary}
        if replay.status != first.status or replay.completed_games != first.completed_games or replay.completed_pairs != first.completed_pairs or summary != replay_summary:
            failures.append("complete-stage replay status/count/summary differs")
        if first.effective_game_lanes != 8:
            failures.append("effective game lanes did not equal eight")
        if telemetry and not telemetry.get("all_root_window_pruning_true", False):
            failures.append("root pruning telemetry was not true for every search")
        if telemetry.get("missing_root_window_pruning_rows", 0):
            failures.append("root pruning telemetry field was missing")
    return {"config": {"pairs": 8, "total_games": 16, "nodes_per_move": 512, "parent_nodes_per_move": 512, "child_nodes_per_move": 512, "max_depth": 12, "tt_megabytes": 8, "workers": 8, "root_window_pruning": True, "execution_caps": asdict(caps)}, "run": {"status": first.status, "completed_games": first.completed_games, "completed_pairs": first.completed_pairs, "total_games": first.total_games, "reason": first.reason, "effective_game_lanes": first.effective_game_lanes}, "summary": summary, "telemetry": telemetry, "checkpoint_validation": checkpoint_validation, "replay_validation": replay_validation, "contract_failures": failures}


def run() -> dict:
    if not native_available():
        raise RuntimeError("F81-R1 requires the native extension")
    if OUT.exists() and any(OUT.iterdir()):
        raise RuntimeError("F81-R1 runtime namespace is not fresh")
    compiled, native, _profile = f59._ruleset(LABEL)
    prior_evidence = f81._validate_prior_evidence()
    corpus, corpus_payload = _load_frozen_corpus(compiled)
    gen1, candidate, descriptor = f81._load_candidate(compiled)
    arena = _run_stage(compiled, native, gen1, candidate, corpus)
    failures = list(arena["contract_failures"])
    run_info = arena["run"]
    summary = arena["summary"]
    aggregate = None
    if summary is not None:
        scores = list(summary["pair_scores"])
        low, high = bootstrap_pair_mean_ci(scores)
        aggregate = {"pair_count": len(scores), "pair_scores": scores, "mean_pair_score": sum(scores) / len(scores), "child_better_pairs": summary["child_better_pairs"], "tied_pairs": summary["tied_pairs"], "child_worse_pairs": summary["child_worse_pairs"], "bootstrap_low": low, "bootstrap_high": high, "game_wins": summary["game_wins"], "game_draws": summary["game_draws"], "game_losses": summary["game_losses"], "completed_games": run_info["completed_games"], "completed_pairs": run_info["completed_pairs"]}
    if failures:
        classification = "HARNESS_MISMATCH"
    elif run_info["status"] != "COMPLETE":
        classification = "PARENT_ANCHORED_FULL_RESIDUAL_FINAL_CONFIRMATION_UNRESOLVED"
    elif aggregate["mean_pair_score"] > 0.5 and aggregate["child_better_pairs"] > aggregate["child_worse_pairs"]:
        classification = "PARENT_ANCHORED_FULL_RESIDUAL_FINAL_CONFIRMED"
    else:
        classification = "PARENT_ANCHORED_FULL_RESIDUAL_FINAL_CONFIRMATION_REJECTED"
    result = {"schema": "generic-chess-f81-r1-eight-lane-final-strength-confirmation-v1", "work_order": WORK_ORDER, "baseline_sha": BASELINE_SHA, "classification": classification, "parent_checkpoint_id": gen1.checkpoint_id, "child_checkpoint_id": candidate.checkpoint_id, "candidate_model_sha256": descriptor["candidate_model_sha256"], "opening_corpus": corpus_payload, "prior_evidence": prior_evidence, "arena": arena, "contract_failures": failures, "champion_before": PARENT_SHA, "champion_after": CHILD_SHA if classification == "PARENT_ANCHORED_FULL_RESIDUAL_FINAL_CONFIRMED" else PARENT_SHA, "code_provenance": {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in ("scripts/f81_r1_eight_lane_final_strength_confirmation.py", "generic_chess/learning/arena.py", "generic_chess/learning/openings.py", "generic_chess/native/semantic_engine.py")}}
    _atomic_json(RESULT_PATH, result)
    if run_info["status"] == "COMPLETE" and not failures:
        _atomic_json(ARTIFACT_PATH, result)
    return result


def main() -> None:
    result = run()
    aggregate = result["arena"].get("summary") or {}
    print(json.dumps({"classification": result["classification"], "parent_checkpoint_id": result["parent_checkpoint_id"], "child_checkpoint_id": result["child_checkpoint_id"], "fresh_pair_scores": aggregate.get("pair_scores"), "fresh_mean_pair_score": aggregate.get("mean_pair_score"), "better": aggregate.get("child_better_pairs"), "tied": aggregate.get("tied_pairs"), "worse": aggregate.get("child_worse_pairs"), "game_wins": aggregate.get("game_wins"), "game_draws": aggregate.get("game_draws"), "game_losses": aggregate.get("game_losses"), "contract_failures": result["contract_failures"]}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
