"""Persist the exact F61 candidate model parameters from transient evidence."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.learning.serialization import stable_sha256
from scripts import f59_action_spectrum_diagnosis as f59


SOURCE = ROOT / ".generic_chess_flow" / "f61-strength-first-triage" / "f61_results.json"
DEST = ROOT / "docs" / "architecture" / "GENERICCHESS_F61_MODEL_PARAMS.json"
CORRECTED_TRAINING_CONFIG = "f61-corrected-perspective"


def _corrected_checkpoint(parent, model, seed):
    return parent.child_checkpoint(
        board_weights=parent.board_weights,
        hand_weights=parent.hand_weights,
        dynamic_weights=parent.dynamic_weights,
        compact_nonlinear=model,
        games_seen_delta=0,
        positions_seen_delta=0,
        training_updates_delta=1,
        training_config_hash=CORRECTED_TRAINING_CONFIG,
        training_seed=seed,
    )


def main() -> None:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    parent = f59._parent(f59.LABELS[1])
    if parent.checkpoint_id != payload["parent_checkpoint_id"]:
        raise RuntimeError("F61 durable model parent identity mismatch")
    candidates = [
        {
            key: candidate[key]
            for key in (
                "candidate_id", "training_distribution", "objective", "seed",
                "parent_checkpoint_id", "checkpoint_id", "model_sha256",
                "input_dimension", "model",
            )
        }
        for candidate in payload["candidates"]
    ]
    corrected = []
    originals = []
    for candidate in candidates:
        old_model = dict(candidate["model"])
        old_model_sha = stable_sha256(old_model)
        if old_model_sha != candidate["model_sha256"]:
            raise RuntimeError(f"F61 old model hash mismatch: {candidate['candidate_id']}")
        corrected_model = dict(old_model, perspective="successor_root_q")
        corrected_model_sha = stable_sha256(corrected_model)
        checkpoint = _corrected_checkpoint(
            parent, corrected_model, candidate["seed"]
        )
        shared = {
            "old_model_sha256": old_model_sha,
            "corrected_model_sha256": corrected_model_sha,
            "old_checkpoint_id": candidate["checkpoint_id"],
            "corrected_checkpoint_id": checkpoint.checkpoint_id,
        }
        originals.append({
            **candidate,
            **shared,
            "perspective": "owner0",
        })
        corrected.append({
            **candidate,
            **shared,
            "checkpoint_id": checkpoint.checkpoint_id,
            "model_sha256": corrected_model_sha,
            "model": corrected_model,
            "perspective": "successor_root_q",
        })
    durable = {
        "schema": "generic-chess-f61-model-params-v2",
        "work_order": payload["work_order"],
        "parent_checkpoint_id": payload["parent_checkpoint_id"],
        "f60_result_sha256": payload["f60_result_sha256"],
        "candidates": originals,
        "corrected_candidates": corrected,
    }
    # Preserve this large artifact's established Windows line endings so a
    # metadata repair does not rewrite its 470k-line learned tensor payload.
    with DEST.open("w", encoding="utf-8", newline="\r\n") as stream:
        stream.write(json.dumps(durable, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
