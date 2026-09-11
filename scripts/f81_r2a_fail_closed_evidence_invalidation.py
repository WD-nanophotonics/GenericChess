"""Fail-closed invalidation of contaminated F81-R1 canonical evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


WORK_ORDER = "GENERICCHESS-F81-R2A-FAIL-CLOSED-EVIDENCE-INVALIDATION"
BASELINE_SHA = "0a814fb14ac4fa93191f681c2a6c128145450a91"
PARENT_SHA = "d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4"
CHILD_SHA = "f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4"
MODEL_SHA = "b4372d087d0e7760857efefd69413c97c8cf10b5b188dd704f5d1e308a4d32b6"
CORPUS_ID = "67b9dafc51a618645c3328228c30a8744cc8f988395a7d54d382b65276dc935c"
OLD_REPORT_SHA = "9273856d350f9e9a6b94eecba251baaf4fd4275f70d8ddeb82ed39f493ad851a"
OLD_ARTIFACT_SHA = "dc769e52c7d5d6357fabfb640c88a51ab3b0600b9c97aec8919c810b7d25e938"
AUDIT_PATH = ROOT / "artifacts" / "f81_final_confirmation" / "f81_r1_time_cap_audit.json"
AUDIT_SHA = "1c418b509654f4f054db738720880bf4435e611bd2cba589b4018d78a2c961a6"
ARTIFACT_PATH = ROOT / "artifacts" / "f81_final_confirmation" / "final_strength_evidence.json"
CORPUS_PATH = ROOT / "artifacts" / "f81_final_confirmation" / "openings.json"


def _write_pending_artifact() -> dict:
    old = json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    if old.get("schema") != "generic-chess-f81-final-strength-evidence-v1" or old.get("classification") != "PARENT_ANCHORED_FULL_RESIDUAL_FINAL_CONFIRMED":
        raise RuntimeError("F81-R2A expected the original confirmed v1 artifact")
    if hashlib.sha256(ARTIFACT_PATH.read_bytes()).hexdigest() != OLD_ARTIFACT_SHA:
        raise RuntimeError("F81-R2A original artifact SHA mismatch")
    if hashlib.sha256(AUDIT_PATH.read_bytes()).hexdigest() != AUDIT_SHA:
        raise RuntimeError("F81-R2A audit SHA mismatch")
    if audit.get("contaminated_pair_indices") != [5] or audit.get("contract_failures"):
        raise RuntimeError("F81-R2A audit does not isolate pair 5 cleanly")
    clean = [0, 1, 2, 3, 4, 6, 7]
    pending = {
        "schema": "generic-chess-f81-final-strength-evidence-v2-pending-corrective",
        "work_order": WORK_ORDER,
        "baseline_sha": BASELINE_SHA,
        "classification": "PARENT_ANCHORED_FULL_RESIDUAL_FINAL_CONFIRMATION_UNRESOLVED",
        "invalidated_prior_result": "INVALIDATED_BY_TIME_BUDGET_CAP_CONTRACT_MISMATCH",
        "original_r1_report": {"path": "docs/architecture/GENERICCHESS_F81_R1_EIGHT_LANE_FINAL_STRENGTH_CONFIRMATION.md", "content_sha256": OLD_REPORT_SHA},
        "original_r1_artifact": {"path": "artifacts/f81_final_confirmation/final_strength_evidence.json", "content_sha256": OLD_ARTIFACT_SHA},
        "time_cap_audit": {"path": str(AUDIT_PATH.relative_to(ROOT)), "content_sha256": AUDIT_SHA},
        "arena_fix_checkpoint": "f592fb29a36dafb875ceaf50e88161482d518eba",
        "parent_checkpoint_id": PARENT_SHA,
        "child_checkpoint_id": CHILD_SHA,
        "candidate_model_sha256": MODEL_SHA,
        "corpus_path": str(CORPUS_PATH.relative_to(ROOT)),
        "corpus_id": CORPUS_ID,
        "corpus_content_sha256": hashlib.sha256(CORPUS_PATH.read_bytes()).hexdigest(),
        "retained_clean_pair_indices": clean,
        "retained_clean_game_count": 14,
        "pending_rerun_pair_indices": [5],
        "invalidated_diagnostic_scores": {key: old.get(key) for key in ("fresh_pair_scores", "fresh_mean_pair_score", "fresh_child_better_pairs", "fresh_tied_pairs", "fresh_child_worse_pairs", "fresh_bootstrap_low", "fresh_bootstrap_high", "fresh_game_wins", "fresh_game_draws", "fresh_game_losses")},
        "authoritative_completion": {"clean_pair_indices": clean, "clean_game_count": 14, "contaminated_pair_indices": [5], "contaminated_pair_excluded": True},
        "contract_failures": [],
        "champion_before": PARENT_SHA,
        "champion_after": PARENT_SHA,
    }
    ARTIFACT_PATH.write_text(json.dumps(pending, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return pending


def main() -> None:
    pending = _write_pending_artifact()
    print(json.dumps({"classification": pending["classification"], "invalidated_prior_result": pending["invalidated_prior_result"], "retained_clean_pair_indices": pending["retained_clean_pair_indices"], "pending_rerun_pair_indices": pending["pending_rerun_pair_indices"], "champion_after": pending["champion_after"], "artifact_sha256": hashlib.sha256(ARTIFACT_PATH.read_bytes()).hexdigest()}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
