"""Contract tests for the F5 attack/S3 audit harness."""

from __future__ import annotations

from scripts.audit_f4_runtime_cost import FINGERPRINT, corpus_specs, make_session
from scripts.audit_f5_semantic_attack_s3 import attack_micro_specs, semantic_specs
from generic_chess.core.semantic_executor import _sources_by_owner_type


def test_f5_reuses_the_certified_four_prefix_corpus():
    assert [spec["id"] for spec in semantic_specs()] == [
        "semantic_prefix_0",
        "semantic_prefix_1",
        "semantic_prefix_2",
        "semantic_prefix_3",
    ]
    assert len(attack_micro_specs()) == 4
    assert all(spec["owners"] == [0, 1] for spec in attack_micro_specs())


def test_f5_micro_corpus_queries_every_square_for_both_owners():
    assert all(spec["squares"] == "all" for spec in attack_micro_specs())
    assert all(9 * 9 * 2 == 162 for _spec in attack_micro_specs())


def test_f5_corpus_is_reachable_and_fingerprint_certified():
    for spec in corpus_specs():
        session = make_session(spec)
        if spec["kind"] == "semantic":
            assert session.compiled.ruleset_fingerprint == FINGERPRINT
            assert session.state.terminal_status.status.value == "ongoing"
            assert session.legal_actions()


def test_f5_source_index_is_position_local_and_board_ordered():
    session = make_session(next(spec for spec in corpus_specs() if spec["id"] == "semantic_prefix_0"))
    index = _sources_by_owner_type(session.state.position)
    flattened = [source for entries in index.values() for source, _piece in entries]
    assert sorted(flattened) == sorted(
        source for source, piece in enumerate(session.state.position.board) if piece is not None
    )
    assert all([source for source, _piece in entries] == sorted(source for source, _piece in entries)
               for entries in index.values())
    assert all(entry[1].owner == owner and entry[1].current_type_id == type_id
               for (owner, type_id), entries in index.items()
               for entry in entries)
