"""Frozen V2B rule-only board prior at the inventory-derived full density.

The semantic event construction is shared with V2A. Only evaluation of each
conditional density polynomial changes: V2B evaluates it at rho_max instead of
integrating it over Uniform[0, rho_max]. This module imports no human targets.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_static_semantic_material_prior_v2a import audit_ruleset_v2a


def audit_ruleset_v2b(compiled: Any) -> dict[str, Any]:
    return audit_ruleset_v2a(compiled, fixed_at_rho_max=True)


def audit_benchmarks_v2b() -> dict[str, Any]:
    rulesets = {
        "western_chess": compile_semantic_ruleset(build_western_chess_ruleset()),
        "standard_shogi": compile_semantic_ruleset(build_standard_shogi_ruleset()),
    }
    results: dict[str, Any] = {}
    for name, compiled in rulesets.items():
        v2a = audit_ruleset_v2a(compiled)
        v2b = audit_ruleset_v2b(compiled)
        rows = v2b["ledger"]
        for type_id, row in rows.items():
            previous = v2a["ledger"][type_id]
            row["v2_fixed_rho_2_3_exact"] = previous["fixed_three_label_reproduction"]["v2a_semantics_at_rho_2_3"]
            row["v2a_uniform_0_rho_max_board_intrinsic"] = previous["v2a_phase_averaged_board_intrinsic"]
            row["v2a_uniform_0_rho_max_exact"] = previous["v2a_raw_exact"]
            row["v2a_components"] = previous["components"]
            row["v2a_components_exact"] = previous["components_exact"]
        results[name] = v2b
    return {
        "schema_version": 1,
        "kind": "STATIC_MATERIAL_PRIOR_V2B_FULL_INVENTORY_DENSITY_FREEZE_CANDIDATE",
        "human_metrics_computed": False,
        "human_reference_imported": False,
        "density_hypothesis_recorded_before_validation": True,
        "rulesets": results,
    }


def main() -> int:
    result = audit_benchmarks_v2b()
    output = ROOT / ".generic_chess_flow" / "static-semantic-material-prior-v2b-board.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        name: {
            "classification": row["classification"],
            "coverage_complete": row["coverage_complete"],
            "inventory_bound_complete": row["inventory_bound"]["complete"],
            "rho_max": row["inventory_bound"]["rho_max"],
            "human_metrics_computed": row["human_metrics_computed"],
        }
        for name, row in result["rulesets"].items()
    }
    print(json.dumps({"output": str(output), "rulesets": summary}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
