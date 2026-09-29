"""Post-freeze Chess/Shogi validation of first-action service pilot.

The Xiangqi human material holdout is not accessed in this script.
"""

from __future__ import annotations

from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.first_action_service_pilot import audit_first_action_service
from scripts.freeze_first_action_service_pilot import _project

FREEZE = ROOT / "docs/research/data/first_action_service_chess_shogi_preref.json"
OUTPUT = ROOT / "docs/research/data/first_action_service_chess_shogi_validation.json"
SHOGI_REFERENCE = ROOT / "tests/fixtures/f40_material_prior_audit.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preflight(frozen: dict) -> dict:
    """Reproduce all frozen inputs/results before any reference is opened."""
    if frozen.get("classification") != "FIRST_ACTION_SERVICE_CHESS_SHOGI_PREREFERENCE":
        raise RuntimeError("wrong first-action service freeze classification")
    if frozen.get("human_reference_imported") is not False or frozen.get(
            "xiangqi_material_reference_imported") is not False:
        raise RuntimeError("pre-reference freeze records reference access")
    for relative, expected in frozen["input_sha256"].items():
        if _sha(ROOT / relative) != expected:
            raise RuntimeError(f"frozen input hash mismatch: {relative}")
    reproduced = {}
    for name, builder in (("western_chess", build_western_chess_ruleset),
                          ("standard_shogi", build_standard_shogi_ruleset)):
        actual = _project(audit_first_action_service(compile_semantic_ruleset(builder()),
                                                     max_seconds=60))
        actual_json = json.loads(json.dumps(actual))
        if actual_json != frozen["rulesets"][name]:
            raise RuntimeError(f"frozen result mismatch: {name}")
        reproduced[name] = actual_json
    return reproduced


def validate() -> dict:
    frozen = json.loads(FREEZE.read_text(encoding="utf-8"))
    try:
        reproduced = preflight(frozen)
    except Exception as error:
        return {"classification": "FIRST_ACTION_SERVICE_VALIDATION_INCONCLUSIVE",
                "human_reference_read": False,
                "xiangqi_human_reference_read": False,
                "reason": str(error)}

    # The existing reference fixture is opened only after exact preflight.
    from scripts.validate_static_semantic_material_prior_v2d import (
        CHESS_BANDS, CHESS_REF, SHOGI_GATES, SHOGI_TYPES, _metrics,
    )
    fixture = json.loads(SHOGI_REFERENCE.read_text(encoding="utf-8"))
    chess_exact = reproduced["western_chess"]["raw_board_exact"]
    chess = {type_id: float(Fraction(chess_exact[type_id])) for type_id in CHESS_REF}
    ratios = {type_id: chess[type_id] / chess["P"] for type_id in CHESS_BANDS}
    bands = {type_id: {
        "ratio": ratios[type_id], "band": list(CHESS_BANDS[type_id]),
        "pass": CHESS_BANDS[type_id][0] <= ratios[type_id] <= CHESS_BANDS[type_id][1],
    } for type_id in CHESS_BANDS}
    ordering = (chess["P"] > 0 and chess["P"] < chess["N"]
                and chess["P"] < chess["B"] and chess["N"] < chess["R"]
                and chess["B"] < chess["R"] < chess["Q"])
    chess_pass = all(row["pass"] for row in bands.values()) and ordering

    shogi_ref = {
        type_id: float(fixture["standard_shogi_human_validation"]["human_reference"]["board"][type_id])
        for type_id in SHOGI_TYPES
    }
    shogi_exact = reproduced["standard_shogi"]["raw_board_exact"]
    shogi = {type_id: float(Fraction(shogi_exact[type_id])) for type_id in SHOGI_TYPES}
    shogi_metrics = _metrics(shogi, shogi_ref, SHOGI_TYPES)
    shogi_pass = all(shogi_metrics[metric] >= threshold
                     for metric, threshold in SHOGI_GATES.items())
    return {
        "classification": ("FIRST_ACTION_SERVICE_VALIDATION_PASS"
                           if chess_pass and shogi_pass else "FIRST_ACTION_SERVICE_VALIDATION_REJECTED"),
        "human_reference_read": True,
        "xiangqi_human_reference_read": False,
        "prereference_artifact_sha256": _sha(FREEZE),
        "shogi_reference_fixture_sha256": _sha(SHOGI_REFERENCE),
        "implementation_commit": frozen["implementation_commit"],
        "chess": {
            "raw_board": chess, "pawn_normalized_ratios": ratios,
            "ratio_bands": bands, "sensible_ordering_positive_pawn": ordering,
            "metrics_vs_reference": _metrics(chess, CHESS_REF, list(CHESS_REF)),
            "gate_pass": chess_pass,
        },
        "shogi": {
            "scope": "board_mode_only; held values remain coarse diagnostics",
            "raw_board": shogi, "metrics_vs_reference": shogi_metrics,
            "frozen_gates": SHOGI_GATES, "gate_pass": shogi_pass,
            "rook_vs_promoted_rook": {
                "candidate_R": shogi["R"], "candidate_TR": shogi["TR"],
                "reference_R": shogi_ref["R"], "reference_TR": shogi_ref["TR"],
            },
        },
        "gate_summary": {"western_chess": chess_pass, "standard_shogi": shogi_pass},
    }


if __name__ == "__main__":
    result = validate()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"classification": result["classification"],
                      "gate_summary": result.get("gate_summary"),
                      "output": str(OUTPUT.relative_to(ROOT))}, indent=2))
