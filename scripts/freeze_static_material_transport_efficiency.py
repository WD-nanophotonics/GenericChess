"""Freeze transport feature and raw Chess/Shogi graphs before residual inspection."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.static_material_transport_efficiency import audit_benchmarks

FROZEN_FILES = (
    "scripts/static_material_transport_efficiency.py",
    "scripts/freeze_static_material_transport_efficiency.py",
    "scripts/validate_static_material_transport_efficiency.py",
    "tests/test_static_material_transport_efficiency.py",
    "docs/architecture/ADR-124-static-material-transport-efficiency.md",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze() -> dict:
    result = audit_benchmarks()
    expected = {"western_chess": "1/2", "standard_shogi": "40/81"}
    for name, rho in expected.items():
        row = result["rulesets"][name]
        if not row["coverage_complete"]:
            raise RuntimeError(f"incomplete transport graph coverage for {name}")
        if row["inventory_bound"]["rho_max"] != rho:
            raise RuntimeError(f"unexpected V2B density for {name}: {row['inventory_bound']['rho_max']}")
    flow_dir = ROOT / ".generic_chess_flow"
    flow_dir.mkdir(parents=True, exist_ok=True)
    raw_path = flow_dir / "static-material-transport-efficiency-raw.json"
    raw_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    hashes = {relative: _sha256(ROOT / relative) for relative in FROZEN_FILES}
    raw_rel = ".generic_chess_flow/static-material-transport-efficiency-raw.json"
    hashes[raw_rel] = _sha256(raw_path)
    manifest = {
        "schema_version": 1,
        "kind": "STATIC_MATERIAL_TRANSPORT_EFFICIENCY_FEATURE_FREEZE",
        "reference_data_read": False,
        "v2b_residuals_read": False,
        "edge_cost_interpretation": "expected independent opportunity samples under the fixed local V2B occupancy measure; not real-game moves, time, or material value",
        "sha256": hashes,
        "rho_max": {name: result["rulesets"][name]["inventory_bound"]["rho_max"] for name in expected},
    }
    manifest_path = flow_dir / "static-material-transport-efficiency-freeze.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "raw_path": str(raw_path),
        "freeze_path": str(manifest_path),
        "classification": result["classification"],
        "coverage_complete": {name: row["coverage_complete"] for name, row in result["rulesets"].items()},
        "sha256": hashes,
    }


if __name__ == "__main__":
    print(json.dumps(freeze(), indent=2, sort_keys=True))
