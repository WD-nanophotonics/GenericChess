"""F81-R2 audit and time-budget cap-contract corrective harness."""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.learning import arena as arena_module  # noqa: E402
from generic_chess.learning.arena import run_arena_game_resumable  # noqa: E402
from generic_chess.learning.openings import ArenaOpeningCorpus  # noqa: E402
from generic_chess.learning.statistics import bootstrap_pair_mean_ci  # noqa: E402
from generic_chess.native import native_available  # noqa: E402
from scripts import f59_action_spectrum_diagnosis as f59  # noqa: E402
from scripts import f77_trusted_pointwise_q_arena2_triage as f77  # noqa: E402
from scripts import f81_r1_eight_lane_final_strength_confirmation as f81r1  # noqa: E402


WORK_ORDER = "GENERICCHESS-F81-R2-TIME-BUDGET-CAP-CORRECTIVE"
BASELINE_SHA = "55c7bbcccb21d78d0398e0deecbfd5301e059392"
PROGRESS = ROOT / ".generic_chess_flow" / "f81-r1-eight-lane-final-confirmation" / "progress"
CORPUS_PATH = ROOT / "artifacts" / "f81_final_confirmation" / "openings.json"
AUDIT_PATH = ROOT / "artifacts" / "f81_final_confirmation" / "f81_r1_time_cap_audit.json"
OUT = ROOT / ".generic_chess_flow" / "f81-r2-time-budget-corrective"
PROGRESS_R2 = OUT / "progress"
RESULT_PATH = OUT / "f81_r2_results.json"
R1_REPORT_PATH = "docs/architecture/GENERICCHESS_F81_R1_EIGHT_LANE_FINAL_STRENGTH_CONFIRMATION.md"
R1_REPORT_SHA = "9273856d350f9e9a6b94eecba251baaf4fd4275f70d8ddeb82ed39f493ad851a"
R1_ARTIFACT_PATH = "artifacts/f81_final_confirmation/final_strength_evidence.json"
R1_ARTIFACT_SHA = "dc769e52c7d5d6357fabfb640c88a51ab3b0600b9c97aec8919c810b7d25e938"
ARENA_FIX_CHECKPOINT = "f592fb29a36dafb875ceaf50e88161482d518eba"
CONTAMINATED_PAIR = 5
CAP_LIKE_REASONS = {"time_budget", "time_limit", "timeout", "deadline", "cancelled", "canceled"}


def _load_manifest_and_corpus(compiled):
    manifest = json.loads((PROGRESS / "manifest.json").read_text(encoding="utf-8"))
    corpus_payload = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    corpus = f81r1.ArenaOpeningCorpus.from_dict(corpus_payload["corpus"])
    corpus.validate(compiled)
    if corpus.corpus_id != f81r1.CORPUS_ID or corpus_payload.get("corpus_id") != f81r1.CORPUS_ID:
        raise RuntimeError("F81-R2 corpus identity mismatch")
    return manifest, corpus, corpus_payload


def _cap_like(reason: str) -> bool:
    normalized = reason.strip().lower()
    return normalized in CAP_LIKE_REASONS or "deadline" in normalized


