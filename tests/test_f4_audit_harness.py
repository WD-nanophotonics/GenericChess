"""Non-interference and determinism checks for the F4 audit harness."""

from __future__ import annotations

from scripts.audit_f4_runtime_cost import FINGERPRINT, corpus_specs, make_session, profile_config


def test_f4_corpus_is_fixed_and_contains_four_semantic_prefixes():
    specs = corpus_specs()
    assert [spec["id"] for spec in specs] == [
        "legacy_draw_root",
        "continuous_check_prefix",
        "semantic_prefix_0",
        "semantic_prefix_1",
        "semantic_prefix_2",
        "semantic_prefix_3",
    ]
    assert sum(spec["kind"] == "semantic" for spec in specs) == 4


def test_f4_semantic_corpus_has_certified_fingerprint_and_reachable_sessions():
    for spec in corpus_specs():
        session = make_session(spec)
        assert session.state.terminal_status.status.value == "ongoing"
        if spec["kind"] == "semantic":
            assert session.compiled.ruleset_fingerprint == FINGERPRINT
            assert len(session._search_witnesses) == len(session.state.history)
            assert session.legal_actions()


def test_f4_profiles_are_exactly_frozen():
    profile_a = profile_config("A")
    profile_b = profile_config("B")
    assert profile_a["max_depth"] == 2
    assert profile_a["max_nodes"] == 512
    assert profile_a["quiescence_max_depth"] == 0
    assert profile_a["use_tt"] is True and profile_a["use_ordering"] is False
    assert profile_b["max_depth"] == 2
    assert profile_b["max_nodes"] == 256
    assert profile_b["quiescence_max_depth"] == 4
    assert profile_b["use_tt"] is True and profile_b["use_ordering"] is True
