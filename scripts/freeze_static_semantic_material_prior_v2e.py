"""Freeze the V2E transition candidate and its exact V2D dependency."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "scripts/audit_static_semantic_material_prior_v2.py",
    "scripts/audit_static_semantic_material_prior_v2a.py",
    "scripts/audit_static_semantic_material_prior_v2b.py",
    "scripts/audit_static_semantic_material_prior_v2c.py",
    "scripts/audit_static_semantic_material_prior_v2d.py",
    "scripts/audit_static_semantic_material_prior_v2e.py",
    "scripts/freeze_static_semantic_material_prior_v2d.py",
    "scripts/freeze_static_semantic_material_prior_v2e.py",
    "scripts/validate_static_semantic_material_prior_v2d.py",
    "scripts/validate_static_semantic_material_prior_v2e.py",
    "tests/test_static_semantic_material_prior_v2d.py",
    "tests/test_static_semantic_material_prior_v2e.py",
    "docs/architecture/ADR-125-static-semantic-material-prior-v2c.md",
    "docs/architecture/ADR-126-static-semantic-material-prior-v2d-capture-affordance.md",
    "docs/architecture/ADR-127-static-semantic-material-prior-v2e-type-transition-option-value.md",
    ".generic_chess_flow/static-semantic-material-prior-v2e-key-identity-erratum.json",
    ".generic_chess_flow/static-semantic-material-prior-v2d-freeze.json",
    ".generic_chess_flow/static-semantic-material-prior-v2d-capture-affordance.json",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze() -> dict:
    flow = ROOT / ".generic_chess_flow"
    previous_freeze = flow / "static-semantic-material-prior-v2e-freeze.json"
    previous_validation = flow / "static-semantic-material-prior-v2e-human-validation.json"
    if previous_freeze.is_file():
        old_freeze = json.loads(previous_freeze.read_text(encoding="utf-8"))
        old_validation = json.loads(previous_validation.read_text(encoding="utf-8")) if previous_validation.is_file() else {}
        erratum = {
            "kind": "STATIC_MATERIAL_PRIOR_V2E_PRIOR_FREEZE_INVALIDATED_BY_REFERENCE_SYNTAX_KEY_ALIAS",
            "finding": "Different compiled square-ref syntaxes resolving to the same actual removed square/disposition were split into multiple transition identities.",
            "correction": "Transition identity uses resolved physical removed-square/disposition pairs; original ref syntax remains ledger-only.",
            "invalidated_freeze_sha256": _sha(previous_freeze),
            "invalidated_candidate_sha256": old_freeze.get("sha256", {}).get(
                ".generic_chess_flow/static-semantic-material-prior-v2e-type-transition.json"),
            "invalidated_validation_sha256": _sha(previous_validation) if previous_validation.is_file() else None,
            "invalidated_validation_summary": {
                "classification": old_validation.get("classification"),
                "gate_summary": old_validation.get("gate_summary"),
                "western_chess_v2e_ratios": old_validation.get("rulesets", {}).get("western_chess", {}).get("v2e", {}).get("pawn_normalized_ratios"),
            },
            "scope": "Only event-key canonicalization changed; V2D base, transition recurrence, coefficient, temporal assumption, gates and reference data are unchanged.",
        }
        (flow / "static-semantic-material-prior-v2e-key-identity-erratum.json").write_text(
            json.dumps(erratum, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    candidate_path = flow / "static-semantic-material-prior-v2e-type-transition.json"
    if not candidate_path.is_file():
        raise RuntimeError("Run the complete pre-reference V2E audit before freezing")
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    if candidate.get("human_reference_imported") or candidate.get("human_metrics_computed"):
        raise RuntimeError("Refusing to freeze after reference access")
    if not candidate.get("base_v2d_reproduced") or not candidate.get("coverage_complete"):
        raise RuntimeError("V2D reproduction or transition coverage is incomplete")
    if candidate.get("transition_coefficient") != 1 or candidate.get("temporal_discount_used"):
        raise RuntimeError("Candidate differs from the frozen V2E hypothesis")
    hashes = {relative: _sha(ROOT / relative) for relative in FILES}
    candidate_rel = ".generic_chess_flow/static-semantic-material-prior-v2e-type-transition.json"
    hashes[candidate_rel] = _sha(candidate_path)
    record = {"schema_version": 1, "kind": "STATIC_MATERIAL_PRIOR_V2E_PRE_REFERENCE_FREEZE",
        "reference_data_read": False, "human_metrics_computed": False,
        "base_v2d_reproduced": True, "transition_coefficient": 1,
        "temporal_discount_used": False, "transport_term_used": False,
        "density_scan_used": False, "sha256": hashes}
    path = flow / "static-semantic-material-prior-v2e-freeze.json"
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"freeze_path": str(path), "candidate_classification": candidate["classification"],
            "coverage_complete": candidate["coverage_complete"], "hash_count": len(hashes), "sha256": hashes}


if __name__ == "__main__":
    print(json.dumps(freeze(), indent=2, sort_keys=True))
