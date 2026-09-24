"""Generate the pre-reference V2B candidate and content-addressed freeze record."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.audit_static_semantic_material_prior_v2b import audit_benchmarks_v2b

HYPOTHESIS = (
    "Evaluate the unchanged V2A semantic-event polynomial at rho_ref=rho_max, derived only from the executable initial conserved physical token inventory and board area."
)
FROZEN_FILES = (
    "scripts/audit_static_semantic_material_prior_v2a.py",
    "scripts/audit_static_semantic_material_prior_v2b.py",
    "scripts/freeze_static_semantic_material_prior_v2b.py",
    "scripts/validate_static_material_prior_v2b.py",
    "tests/test_static_semantic_material_prior_v2b.py",
    "docs/architecture/ADR-123-static-semantic-material-prior-v2b.md",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze() -> dict:
    result = audit_benchmarks_v2b()
    expected = {"western_chess": "1/2", "standard_shogi": "40/81"}
    for name, rho in expected.items():
        row = result["rulesets"][name]
        if not row["coverage_complete"] or not row["inventory_bound"]["complete"]:
            raise RuntimeError(f"cannot freeze incomplete V2B semantics/inventory for {name}")
        if row["inventory_bound"]["rho_max"] != rho:
            raise RuntimeError(f"unexpected inventory-derived rho_max for {name}: {row['inventory_bound']['rho_max']}")
        if row["human_metrics_computed"]:
            raise RuntimeError("pre-reference candidate unexpectedly computed human metrics")

    flow_dir = ROOT / ".generic_chess_flow"
    flow_dir.mkdir(parents=True, exist_ok=True)
    candidate_path = flow_dir / "static-semantic-material-prior-v2b-board.json"
    candidate_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    hashes = {relative: _sha256(ROOT / relative) for relative in FROZEN_FILES}
    candidate_rel = ".generic_chess_flow/static-semantic-material-prior-v2b-board.json"
    hashes[candidate_rel] = _sha256(candidate_path)
    record = {
        "schema_version": 1,
        "kind": "STATIC_MATERIAL_PRIOR_V2B_PRE_REFERENCE_FREEZE",
        "hypothesis": HYPOTHESIS,
        "selection_basis": "predeclared executable initial inventory, not human-reference fitting or density search",
        "reference_data_read": False,
        "human_metrics_computed": False,
        "test_command": ".venv\\Scripts\\python.exe -m pytest -p no:cacheprovider tests/test_static_semantic_material_prior_v2b.py tests/test_static_semantic_material_prior_v2a.py -q",
        "sha256": hashes,
        "inventory_density": {
            name: result["rulesets"][name]["inventory_bound"]["rho_max"] for name in expected
        },
    }
    freeze_path = flow_dir / "static-semantic-material-prior-v2b-freeze.json"
    freeze_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "candidate_path": str(candidate_path),
        "freeze_path": str(freeze_path),
        "rulesets": {
            name: {
                "rho_max": row["inventory_bound"]["rho_max"],
                "coverage_complete": row["coverage_complete"],
                "human_metrics_computed": row["human_metrics_computed"],
            }
            for name, row in result["rulesets"].items()
        },
        "frozen_sha256": hashes,
    }


if __name__ == "__main__":
    print(json.dumps(freeze(), indent=2, sort_keys=True))
