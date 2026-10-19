import pytest

from results.dev_aux.task2602.audit_task2593_baseline_exposure_v2 import extract_fields


def test_decodes_only_requested_fields_and_skips_nested_unrequested_payload():
    text = r'{"ignored":{"weights":[1,{"x":"}] escaped \\\""}]},"seed":7,"method":"TD","observed":true,"complete":true,"pv_terminal":true}'
    assert extract_fields(text) == {
        "seed": 7, "method": "TD", "observed": True,
        "complete": True, "pv_terminal": True,
    }


def test_requested_fields_can_appear_in_any_order():
    text = '{"pv_terminal":true,"complete":true,"observed":true,"method":"TD","seed":4,"tail":[1,2]}'
    assert extract_fields(text) == {
        "seed": 4, "method": "TD", "observed": True,
        "complete": True, "pv_terminal": True,
    }


def test_rejects_malformed_container_in_skipped_value():
    with pytest.raises(ValueError):
        extract_fields('{"ignored":[1,2},"seed":2}')


def test_rejects_non_object_line():
    with pytest.raises(ValueError):
        extract_fields('[{"seed":1}]')
