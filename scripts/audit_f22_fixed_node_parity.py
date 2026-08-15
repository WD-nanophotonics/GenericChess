"""Re-run fixed-node Native ON/OFF parity without a wall-clock cap."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import scripts.audit_f22_post_f21 as audit  # noqa: E402

OUT = ROOT / "artifacts" / "f22_post_f21_rebaseline_strength"


def main():
    audit.load_native(sys.argv[1])
    audit.m = audit.imports()
    _semantic, compiled = audit.compile_context(audit.m)
    positions, _refs, _source = audit.load_round5()
    rows = []
    for position in positions:
        for budget in (128, 256):
            native = audit.search_once(audit.m, compiled, position["sfen"], native=True, max_nodes=budget, profile_name="B")
            python = audit.search_once(audit.m, compiled, position["sfen"], native=False, max_nodes=budget, profile_name="B")
            ignored = {"evaluation_seconds", "ordering_seconds", "legal_generation_seconds", "root_scan_seconds", "time_to_first_legal_action", "time_to_first_completed_iteration", "native_legality_enabled", "native_legality_calls", "native_legality_actions", "native_legality_seconds", "native_legality_payload_seconds", "native_legality_decode_binding_seconds", "native_legality_fallbacks", "native_legality_operational_failures"}
            left = {key: value for key, value in native["stats"].items() if key not in ignored and not key.endswith("_seconds")}
            right = {key: value for key, value in python["stats"].items() if key not in ignored and not key.endswith("_seconds")}
            rows.append({"position_id": position["name"], "node_budget": budget, "native_on": {key: native[key] for key in ("move", "score", "pv", "nodes", "qnodes", "termination_reason")}, "native_off": {key: python[key] for key in ("move", "score", "pv", "nodes", "qnodes", "termination_reason")}, "logical_stats_equal": left == right, "exact_parity": all(native[key] == python[key] for key in ("move", "score", "pv", "nodes", "qnodes", "termination_reason")) and left == right})
    (OUT / "native_on_off_node_parity.json").write_text(json.dumps({"rows": rows, "fixed_node_budgets": [128, 256], "exact_all": all(row["exact_parity"] for row in rows), "wall_clock_cap_applied": False}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"rows": len(rows), "exact_all": all(row["exact_parity"] for row in rows)}, sort_keys=True))


if __name__ == "__main__":
    main()
