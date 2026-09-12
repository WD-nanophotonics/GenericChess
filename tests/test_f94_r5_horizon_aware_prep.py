"""Result-free invariants for the R5 horizon-aware PREP."""

from __future__ import annotations

import json

import scripts.f94_r5_horizon_aware_prep as r5


def test_r5_prep_is_result_free_and_freezes_horizon_and_trace_contract(tmp_path):
    output = tmp_path / "r5-prep.json"
    payload = r5.build_prep(output=output)

    assert payload["schema"] == "generic-chess-f94-r5-horizon-aware-prep-v2"
    assert payload["status"] == "PREP_FROZEN"
    assert payload["result_free"] is True
    assert payload["r3_result_used"] is False
    assert payload["qualification_authority"]["path"] == "docs/architecture/GENERICCHESS_F94_R2_STRENGTH_RESPONSE_PREP.json"
    assert payload["protocol_source_sha"] == payload["source_sandbox_sha"]
    assert payload["budgets"]["nodes_per_move"] == [256, 1024, 4096]
    assert payload["gates"]["child_only_ceiling_fraction"]["threshold"] == 0.5
    assert payload["gates"]["strongest_vs_weakest_horizon_fraction"]["threshold"] == 0.5
    assert payload["action_trace_contract"]["required_for_all_games"] is True
    for candidate in payload["candidates"]:
        prep = candidate["prep"]
        assert prep["schema"] == "generic-chess-strength-response-horizon-aware-prep-v2"
        assert prep["max_ply"] > 0
        assert prep["action_trace_schema"] == "generic-chess-strength-response-action-trace-v1"
        assert candidate["layer_d_prerequisite"] in {"READY", "SHORT_CIRCUIT"}
    assert json.loads(output.read_text(encoding="utf-8")) == payload
