from __future__ import annotations

import json
from pathlib import Path

from generic_chess.ai.evaluation.analyzer import build_movement_capability, profile_movement_atoms
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import _median, _raw_capability_score
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs/research/data/static_5x5_price_20261020/candidate96/rule-522001.json"
OUTPUT = ROOT / "docs/research/data/cross_size_static_price_sensitivity_20261020.json"
SIZES = (4, 5, 8)


def build() -> dict:
    compiled = compile_ruleset(ruleset_from_dict(json.loads(SOURCE.read_text(encoding="utf-8"))))
    config = EvaluationConfig()
    types = [piece for piece in compiled.piece_types if not piece.is_anchor]
    atoms = {piece.type_id: profile_movement_atoms(compiled, piece.type_id) for piece in types}
    result = {
        "schema": "primary-cross-size-static-price-sensitivity-v1",
        "question": "Do fixed movement atoms preserve normalized static ratios when only board size changes?",
        "scope": "One frozen generated rule; direct movement capability only; no setup, promotion, drop, state, game utility, or population claim.",
        "source": str(SOURCE.relative_to(ROOT)).replace("\\", "/"),
        "sizes": {},
    }
    for size in SIZES:
        raw = {type_id: _raw_capability_score(build_movement_capability(size, type_atoms, config), config)
               for type_id, type_atoms in atoms.items()}
        median = _median(list(raw.values()))
        normalized = {key: max(1, min(10_000, int(round(1000 * value / median))))
                      for key, value in raw.items()}
        result["sizes"][str(size)] = {
            "ordinary_median_raw": median,
            "raw_capability": raw,
            "normalized_board_value": normalized,
            "rank_desc": sorted(normalized, key=lambda key: (-normalized[key], key)),
        }
    for smaller, larger in ((4, 5), (5, 8), (4, 8)):
        a = result["sizes"][str(smaller)]["normalized_board_value"]
        b = result["sizes"][str(larger)]["normalized_board_value"]
        result.setdefault("ratios", {})[f"{smaller}x{smaller}_to_{larger}x{larger}"] = {
            "P_over_B": [a["P"] / a["B"], b["P"] / b["B"]],
            "A_over_B": [a["A"] / a["B"], b["A"] / b["B"]],
            "rank_order_same": result["sizes"][str(smaller)]["rank_desc"] == result["sizes"][str(larger)]["rank_desc"],
        }
    return result


if __name__ == "__main__":
    data = build()
    OUTPUT.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(data, indent=2, sort_keys=True))
    print(f"\nWrote {OUTPUT.relative_to(ROOT)}")
