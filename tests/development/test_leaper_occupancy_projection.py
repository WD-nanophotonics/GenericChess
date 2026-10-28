"""Independent-Core and deliberately corrupted-source checks for the witness."""
from collections import Counter
from dataclasses import replace
import json
from pathlib import Path

import pytest

from generic_chess.core.position import Hands
from generic_chess.core.identity import position_identity_key
from generic_chess.core.search_runtime import RuntimePositionIdentity
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from scripts import verify_leaper_occupancy_projection as witness
from scripts import measure_leaper_incidence_obligations as census


@pytest.fixture(scope="module")
def data():
    fixture = json.loads((Path(__file__).parents[1] / "fixtures" /
                         "leaper_occupancy_projection.json").read_text(encoding="utf-8"))
    compiled = compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(fixture["RuleSet"]))
    session = GameSession.replay(compiled, deserialize_game_record(json.dumps(fixture["record"])))
    types, forward, reverse, _ = witness.incidence(compiled)
    return fixture, compiled, session.state.position, types, forward, reverse


def test_all_sources_include_empty_and_friendly_target_pseudoattacks(data):
    _, compiled, position, types, forward, reverse = data
    stats, witnesses = Counter(), {}
    witness.check_position(position, compiled, types, forward, reverse, stats, witnesses)
    assert stats["core_attack_comparisons"] == 50
    assert stats["empty_target_comparisons"] and stats["friendly_target_comparisons"]
    overlap = witnesses["overlap"]
    assert overlap["remaining_sources"] and not overlap["naive_xor_says_attacked"]


def test_boolean_agreement_does_not_certify_source_identity(data):
    _, compiled, position, types, forward, reverse = data
    # In this published root K0, A2 and B10 all attack square5. Losing K0
    # from the reverse index leaves the Boolean answer unchanged, but makes
    # future source deletions unsound. The source witness must reject it.
    corrupted = dict(reverse)
    assert corrupted[0, "K", 5] & 1
    corrupted[0, "K", 5] &= ~1
    occ = witness.occupation(position, compiled, types)
    assert bool(witness.sources(occ, corrupted, types, 0, 5))
    assert semantic_engine_for(compiled).is_square_attacked(position, 5, 0)
    with pytest.raises(AssertionError):
        witness.check_position(position, compiled, types, forward, corrupted, Counter(), {})


@pytest.mark.parametrize("kind", ["quiet", "capture"])
def test_literal_published_delta_and_each_undo_prefix(data, kind):
    fixture, compiled, _, types, forward, reverse = data
    example = fixture[kind]
    session = GameSession.replay(compiled, deserialize_game_record(json.dumps(example["before_record"])))
    wire = dict(schema_version=1, ruleset_fingerprint=compiled.ruleset_fingerprint,
                resigned_by=None, actions=[example["action"]])
    action = deserialize_game_record(json.dumps(wire)).actions[0]
    parent = session.state.position
    session.submit(action)
    stats = Counter()
    witness.check_delta(parent, session.state.position, action, compiled,
                        types, forward, reverse, stats)
    assert stats["delta_undo_transitions"] == 1
    assert stats["rollback_prefixes"] == (3 if kind == "capture" else 2)
    assert stats[kind + "_deltas"] == 1


@pytest.mark.parametrize("mutation", ["fingerprint", "aux", "hand", "promotion",
                                      "type_change", "boolean_owner", "anchor_missing", "board_tail"])
def test_unsupported_state_rejected_before_projection(data, mutation):
    _, compiled, position, types, _, _ = data
    if mutation == "fingerprint":
        bad = replace(position, ruleset_fingerprint="foreign")
    elif mutation == "aux":
        bad = replace(position, aux_state=(((99, -1), 1),))
    elif mutation == "hand":
        bad = replace(position, hands=(Hands((("A", 1),)), Hands.empty()))
    elif mutation == "board_tail":
        bad = replace(position, board=(*position.board, None))
    else:
        board = list(position.board)
        if mutation == "promotion":
            board[0] = replace(board[0], promoted=True)
        elif mutation == "type_change":
            board[0] = replace(board[0], current_type_id="A")
        elif mutation == "boolean_owner":
            board[0] = replace(board[0], owner=False)
        else:
            board[0] = None
        bad = replace(position, board=tuple(board))
    with pytest.raises(AssertionError):
        witness.occupation(bad, compiled, types)