def audit_r1_progress() -> dict:
    if not native_available():
        raise RuntimeError("F81-R2 requires the native extension for legal replay audit")
    compiled, _native, _profile = f59._ruleset(f81r1.LABEL)
    manifest, corpus, corpus_payload = _load_manifest_and_corpus(compiled)
    if manifest.get("schema") != arena_module.ARENA_GAME_PROGRESS_SCHEMA:
        raise RuntimeError("F81-R2 manifest schema mismatch")
    identity = manifest["identity"]
    if identity.get("parent_checkpoint_id") != f81r1.PARENT_SHA or identity.get("child_checkpoint_id") != f81r1.CHILD_SHA:
        raise RuntimeError("F81-R2 manifest checkpoint identity mismatch")
    config, caps = f81r1._config_and_caps()
    if identity.get("ordered_openings") != corpus.to_dict()["openings"]:
        raise RuntimeError("F81-R2 manifest corpus ordering mismatch")
    expected_config = arena_module.asdict(config)
    if identity.get("config") != expected_config:
        raise RuntimeError("F81-R2 manifest config mismatch")
    expected_caps = arena_module.asdict(caps)
    if identity.get("execution_caps") != expected_caps:
        raise RuntimeError("F81-R2 manifest caps mismatch")
    files = sorted(PROGRESS.glob("game-*.json"))
    expected_names = {f"game-{pair:06d}-owner-{owner}.json" for pair in range(8) for owner in (0, 1)}
    if {path.name for path in files} != expected_names:
        raise RuntimeError("F81-R2 expected exactly sixteen F81-R1 game files")
    games = {}
    failures = []
    for path in files:
        match = re.fullmatch(r"game-(\d{6})-owner-([01])\.json", path.name)
        pair_index, owner = int(match.group(1)), int(match.group(2))
        payload = json.loads(path.read_text(encoding="utf-8"))
        expected = arena_module._game_progress_identity_for(identity, config, caps, corpus.to_dict()["openings"][pair_index], pair_index, owner, capture_search_metrics=True)
        try:
            game = arena_module._validate_game_progress(compiled, corpus.openings[pair_index], payload, expected_identity=expected, identity_sha256=manifest["identity_sha256"], config=config, capture_search_metrics=True, pair_index=pair_index, child_owner=owner)
        except Exception as exc:
            failures.append(f"{path.name}: {exc}")
            continue
        reasons = Counter(str(row.get("termination_reason", "")).strip().lower() for row in game.search_metrics)
        cap_reasons = sorted(reason for reason in reasons if _cap_like(reason))
        games[(pair_index, owner)] = game
        games.setdefault((pair_index, "audit"), {})
        games[(pair_index, "audit")][owner] = {
            "path": str(path.relative_to(ROOT)),
            "progress_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "opening_id": game.opening_id,
            "child_owner": owner,
            "result": game.result,
            "winner": game.winner,
            "child_points": game.child_points,
            "plies": game.plies,
            "telemetry_row_count": len(game.search_metrics),
            "trusted_elapsed_total_seconds": sum(float(row.get("elapsed_seconds", 0.0)) for row in game.search_metrics),
            "termination_reason_counts": dict(sorted(reasons.items())),
            "termination_reason_set": sorted(reasons),
            "max_search_nodes": max((int(row.get("nodes", 0)) for row in game.search_metrics), default=0),
            "all_root_window_pruning_true": bool(game.search_metrics) and all(row.get("root_window_pruning") is True for row in game.search_metrics),
            "missing_root_window_pruning_rows": sum("root_window_pruning" not in row for row in game.search_metrics),
            "cap_contaminated": bool(cap_reasons),
            "cap_like_reasons": cap_reasons,
        }
    pair_rows = []
    contaminated = []
    for pair_index in range(8):
        pair_games = games.get((pair_index, "audit"), {})
        if set(pair_games) != {0, 1}:
            failures.append(f"pair {pair_index} does not have both owners")
            continue
        contaminated_pair = any(pair_games[owner]["cap_contaminated"] for owner in (0, 1))
        if contaminated_pair:
            contaminated.append(pair_index)
        pair_rows.append({"pair_index": pair_index, "opening_id": pair_games[0]["opening_id"], "game_child_owner0": pair_games[0], "game_child_owner1": pair_games[1], "pair_score": (pair_games[0]["child_points"] + pair_games[1]["child_points"]) / 2.0, "cap_contaminated": contaminated_pair})
    audit = {
        "schema": "generic-chess-f81-r1-time-cap-audit-v1",
        "work_order": WORK_ORDER,
        "baseline_sha": BASELINE_SHA,
        "source_progress": str(PROGRESS.relative_to(ROOT)),
        "manifest_identity_sha256": manifest["identity_sha256"],
        "corpus_path": str(CORPUS_PATH.relative_to(ROOT)),
        "corpus_id": corpus.corpus_id,
        "corpus_content_sha256": hashlib.sha256(CORPUS_PATH.read_bytes()).hexdigest(),
        "parent_checkpoint_id": f81r1.PARENT_SHA,
        "child_checkpoint_id": f81r1.CHILD_SHA,
        "candidate_model_sha256": f81r1.CANDIDATE_MODEL_SHA,
        "opening_count": len(corpus.openings),
        "game_file_count": len(files),
        "validated_game_count": len([key for key in games if isinstance(key[1], int)]),
        "pair_count": len(pair_rows),
        "pairs": pair_rows,
        "contaminated_pair_indices": contaminated,
        "contract_failures": failures,
        "audit_classification": "TIME_BUDGET_CAP_CONTAMINATION_FOUND" if contaminated else "HARNESS_MISMATCH",
        "frozen_corpus_payload_sha256": hashlib.sha256(json.dumps(corpus_payload, sort_keys=True).encode()).hexdigest(),
    }
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_PATH.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return audit


