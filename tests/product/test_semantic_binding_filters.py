"""Source/target queries retain the complete semantic legality contract."""
import pytest
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.session.session import GameSession
from rule_semantics_ir_fixtures import (
    cannon_ruleset, castling_ruleset, en_passant_ruleset, nifu_ruleset,
    uchifuzume_ruleset, weird_rulesets,
)


@pytest.mark.parametrize("definition", [
    cannon_ruleset(), castling_ruleset(), en_passant_ruleset(), nifu_ruleset(),
    uchifuzume_ruleset(), *weird_rulesets(),
    build_western_chess_ruleset(), build_standard_shogi_ruleset(),
], ids=["cannon", "castling", "en-passant", "nifu", "uchifuzume",
        "weird-ray", "zone-drop", "temporary-right", "compound", "postcondition",
        "western", "shogi"])
def test_filtered_bindings_equal_full_legal_subsets_through_play(definition):
    compiled = compile_ruleset_for_execution(definition)
    session = GameSession(compiled)
    engine = semantic_engine_for(compiled)
    for _ in range(4):
        position = session.state.position
        full = list(engine.iter_legal_action_bindings(position))
        sources = {i for i, piece in enumerate(position.board) if piece is not None}
        sources.add(next((i for i, piece in enumerate(position.board) if piece is None), 0))
        for source in sources:
            filtered = list(engine.iter_legal_action_bindings(position, source=source))
            assert filtered == [(a, b) for a, b in full if a.source == source]
        for target in range(len(position.board)):
            assert list(engine.iter_legal_action_bindings(position, target=target)) == [
                (a, b) for a, b in full if a.target == target]
        for action, _ in full[:8]:
            if action.source is not None:
                assert list(engine.iter_legal_action_bindings(position,
                    source=action.source, target=action.target)) == [
                    (a, b) for a, b in full
                    if a.source == action.source and a.target == action.target]
        if session.state.terminal_status.is_terminal:
            break
        actions = sorted(session.legal_actions(), key=repr)
        if not actions:
            break
        session.submit(actions[0])


def test_filtered_query_observes_cancellation():
    compiled = compile_ruleset_for_execution(cannon_ruleset())
    position = GameSession(compiled).state.position
    engine = semantic_engine_for(compiled)
    def cancel():
        raise InterruptedError("stop filtered query")
    with pytest.raises(InterruptedError, match="stop filtered query"):
        list(engine.iter_legal_action_bindings(position, cancel, source=0, target=1))


@pytest.mark.parametrize("filters", [{"source": -1}, {"source": 64},
    {"target": -1}, {"target": 64}, {"source": True}, {"target": 0.5}])
def test_invalid_binding_filters_do_not_wrap_coordinates(filters):
    compiled = compile_ruleset_for_execution(cannon_ruleset())
    position = GameSession(compiled).state.position
    with pytest.raises(ValueError, match="filter square"):
        list(semantic_engine_for(compiled).iter_legal_action_bindings(position, **filters))



def test_target_filter_does_not_skip_pawn_drop_mate_postcondition():
    from dataclasses import replace
    from generic_chess.core.pieces import Piece
    from generic_chess.core.position import Hands

    board = [[None] * 9 for _ in range(9)]
    # The gold covers h9/h8; the friendly king protects the i8 drop.
    for owner, tid, file, rank in ((0, "K", 8, 6), (1, "K", 8, 8), (0, "G", 6, 7)):
        board[rank][file] = Piece(owner, tid, tid)
    definition = replace(build_standard_shogi_ruleset(), initial_position=tuple(map(tuple, board)))
    compiled = compile_ruleset_for_execution(definition)
    engine = semantic_engine_for(compiled)
    position = replace(GameSession(compiled).state.position,
                       hands=(Hands((("P", 1),)), Hands.empty()))
    target = 8 + 9 * 7
    candidates = [(pattern, action, binding) for pattern in engine._patterns
                  for action, binding in engine._iter_candidates(pattern, position)
                  if action.source is None and action.target == target]
    assert len(candidates) == 1
    pattern, action, binding = candidates[0]
    assert engine._trial_child_if_s3_legal(pattern, position, action, binding) is not None
    assert not list(engine.iter_legal_action_bindings(position, target=target))
    assert not [(a, b) for a, b in engine.iter_legal_action_bindings(position)
                if a.target == target]
