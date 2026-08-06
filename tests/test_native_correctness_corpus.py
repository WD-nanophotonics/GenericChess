"""Correctness corpus: reproducible hashes, child keys, perft and rebuilds."""

import json
from pathlib import Path

from generic_chess.ai.benchmark.audit_suite import build_session, standard_ruleset_specs
from generic_chess.ai.benchmark.correctness_corpus import (
    _canonical_actions_hash,
    build_corpus,
    perft,
)
from generic_chess.core.keys import position_key
from generic_chess.core.transition import legal_successors


def _committed():
    path = (
        Path(__file__).resolve().parent.parent
        / "tests"
        / "fixtures"
        / "native_correctness_corpus_v1.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def test_committed_corpus_parses_and_is_consistent():
    raw = _committed()
    assert raw["schema_version"] == 1
    assert raw["corpus_version"] == "v1"
    assert raw["fixtures"]
    for fixture in raw["fixtures"]:
        assert fixture["legal_action_count"] == len(fixture["legal_actions"])
        assert len(fixture["child_keys"]) == fixture["legal_action_count"]
        assert set(fixture["perft"]) == {"1", "2", "3"}


def test_fixture_rebuild_matches_saved():
    raw = _committed()
    fixture = raw["fixtures"][0]
    spec = next(
        s
        for s in standard_ruleset_specs()
        if s.fixture_id == fixture["ruleset_fixture_id"]
    )
    compiled, session = build_session(spec, tuple(fixture["action_prefix"]))
    assert position_key(session.state.position, compiled) == fixture["position_key"]
    actions = session.legal_actions()
    assert len(actions) == fixture["legal_action_count"]
    assert _canonical_actions_hash(actions) == fixture["legal_action_hash"]
    keys = [
        position_key(child.position, compiled)
        for _action, child in legal_successors(session.state, compiled)
    ]
    assert keys == fixture["child_keys"]
    assert perft(compiled, session.state, 1) == fixture["perft"]["1"]
    assert perft(compiled, session.state, 2) == fixture["perft"]["2"]


def test_corpus_regeneration_matches_committed():
    regenerated = build_corpus(commit="")
    raw = _committed()
    assert [f["fixture_id"] for f in regenerated["fixtures"]] == [
        f["fixture_id"] for f in raw["fixtures"]
    ]
    for a, b in zip(regenerated["fixtures"], raw["fixtures"]):
        assert a["position_key"] == b["position_key"]
        assert a["legal_action_hash"] == b["legal_action_hash"]
        assert a["child_keys"] == b["child_keys"]
        assert a["perft"] == b["perft"]
