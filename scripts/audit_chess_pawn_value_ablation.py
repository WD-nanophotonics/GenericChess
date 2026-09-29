"""Single-parameter causal ablation on the frozen pawn capture/mate root."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.audit_chess_mate2_qsearch import _python_search
from scripts.audit_chess_material_change_outcome import FEN
from scripts.f156_known_game_shallow_search_equivalence import _values, _western_pair, _western_state


def run_probe() -> dict:
    compiled, _ = _western_pair()
    state = _western_state(compiled, FEN)
    indexed = _values(compiled)
    rows = {}
    for pawn_value in (indexed["P"], 0):
        values = dict(indexed)
        values["P"] = pawn_value
        for qdepth in (0, 4):
            rows[f"p{pawn_value}_q{qdepth}"] = _python_search(
                compiled, state, values, 2, qdepth
            )
    base_q0 = rows[f"p{indexed['P']}_q0"]
    zero_q0 = rows["p0_q0"]
    base_q4 = rows[f"p{indexed['P']}_q4"]
    zero_q4 = rows["p0_q4"]
    valid = (
        base_q0["action"]["pattern_id"].endswith("capture")
        and zero_q0["action"]["pattern_id"].endswith("quiet")
        and base_q0["action"] != zero_q0["action"]
        and base_q4["action"] == zero_q4["action"]
        and all(row["completed_depth"] == 2 for row in rows.values())
    )
    return {
        "classification": "PAWN_VALUE_SEARCH_SENSITIVITY_PASS" if valid else "OBSERVATION_CHANGED",
        "root_fen": FEN,
        "control_profile": indexed,
        "ablation": "P=0, all other indexed values unchanged",
        "rows": rows,
    }


if __name__ == "__main__":
    result = run_probe()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["classification"] == "PAWN_VALUE_SEARCH_SENSITIVITY_PASS" else 1)
