from __future__ import annotations

import json
from pathlib import Path

from results.dev_aux.task2629.prepare_fresh_eval_roots import canon, load_records, walk_records


def test_walk_records_finds_nested_full_histories_without_reading_outcomes():
    first = {"ruleset_fingerprint": "rule15", "actions": []}
    second = {"ruleset_fingerprint": "other", "actions": [{"a": 1}]}
    row = {"actual_outcome": 1, "nested": {"record_before": first},
           "records": [second]}
    found = list(walk_records(row))
    assert found == [first, second]
    assert canon({"actions": [], "ruleset_fingerprint": "rule15"}) == canon(first)


def test_load_records_filters_by_pinned_fingerprint_for_jsonl_and_json():
    wanted = {"ruleset_fingerprint": "rule15", "actions": []}
    other = {"ruleset_fingerprint": "other", "actions": []}
    temp = Path(__file__).resolve().parent / ".test-temp"
    temp.mkdir(exist_ok=True)
    jsonl, source = temp / "sample.jsonl", temp / "sample.json"
    try:
        jsonl.write_text(json.dumps({"record": wanted}) + "\n"
                         + json.dumps({"record": other}) + "\n", encoding="utf-8")
        assert list(load_records(jsonl, "rule15")) == [wanted]
        source.write_text(json.dumps({"records": [wanted, other]}), encoding="utf-8")
        assert list(load_records(source, "rule15")) == [wanted]
    finally:
        jsonl.unlink(missing_ok=True)
        source.unlink(missing_ok=True)
        temp.rmdir()


def test_prep_source_has_frozen_new_family_range_and_no_terminal_filter():
    path = Path(__file__).with_name("prepare_fresh_eval_roots.py")
    text = path.read_text(encoding="utf-8")
    assert "FAMILY_RANGE = range(300_000, 350_000)" in text
    assert "actual_outcome" not in text
    assert "eval-result" not in text
