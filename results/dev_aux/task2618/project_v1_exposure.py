"""Create a public, outcome-free projection of v1 root exposure metadata."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "results/dev_aux/task2618"
SOURCE = TASK / "learner-comparison-v1/games.jsonl"
OUTPUT = TASK / "learner-comparison-v4-prep/v1-exposure-projection.json"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def project(games_raw: bytes) -> dict:
    rows = []
    for line in games_raw.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        family = row.get("family")
        unstarted = row.get("unstarted") is True
        if not isinstance(family, int):
            if unstarted:
                continue
            raise ValueError("started v1 row has no integer family id")
        rows.append({"family": family, "unstarted": unstarted})
    return {
        "status": "OUTCOME_FREE_EXPOSURE_PROJECTION",
        "source_path": SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256": sha(games_raw),
        "projected_fields": ["family", "unstarted"],
        "row_count": len(rows),
        "rows": rows,
        "outcome_fields_used": False,
    }


def main() -> dict:
    if OUTPUT.exists():
        raise FileExistsError(f"write-once v1 exposure projection exists: {OUTPUT}")
    projection = project(SOURCE.read_bytes())
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(projection, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    with OUTPUT.open("xb") as stream:
        stream.write(raw)
        stream.flush()
    return {"path": OUTPUT.relative_to(ROOT).as_posix(), "sha256": sha(raw),
            "rows": projection["row_count"], "outcome_fields_used": False}


if __name__ == "__main__":
    print(json.dumps(main(), indent=2, sort_keys=True))
