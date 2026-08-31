import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def test_f32_qsearch_diagnosis_contract():
    path = ROOT / "tests" / "fixtures" / "f32_qsearch_diagnosis.json"
    if not path.is_file():
        pytest.skip("F32 evidence is generated after manifest freeze")
    result = json.loads(path.read_text(encoding="utf-8"))
    assert result["production_changed"] is False
    assert result["lazy_and_noisy"]["LAZY_NONCHECK_QSEARCH_VALUE_PARITY"] is True
    assert result["lazy_and_noisy"]["variant"] == "LAZY_NONCHECK_LEGAL_GENERATION"
    assert set(result["reduced_noisy_variants"]) == {"Q0_PRODUCTION_EXACT", "Q1_CAPTURES_PROMOTIONS", "Q2_PLUS_CHECKING_BOARD_MOVES", "Q3_PLUS_CHECKING_DROPS"}
    assert result["next_boundary"] in {"F33_QUIESCENCE_LAZY_GENERATION_IMPLEMENTATION", "F33_SEMANTIC_CHECKING_ACTION_DISCOVERY_FASTPATH", "F33_QUIESCENCE_BUDGET_ARCHITECTURE", "F33_IN_CHECK_SEARCH_RUNTIME_OPTIMIZATION", "F33_RULE_DERIVED_EVALUATOR_REENTRY", "F33_STANDARD_SHOGI_MINIMAL_INTERVENTION_SELECTION"}
    assert all(result["flags"].values())
