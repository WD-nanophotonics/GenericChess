import json

from scripts.f91_candidate_payload import persist_compact_payload


def test_f91_candidate_payload_persists_compact_payload_without_changes(tmp_path):
    payload = {"output_bias": 1.25, "output_weights": [0.5, -0.25], "width": 2}
    path = persist_compact_payload(tmp_path, 0.5, payload)
    assert path.name == "compact_model.json"
    assert json.loads(path.read_text(encoding="utf-8")) == payload
