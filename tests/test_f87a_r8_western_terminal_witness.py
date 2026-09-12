import json

from scripts.f87a_r8_western_terminal_witness import run


def test_western_terminal_witness_is_legal_and_not_dynamic_admission(tmp_path):
    result = run(tmp_path)
    assert result == json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert result["status"] == "RESULT_COMPLETE"
    assert result["plies"] == 7
    assert result["terminal_status"] == "checkmate"
    assert result["winner"] == 0
    assert result["natural_legal_witness"] is True
    assert result["dynamic_viability_pass"] is False
    assert result["training_steps"] == 0
