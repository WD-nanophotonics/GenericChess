"""Persist the exact F61 candidate model parameters from transient evidence."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".generic_chess_flow" / "f61-strength-first-triage" / "f61_results.json"
DEST = ROOT / "docs" / "architecture" / "GENERICCHESS_F61_MODEL_PARAMS.json"


def main() -> None:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    durable = {
        "work_order": payload["work_order"],
        "parent_checkpoint_id": payload["parent_checkpoint_id"],
        "f60_result_sha256": payload["f60_result_sha256"],
        "candidates": [
            {
                key: candidate[key]
                for key in (
                    "candidate_id", "training_distribution", "objective", "seed",
                    "parent_checkpoint_id", "checkpoint_id", "model_sha256",
                    "input_dimension", "model",
                )
            }
            for candidate in payload["candidates"]
        ],
    }
    DEST.write_text(json.dumps(durable, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
