"""Bind the pre-reference V2D candidate and its unchanged V2C input by SHA-256."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FROZEN_FILES = (
    "scripts/audit_static_semantic_material_prior_v2.py",
    "scripts/audit_static_semantic_material_prior_v2a.py",
    "scripts/audit_static_semantic_material_prior_v2b.py",
    "scripts/audit_static_semantic_material_prior_v2c.py",
    "scripts/audit_static_semantic_material_prior_v2d.py",
    "scripts/freeze_static_semantic_material_prior_v2d.py",
    "scripts/validate_static_semantic_material_prior_v2d.py",
    "tests/test_static_semantic_material_prior_v2d.py",
    "docs/architecture/ADR-125-static-semantic-material-prior-v2c.md",
    "docs/architecture/ADR-126-static-semantic-material-prior-v2d-capture-affordance.md",
    ".generic_chess_flow/static-semantic-material-prior-v2c-freeze.json",
    ".generic_chess_flow/static-semantic-material-prior-v2c-board.json",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze() -> dict:
    flow = ROOT / ".generic_chess_flow"
    candidate_path = flow / "static-semantic-material-prior-v2d-capture-affordance.json"
    if not candidate_path.is_file():
        raise RuntimeError("Run the complete pre-reference V2D audit before freezing")
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    if candidate.get("human_reference_imported") or candidate.get("human_metrics_computed"):
        raise RuntimeError("Refusing to freeze a candidate after reference access")
    if not candidate.get("coverage_complete"):
        raise RuntimeError("V2D capture semantics are incomplete; do not freeze for validation")
    if candidate.get("capture_affordance_coefficient") != 1 or candidate.get("density_scan_used") or candidate.get("transport_term_used"):
        raise RuntimeError("V2D candidate violates the frozen work-order definition")
    hashes = {relative: _sha256(ROOT / relative) for relative in FROZEN_FILES}
    candidate_rel = ".generic_chess_flow/static-semantic-material-prior-v2d-capture-affordance.json"
    hashes[candidate_rel] = _sha256(candidate_path)
    record = {"schema_version": 1, "kind": "STATIC_MATERIAL_PRIOR_V2D_PRE_REFERENCE_FREEZE",
        "reference_data_read": False, "human_metrics_computed": False,
        "capture_affordance_coefficient": 1,
        "coefficient_reason": "one unit per distinct executable opponent-board-resource removal affordance",
        "density_scan_used": False, "transport_term_used": False,
        "sha256": hashes}
    freeze_path = flow / "static-semantic-material-prior-v2d-freeze.json"
    freeze_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"freeze_path": str(freeze_path), "sha256": hashes,
            "coverage_complete": candidate["coverage_complete"],
            "candidate_classification": candidate["classification"]}


if __name__ == "__main__":
    print(json.dumps(freeze(), indent=2, sort_keys=True))