def _validate_r2_games(compiled, corpus, config, caps) -> tuple[list[dict], list[str]]:
    manifest = json.loads((PROGRESS_R2 / "manifest.json").read_text(encoding="utf-8"))
    rows = []
    failures = []
    for path in sorted(PROGRESS_R2.glob("game-*.json")):
        match = re.fullmatch(r"game-(\d{6})-owner-([01])\.json", path.name)
        if match is None:
            failures.append(f"invalid R2 progress filename: {path.name}")
            continue
        pair_index, owner = int(match.group(1)), int(match.group(2))
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            opening = corpus.openings[pair_index]
            expected = arena_module._game_progress_identity_for(manifest["identity"], config, caps, corpus.to_dict()["openings"][pair_index], pair_index, owner, capture_search_metrics=True)
            game = arena_module._validate_game_progress(compiled, opening, payload, expected_identity=expected, identity_sha256=manifest["identity_sha256"], config=config, capture_search_metrics=True, pair_index=pair_index, child_owner=owner)
            reasons = Counter(str(row.get("termination_reason", "")).strip().lower() for row in game.search_metrics)
            cap_reasons = sorted(reason for reason in reasons if _cap_like(reason))
            rows.append({"pair_index": pair_index, "owner": owner, "game": game, "termination_reason_counts": dict(sorted(reasons.items())), "cap_like_reasons": cap_reasons})
        except Exception as exc:
            failures.append(f"R2 checkpoint validation failed for {path.name}: {exc}")
    return rows, failures


def _durable_r2_artifact(result: dict) -> dict:
    return {
        "schema": "generic-chess-f81-final-strength-evidence-v2",
        "work_order": result["work_order"],
        "baseline_sha": result["baseline_sha"],
        "classification": result["classification"],
        "invalidated_prior_result": "INVALIDATED_BY_TIME_BUDGET_CAP_CONTRACT_MISMATCH",
        "original_r1_report": {"path": R1_REPORT_PATH, "content_sha256": R1_REPORT_SHA},
        "original_r1_artifact": {"path": R1_ARTIFACT_PATH, "content_sha256": R1_ARTIFACT_SHA},
        "arena_fix_checkpoint": ARENA_FIX_CHECKPOINT,
        "time_cap_audit": {"path": str(AUDIT_PATH.relative_to(ROOT)), "content_sha256": hashlib.sha256(AUDIT_PATH.read_bytes()).hexdigest()},
        "parent_checkpoint_id": result["parent_checkpoint_id"],
        "child_checkpoint_id": result["child_checkpoint_id"],
        "candidate_model_sha256": result["candidate_model_sha256"],
        "corpus_path": str(CORPUS_PATH.relative_to(ROOT)),
        "corpus_id": result["corpus_id"],
        "corpus_content_sha256": hashlib.sha256(CORPUS_PATH.read_bytes()).hexdigest(),
        "retained_clean_pair_indices": result["retained_clean_pair_indices"],
        "rerun_pair_indices": result["rerun_pair_indices"],
        "pair_sources": result["pair_sources"],
        "fresh_pair_scores": result.get("fresh_pair_scores"),
        "fresh_mean_pair_score": result.get("fresh_mean_pair_score"),
        "fresh_child_better_pairs": result.get("fresh_child_better_pairs"),
        "fresh_tied_pairs": result.get("fresh_tied_pairs"),
        "fresh_child_worse_pairs": result.get("fresh_child_worse_pairs"),
        "fresh_bootstrap_low": result.get("fresh_bootstrap_low"),
        "fresh_bootstrap_high": result.get("fresh_bootstrap_high"),
        "fresh_game_wins": result.get("fresh_game_wins"),
        "fresh_game_draws": result.get("fresh_game_draws"),
        "fresh_game_losses": result.get("fresh_game_losses"),
        "completed_games": result["completed_games"],
        "completed_pairs": result["completed_pairs"],
        "effective_game_lanes": result["effective_game_lanes"],
        "replay_validation": result.get("replay_validation"),
        "telemetry": result.get("telemetry"),
        "contract_failures": result["contract_failures"],
        "champion_before": result["champion_before"],
        "champion_after": result["champion_after"],
    }


