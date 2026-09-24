"""Create the pre-reference V2C raw candidate and content-hash freeze record."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FROZEN_FILES = (
    "scripts/audit_static_semantic_material_prior_v2.py",
    "scripts/audit_static_semantic_material_prior_v2a.py",
    "scripts/audit_static_semantic_material_prior_v2b.py",
    "scripts/audit_static_semantic_material_prior_v2c.py",
    "scripts/freeze_static_semantic_material_prior_v2c.py",
    "scripts/validate_static_semantic_material_prior_v2c.py",
    "tests/test_static_semantic_material_prior_v2c.py",
    "docs/architecture/ADR-125-static-semantic-material-prior-v2c.md",
    ".generic_chess_flow/static-semantic-material-prior-v2c-source-double-count-erratum.json",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze() -> dict:
    flow_dir = ROOT / ".generic_chess_flow"
    prior_freeze_path = flow_dir / "static-semantic-material-prior-v2c-freeze.json"
    prior_validation_path = flow_dir / "static-semantic-material-prior-v2c-human-validation.json"
    if prior_freeze_path.is_file():
        prior_freeze = json.loads(prior_freeze_path.read_text(encoding="utf-8"))
        prior_validation = json.loads(prior_validation_path.read_text(encoding="utf-8")) if prior_validation_path.is_file() else {}
        erratum_path = flow_dir / "static-semantic-material-prior-v2c-source-double-count-erratum.json"
        erratum = {
            "kind": "STATIC_MATERIAL_PRIOR_V2C_PRIOR_FREEZE_INVALIDATED_BY_SOURCE_DOUBLE_COUNT",
            "scope": "Only the source double-count in A-1 non-source joint occupancy counts was corrected; all other model choices and gates remain unchanged.",
            "invalidated_freeze_sha256": _sha256(prior_freeze_path),
            "invalidated_candidate_sha256": prior_freeze.get("sha256", {}).get(
                ".generic_chess_flow/static-semantic-material-prior-v2c-board.json"
            ),
            "invalidated_validation_sha256": _sha256(prior_validation_path) if prior_validation_path.is_file() else None,
            "invalidated_validation_summary": {
                "classification": prior_validation.get("classification"),
                "gate_summary": prior_validation.get("gate_summary"),
                "western_chess_v2c_ratios": prior_validation.get("rulesets", {}).get("western_chess", {}).get("v2c", {}).get("pawn_normalized_ratios"),
            },
            "confirmed_error": {
                "chess_non_source_expected_occupied": "33/2",
                "chess_invalid_observed_occupied": "35/2",
                "shogi_non_source_expected_occupied": "41/2",
                "shogi_invalid_observed_occupied": "43/2",
            },
        }
        erratum_path.write_text(json.dumps(erratum, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    candidate_path = flow_dir / "static-semantic-material-prior-v2c-board.json"
    if not candidate_path.is_file():
        raise RuntimeError("Run the complete pre-reference V2C audit before freezing")
    result = json.loads(candidate_path.read_text(encoding="utf-8"))
    if result.get("human_reference_imported") or result.get("human_metrics_computed"):
        raise RuntimeError("Refusing to freeze a candidate that has accessed human references")
    for name, row in result["rulesets"].items():
        if not row["coverage_complete"] or row["human_reference_imported"] or row["human_metrics_computed"]:
            raise RuntimeError(f"V2C candidate is not ready to freeze for {name}")
        if not row["token_state_ledger"]["complete"]:
            raise RuntimeError(f"V2C token-state ledger is incomplete for {name}")
    flow_dir.mkdir(parents=True, exist_ok=True)
    hashes = {relative: _sha256(ROOT / relative) for relative in FROZEN_FILES}
    candidate_rel = ".generic_chess_flow/static-semantic-material-prior-v2c-board.json"
    hashes[candidate_rel] = _sha256(candidate_path)
    freeze_record = {
        "schema_version": 1,
        "kind": "STATIC_MATERIAL_PRIOR_V2C_PRE_REFERENCE_FREEZE",
        "reference_data_read": False,
        "human_metrics_computed": False,
        "transport_term_used": False,
        "free_density_parameter": False,
        "density_scan_used": False,
        "probability_assumptions": result["rulesets"],
        "sha256": hashes,
    }
    # Keep full deterministic PMFs/ledgers in the candidate file; the manifest
    # binds them by hash without duplicating the evidence.
    freeze_path = flow_dir / "static-semantic-material-prior-v2c-freeze.json"
    freeze_path.write_text(json.dumps(freeze_record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "candidate_path": str(candidate_path),
        "freeze_path": str(freeze_path),
        "sha256": hashes,
        "rulesets": {
            name: {
                "coverage_complete": row["coverage_complete"],
                "board_count_mean": row["board_token_count_distribution"]["mean_exact"],
                "board_count_variance": row["board_token_count_distribution"]["variance_exact"],
                "owner_model": row["token_state_ledger"]["owner_model"],
            }
            for name, row in result["rulesets"].items()
        },
    }


if __name__ == "__main__":
    print(json.dumps(freeze(), indent=2, sort_keys=True))
