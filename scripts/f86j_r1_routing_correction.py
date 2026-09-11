"""Zero-compute correction of the F86J targeted static routing summary."""

from __future__ import annotations

import json
from pathlib import Path

try:
    from scripts.f86j_partial_reversibility_design import _targeted_route
except ModuleNotFoundError:
    from f86j_partial_reversibility_design import _targeted_route


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "artifacts" / "f86j_partial_reversibility_design" / "results.json"


def main() -> int:
    payload = json.loads(RESULT.read_text(encoding="utf-8"))
    payload["routing"]["static"] = [
        {"sample_id": row["sample_id"], "routing": _targeted_route(row)}
        for row in payload["targeted_static_mate_capacity"]
    ]
    with RESULT.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "F86J_R1_ZERO_NEW_COMPUTE_ROUTING_CORRECTION", "static_checks": 0}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