def run_corrective() -> dict:
    audit = audit_r1_progress()
    if audit["contaminated_pair_indices"] != [CONTAMINATED_PAIR]:
        raise RuntimeError(f"F81-R2 expected only contaminated pair [5], got {audit['contaminated_pair_indices']}")
    if OUT.exists() and any(OUT.iterdir()):
        raise RuntimeError("F81-R2 runtime namespace is not fresh")
    if not native_available():
        raise RuntimeError("F81-R2 requires the native extension")
    compiled, native, _profile = f59._ruleset(f81r1.LABEL)
    _manifest, corpus, _corpus_payload = _load_manifest_and_corpus(compiled)
    source_opening = corpus.openings[CONTAMINATED_PAIR]
    subset = ArenaOpeningCorpus(
        schema_version=corpus.schema_version,
        ruleset_fingerprint=corpus.ruleset_fingerprint,
        seed=corpus.seed,
        min_plies=corpus.min_plies,
        max_plies=corpus.max_plies,
        openings=(replace(source_opening, index=0),),
    )
    subset.validate(compiled)
    base_config, base_caps = f81r1._config_and_caps()
    config = replace(base_config, pairs=1, opening_count=1, workers=2)
    caps = replace(base_caps, max_stage_games=2, max_concurrent_games=2)
    if caps.game_lanes(config.pairs, config.workers) != 2:
        raise RuntimeError("F81-R2 effective corrective lanes are not two")
    gen1, candidate, descriptor = f81r1._load_candidate(compiled)
    first = run_arena_game_resumable(compiled, native, gen1, candidate, config, progress_dir=PROGRESS_R2, openings=subset, capture_search_metrics=True, caps=caps, stage_id="f81-r2-time-budget-corrective-pair-5")
    rows, failures = _validate_r2_games(compiled, subset, config, caps)
    telemetry = {"game_count": len(rows), "termination_reason_counts": dict(sorted(Counter(reason for row in rows for reason, count in row["termination_reason_counts"].items() for _ in range(count)).items())), "cap_like_reasons": sorted({reason for row in rows for reason in row["cap_like_reasons"]}), "max_search_nodes": max((int(metric.get("nodes", 0)) for row in rows for metric in row["game"].search_metrics), default=0), "all_root_window_pruning_true": all(metric.get("root_window_pruning") is True for row in rows for metric in row["game"].search_metrics), "missing_root_window_pruning_rows": sum("root_window_pruning" not in metric for row in rows for metric in row["game"].search_metrics)}
    if telemetry["cap_like_reasons"]:
        failures.append("corrective rerun contains cap-like search termination")
    summary = f77._summary_payload(first.summary)
    replay_validation = None
    if first.status == "COMPLETE":
        replay = run_arena_game_resumable(compiled, native, gen1, candidate, config, progress_dir=PROGRESS_R2, openings=subset, capture_search_metrics=True, caps=caps, stage_id="f81-r2-time-budget-corrective-pair-5")
        replay_summary = f77._summary_payload(replay.summary)
        replay_validation = {"status": replay.status, "completed_games": replay.completed_games, "completed_pairs": replay.completed_pairs, "summary_equal": summary == replay_summary}
        if replay.status != first.status or replay.completed_games != first.completed_games or replay.completed_pairs != first.completed_pairs or summary != replay_summary:
            failures.append("corrective replay status/count/summary differs")
    retained = {row["pair_index"]: row["pair_score"] for row in audit["pairs"] if not row["cap_contaminated"]}
    pair_sources = {str(index): {"source": "F81-R1_RETAINED_CLEAN", "pair_score": retained[index]} for index in sorted(retained)}
    fresh_scores = None
    aggregate = None
    if summary is not None and first.status == "COMPLETE" and not failures:
        fresh_scores = [retained[index] if index != CONTAMINATED_PAIR else summary["pair_scores"][0] for index in range(8)]
        low, high = bootstrap_pair_mean_ci(fresh_scores)
        better = sum(score > 0.5 for score in fresh_scores)
        tied = sum(score == 0.5 for score in fresh_scores)
        worse = sum(score < 0.5 for score in fresh_scores)
        pair_sources[str(CONTAMINATED_PAIR)] = {"source": "F81-R2_REPLACEMENT", "pair_score": summary["pair_scores"][0], "local_pair_index": 0, "original_pair_index": CONTAMINATED_PAIR}
        wins = sum(1 if row["game"].child_points == 1.0 else 0 for row in rows)
        losses = sum(1 if row["game"].child_points == 0.0 else 0 for row in rows)
        draws = len(rows) - wins - losses
        for index in retained:
            games = next(row for row in audit["pairs"] if row["pair_index"] == index)
            wins += sum(1 if games[f"game_child_owner{owner}"]["child_points"] == 1.0 else 0 for owner in (0, 1))
            losses += sum(1 if games[f"game_child_owner{owner}"]["child_points"] == 0.0 else 0 for owner in (0, 1))
            draws += 2 - sum(1 if games[f"game_child_owner{owner}"]["child_points"] in (0.0, 1.0) else 0 for owner in (0, 1))
        aggregate = {"pair_count": 8, "pair_scores": fresh_scores, "mean_pair_score": sum(fresh_scores) / 8, "child_better_pairs": better, "tied_pairs": tied, "child_worse_pairs": worse, "bootstrap_low": low, "bootstrap_high": high, "game_wins": wins, "game_draws": draws, "game_losses": losses}
    classification = "HARNESS_MISMATCH" if failures else "PARENT_ANCHORED_FULL_RESIDUAL_FINAL_CONFIRMED" if aggregate and aggregate["mean_pair_score"] > 0.5 and aggregate["child_better_pairs"] > aggregate["child_worse_pairs"] else "PARENT_ANCHORED_FULL_RESIDUAL_FINAL_CONFIRMATION_UNRESOLVED" if first.status != "COMPLETE" else "PARENT_ANCHORED_FULL_RESIDUAL_FINAL_CONFIRMATION_REJECTED"
    result = {"schema": "generic-chess-f81-r2-time-budget-cap-corrective-v1", "work_order": WORK_ORDER, "baseline_sha": BASELINE_SHA, "classification": classification, "invalidated_prior_result": "INVALIDATED_BY_TIME_BUDGET_CAP_CONTRACT_MISMATCH", "original_r1_report": {"path": R1_REPORT_PATH, "content_sha256": R1_REPORT_SHA}, "original_r1_artifact": {"path": R1_ARTIFACT_PATH, "content_sha256": R1_ARTIFACT_SHA}, "arena_fix_checkpoint": ARENA_FIX_CHECKPOINT, "time_cap_audit": {"path": str(AUDIT_PATH.relative_to(ROOT)), "content_sha256": hashlib.sha256(AUDIT_PATH.read_bytes()).hexdigest()}, "parent_checkpoint_id": gen1.checkpoint_id, "child_checkpoint_id": candidate.checkpoint_id, "candidate_model_sha256": descriptor["candidate_model_sha256"], "corpus_id": corpus.corpus_id, "retained_clean_pair_indices": sorted(retained), "rerun_pair_indices": [CONTAMINATED_PAIR], "pair_sources": pair_sources, "fresh_pair_scores": aggregate["pair_scores"] if aggregate else None, "fresh_mean_pair_score": aggregate["mean_pair_score"] if aggregate else None, "fresh_child_better_pairs": aggregate["child_better_pairs"] if aggregate else None, "fresh_tied_pairs": aggregate["tied_pairs"] if aggregate else None, "fresh_child_worse_pairs": aggregate["child_worse_pairs"] if aggregate else None, "fresh_bootstrap_low": aggregate["bootstrap_low"] if aggregate else None, "fresh_bootstrap_high": aggregate["bootstrap_high"] if aggregate else None, "fresh_game_wins": aggregate["game_wins"] if aggregate else None, "fresh_game_draws": aggregate["game_draws"] if aggregate else None, "fresh_game_losses": aggregate["game_losses"] if aggregate else None, "completed_games": len(rows) + len(retained) * 2, "completed_pairs": len(retained) + (1 if first.status == "COMPLETE" else 0), "effective_game_lanes": first.effective_game_lanes, "replay_validation": replay_validation, "telemetry": telemetry, "contract_failures": failures, "champion_before": gen1.checkpoint_id, "champion_after": candidate.checkpoint_id if classification == "PARENT_ANCHORED_FULL_RESIDUAL_FINAL_CONFIRMED" else gen1.checkpoint_id}
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ARTIFACT_PATH = f81r1.ARTIFACT_PATH
    ARTIFACT_PATH.write_text(json.dumps(_durable_r2_artifact(result), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> None:
    result = run_corrective()
    print(json.dumps({"classification": result["classification"], "fresh_pair_scores": result["fresh_pair_scores"], "fresh_mean_pair_score": result["fresh_mean_pair_score"], "better": result["fresh_child_better_pairs"], "tied": result["fresh_tied_pairs"], "worse": result["fresh_child_worse_pairs"], "game_wins": result["fresh_game_wins"], "game_draws": result["fresh_game_draws"], "game_losses": result["fresh_game_losses"], "completed_games": result["completed_games"], "completed_pairs": result["completed_pairs"], "contract_failures": result["contract_failures"]}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