def test_stale_victim_source_cannot_pass_capture_delta(data):
    fixture, compiled, _, types, forward, reverse = data
    example = fixture["capture"]
    session = GameSession.replay(compiled, deserialize_game_record(json.dumps(example["before_record"])))
    wire = dict(schema_version=1, ruleset_fingerprint=compiled.ruleset_fingerprint,
                resigned_by=None, actions=[example["action"]])
    action = deserialize_game_record(json.dumps(wire)).actions[0]
    parent = session.state.position
    session.submit(action)
    board = list(session.state.position.board)
    # Simulate a transform retaining the captured actor at an unrelated cell.
    target = action.to_square.rank * compiled.board_size + action.to_square.file
    empty = next(i for i, piece in enumerate(board) if piece is None and
                 i != action.from_square.rank * compiled.board_size + action.from_square.file)
    board[empty] = parent.board[target]
    bad_child = replace(session.state.position, board=tuple(board))
    with pytest.raises(AssertionError):
        witness.check_delta(parent, bad_child, action, compiled, types, forward, reverse, Counter())


def test_count_information_does_not_preserve_source_names(data):
    fixture, compiled, _, types, forward, reverse = data
    example = fixture["counts_cancel"]
    session = GameSession.replay(compiled, deserialize_game_record(json.dumps(example["before_record"])))
    wire = dict(schema_version=1, ruleset_fingerprint=compiled.ruleset_fingerprint,
                resigned_by=None, actions=[example["action"]])
    action = deserialize_game_record(json.dumps(wire)).actions[0]
    parent = session.state.position
    session.submit(action)
    result = census.obligation(parent, session.state.position, action, compiled, types, forward, reverse)
    assert result["source_set_rows_changed"] == 9
    assert result["count_rows_changed"] == 7
    assert result["attack_union_bits_changed"] == 6
    assert result["sequential_incidence_edits"] == 11


@pytest.mark.parametrize("kind", ["quiet", "capture"])
def test_count_delta_is_complete_for_existing_literal_transition(data, kind):
    fixture, compiled, _, types, forward, reverse = data
    example = fixture[kind]
    session = GameSession.replay(compiled, deserialize_game_record(json.dumps(example["before_record"])))
    wire = dict(schema_version=1, ruleset_fingerprint=compiled.ruleset_fingerprint,
                resigned_by=None, actions=[example["action"]])
    action = deserialize_game_record(json.dumps(wire)).actions[0]
    parent = session.state.position
    session.submit(action)
    result = census.obligation(parent, session.state.position, action, compiled, types, forward, reverse)
    assert result["captured"] == (kind == "capture")
    assert result["source_contribution_edits"] == (3 if kind == "capture" else 2)
    assert result["count_rows_changed"] == result["net_nonzero_count_rows"]
    assert result["attack_union_bits_changed"] <= result["count_rows_changed"]


def test_equal_occupancy_is_not_exact_runtime_position_identity(data):
    _, compiled, position, types, _, _ = data
    # Existing Core square positions use None/None carrier dimensions. An
    # explicit equal square shape has equal physical geometry/external key,
    # but the current exact runtime collision guard retains Position fields.
    explicit = replace(position, board_width=compiled.board_size,
                       board_height=compiled.board_size)
    assert witness.occupation(position, compiled, types) == witness.occupation(explicit, compiled, types)
    assert position.side_to_move == explicit.side_to_move
    assert position_identity_key(position, compiled) == position_identity_key(explicit, compiled)
    assert RuntimePositionIdentity(position) != RuntimePositionIdentity(explicit)
