from dataclasses import replace

import pytest

from ai_fixtures import build_4x4_rooks, rook as rook_type
from conftest import king_type
from rule_semantics_ir_fixtures import cannon_ruleset, castling_ruleset

from generic_chess.core.actions import BoardMove
from generic_chess.core.capture_sources import (
    probe_immediate_recaptures,
    query_capture_sources,
    query_counterfactual_legal_capture_sources,
)
from generic_chess.core.capture_pressure_trace import (
    trace_capture_pressure,
    trace_next_turn_legal_captures,
)
from generic_chess.core.coordinates import Square, square_to_index
from generic_chess.core.history_provenance import reconstruct_history_provenance
from generic_chess.core.movegen import legal_actions, legal_actions_from_position
from generic_chess.core.pieces import Piece
from generic_chess.core.semantic_executor import SemanticEngine, semantic_public_actions
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import (
    compile_ruleset_for_execution,
    compile_semantic_ruleset,
)
from generic_chess.rules.schema import RuleActionEffect, RuleSet, RuleSquareRef
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.xiangqi_diagnostic import build_xiangqi_diagnostic_ruleset


def _position(compiled, pieces, side=0):
    position = initial_state(compiled).position
    board = [None] * len(position.board)
    shape = position.board_shape
    for square, piece in pieces:
        index = square_to_index(square, shape)
        assert board[index] is None
        board[index] = piece
    return replace(position, board=tuple(board), side_to_move=side)


@pytest.fixture(scope="module")
def xiangqi():
    compiled = compile_ruleset_for_execution(build_xiangqi_diagnostic_ruleset())
    return compiled, SemanticEngine(compiled)


def _xiangqi_cannon_position(compiled, screens):
    pieces = [
        (Square(4, 0), Piece(0, "G", "G")),
        (Square(4, 9), Piece(1, "G", "G")),
        (Square(0, 4), Piece(0, "C", "C")),
        (Square(4, 4), Piece(1, "S", "S")),
    ]
    pieces.extend((Square(file, 4), Piece(1, "S", "S")) for file in screens)
    return _position(compiled, pieces)


def test_xiangqi_cannon_capture_query_respects_zero_one_two_screens(xiangqi):
    compiled, engine = xiangqi
    target = Square(4, 4)
    source = Square(0, 4)
    cases = (((), False), ((2,), True), ((2, 3), False))
    for screens, expected in cases:
        position = _xiangqi_cannon_position(compiled, screens)
        result = query_capture_sources(position, target, 0, compiled)
        target_index = square_to_index(target, position.board_shape)
        assert (source in result.pseudo_attack_sources) is expected
        assert (source in result.pseudo_capture_sources) is expected
        assert engine.is_square_attacked(position, target_index, 0) is expected
        assert (source in result.legal_capture_sources) is expected

        off_turn = query_capture_sources(
            replace(position, side_to_move=1), target, 0, compiled
        )
        assert off_turn.pseudo_capture_sources == result.pseudo_capture_sources
        assert off_turn.legal_capture_sources is None


def test_xiangqi_horse_source_query_respects_blocked_leg(xiangqi):
    compiled, engine = xiangqi
    source = Square(1, 2)
    target = Square(3, 3)
    kings_and_horse = [
        (Square(4, 0), Piece(0, "G", "G")),
        (Square(4, 9), Piece(1, "G", "G")),
        (Square(4, 5), Piece(1, "S", "S")),  # keep the Generals from facing
        (source, Piece(0, "H", "H")),
        (target, Piece(1, "S", "S")),
    ]
    for blocked, expected in ((False, True), (True, False)):
        pieces = list(kings_and_horse)
        if blocked:
            pieces.append((Square(2, 2), Piece(1, "S", "S")))
        position = _position(compiled, pieces)
        result = query_capture_sources(position, target, 0, compiled)
        target_index = square_to_index(target, position.board_shape)
        assert (source in result.pseudo_attack_sources) is expected
        assert (source in result.pseudo_capture_sources) is expected
        assert engine.is_square_attacked(position, target_index, 0) is expected
        assert (source in result.legal_capture_sources) is expected
        off_turn = query_capture_sources(
            replace(position, side_to_move=1), target, 0, compiled
        )
        assert off_turn.pseudo_capture_sources == result.pseudo_capture_sources
        assert off_turn.legal_capture_sources is None


def test_western_chess_distinguishes_pinned_pseudoattacker_from_legal_capture():
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    engine = SemanticEngine(compiled)
    source = Square(4, 1)  # white rook, pinned on the king's file
    target = Square(6, 1)  # two files away; not also attacked by the white King
    position = _position(
        compiled,
        [
            (Square(4, 0), Piece(0, "K", "K")),
            (Square(7, 7), Piece(1, "K", "K")),
            (source, Piece(0, "R", "R")),
            (Square(4, 7), Piece(1, "R", "R")),
            (target, Piece(1, "P", "P")),
        ],
    )

    result = query_capture_sources(position, target, 0, compiled)
    target_index = square_to_index(target, position.board_shape)
    assert result.pseudo_attack_sources == (source,)
    assert result.pseudo_capture_sources == (source,)
    assert result.legal_capture_sources == ()
    assert engine.is_square_attacked(position, target_index, 0) is True

    black_source = Square(4, 6)
    black_target = Square(6, 6)
    black_pinned = _position(
        compiled,
        [
            (Square(0, 0), Piece(0, "K", "K")),
            (Square(4, 7), Piece(1, "K", "K")),
            (Square(4, 0), Piece(0, "R", "R")),
            (black_source, Piece(1, "R", "R")),
            (black_target, Piece(0, "P", "P")),
        ],
        side=1,
    )
    black_result = query_capture_sources(black_pinned, black_target, 1, compiled)
    assert black_result.pseudo_capture_sources == (black_source,)
    assert black_result.legal_capture_sources == ()
    assert engine.is_square_attacked(
        black_pinned, square_to_index(black_target, black_pinned.board_shape), 1
    ) is True


def test_legacy_capture_source_uses_existing_geometry_and_legal_move_authority():
    compiled = build_4x4_rooks()
    source = Square(1, 1)
    target = Square(1, 2)
    position = _position(
        compiled,
        [
            (Square(0, 0), Piece(0, "K", "K")),
            (Square(3, 3), Piece(1, "K", "K")),
            (source, Piece(0, "R", "R")),
            (target, Piece(1, "R", "R")),
        ],
    )
    result = query_capture_sources(position, target, 0, compiled)
    assert result.pseudo_attack_sources == (source,)
    assert result.pseudo_capture_sources == (source,)
    assert result.legal_capture_sources == (source,)

    not_moving = replace(position, side_to_move=1)
    hypothetical = query_capture_sources(not_moving, target, 0, compiled)
    assert hypothetical.pseudo_attack_sources == (source,)
    assert hypothetical.pseudo_capture_sources == (source,)
    assert hypothetical.legal_capture_sources is None


def test_counterfactual_capture_probe_handles_pinned_and_free_rooks_for_both_owners():
    compiled = build_4x4_rooks()
    cases = (
        (
            0,
            Square(1, 1),
            Square(3, 1),
            [
                (Square(1, 0), Piece(0, "K", "K")),
                (Square(1, 1), Piece(0, "R", "R")),
                (Square(1, 3), Piece(1, "R", "R")),  # pinner
                (Square(3, 1), Piece(1, "R", "R")),  # target
                (Square(3, 3), Piece(1, "K", "K")),
            ],
            Square(1, 3),
        ),
        (
            1,
            Square(1, 2),
            Square(3, 2),
            [
                (Square(1, 0), Piece(0, "R", "R")),  # pinner
                (Square(3, 0), Piece(0, "K", "K")),
                (Square(3, 2), Piece(0, "R", "R")),  # target
                (Square(1, 2), Piece(1, "R", "R")),
                (Square(1, 3), Piece(1, "K", "K")),
            ],
            Square(1, 0),
        ),
    )

    for owner, source, target, pieces, pinner_square in cases:
        position = _position(compiled, pieces, side=1 - owner)
        assert query_counterfactual_legal_capture_sources(
            position, target, owner, compiled
        ) == ()

        unpinned = replace(
            position,
            board=tuple(
                None if square_to_index(pinner_square, position.board_shape) == i else piece
                for i, piece in enumerate(position.board)
            ),
        )
        assert query_counterfactual_legal_capture_sources(
            unpinned, target, owner, compiled
        ) == (source,)

    semantic = compile_ruleset_for_execution(cannon_ruleset())
    semantic_position = _position(
        semantic,
        [
            (Square(7, 7), Piece(0, "K", "K")),
            (Square(1, 0), Piece(1, "K", "K")),  # one cannon screen
            (Square(0, 0), Piece(0, "C", "C")),
            (Square(2, 0), Piece(1, "C", "C")),
        ],
        side=1,
    )
    assert query_counterfactual_legal_capture_sources(
        semantic_position, Square(2, 0), 0, semantic
    ) == (Square(0, 0),)


def test_counterfactual_capture_probe_fails_closed_for_turn_bound_semantics():
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    state = initial_state(compiled)
    target = Square(0, 6)  # Black pawn in the initial position.
    assert query_counterfactual_legal_capture_sources(
        state.position, target, 0, compiled
    ) is None

    triggered = compile_ruleset_for_execution(castling_ruleset())
    triggered_state = initial_state(triggered)
    assert query_counterfactual_legal_capture_sources(
        triggered_state.position, Square(0, 7), 0, triggered
    ) is None


def test_two_action_probe_distinguishes_legal_recapture_for_both_owners():
    compiled = build_4x4_rooks()
    cases = (
        (
            1,
            Square(0, 2),
            Square(3, 2),
            Square(3, 0),
            [
                (Square(0, 0), Piece(0, "K", "K")),
                (Square(3, 3), Piece(1, "K", "K")),
                (Square(0, 2), Piece(1, "R", "R")),
                (Square(3, 2), Piece(0, "R", "R")),
                (Square(3, 0), Piece(0, "R", "R")),
            ],
        ),
        (
            0,
            Square(0, 1),
            Square(3, 1),
            Square(3, 3),
            [
                (Square(0, 3), Piece(1, "K", "K")),
                (Square(3, 0), Piece(0, "K", "K")),
                (Square(0, 1), Piece(0, "R", "R")),
                (Square(3, 1), Piece(1, "R", "R")),
                (Square(3, 3), Piece(1, "R", "R")),
            ],
        ),
    )

    for actor, source, target, protector, pieces in cases:
        protected = _position(compiled, pieces, side=actor)
        unprotected = replace(
            protected,
            board=tuple(
                None if square_to_index(protector, protected.board_shape) == i else piece
                for i, piece in enumerate(protected.board)
            ),
        )
        action = next(
            candidate
            for candidate in legal_actions_from_position(protected, compiled)
            if isinstance(candidate, BoardMove)
            and candidate.from_square == source
            and candidate.to_square == target
        )
        assert action in legal_actions_from_position(unprotected, compiled)

        protected_result = probe_immediate_recaptures(protected, action, compiled)
        unprotected_result = probe_immediate_recaptures(unprotected, action, compiled)
        assert protected_result.status == "verified", protected_result.reason
        assert unprotected_result.status == "verified", unprotected_result.reason
        assert protected_result.capture_source == source
        assert protected_result.capture_target == target
        assert protected_result.recapture_sources == (protector,)
        assert unprotected_result.recapture_sources == ()


def test_two_action_probe_keeps_pinned_pseudo_recapturer_out_of_legal_sources():
    rows = [[None] * 5 for _ in range(5)]
    rows[0][1] = Piece(0, "K", "K")
    rows[4][4] = Piece(1, "K", "K")
    mask = (True,) * 25
    compiled = compile_ruleset_for_execution(
        RuleSet(
            board_size=5,
            piece_types=(king_type(), rook_type()),
            initial_position=tuple(tuple(row) for row in rows),
            drop_allowed={"R": (mask, mask)},
            promotion_allowed={},
            promotion_forced={},
        )
    )
    source = Square(3, 3)
    target = Square(3, 1)
    protector = Square(1, 1)
    pinner = Square(1, 4)
    protected = _position(
        compiled,
        [
            (Square(1, 0), Piece(0, "K", "K")),
            (Square(4, 4), Piece(1, "K", "K")),
            (protector, Piece(0, "R", "R")),
            (pinner, Piece(1, "R", "R")),
            (source, Piece(1, "R", "R")),
            (target, Piece(0, "R", "R")),
        ],
        side=1,
    )
    action = next(
        candidate
        for candidate in legal_actions_from_position(protected, compiled)
        if isinstance(candidate, BoardMove)
        and candidate.from_square == source
        and candidate.to_square == target
    )
    fake_root = probe_immediate_recaptures(protected, action, compiled)
    assert fake_root.status == "verified", fake_root.reason
    assert fake_root.pseudo_recapture_sources == (protector,)
    assert fake_root.recapture_sources == ()

    unpinned = replace(
        protected,
        board=tuple(
            None if square_to_index(pinner, protected.board_shape) == i else piece
            for i, piece in enumerate(protected.board)
        ),
    )
    real_root = probe_immediate_recaptures(unpinned, action, compiled)
    assert real_root.status == "verified", real_root.reason
    assert real_root.pseudo_recapture_sources == (protector,)
    assert real_root.recapture_sources == (protector,)


def test_two_action_probe_uses_semantic_capture_and_transition_authorities():
    compiled = compile_ruleset_for_execution(cannon_ruleset())
    engine = SemanticEngine(compiled)
    position = _position(
        compiled,
        [
            (Square(7, 7), Piece(0, "K", "K")),
            (Square(1, 0), Piece(1, "K", "K")),  # one capture screen
            (Square(0, 0), Piece(0, "C", "C")),
            (Square(2, 0), Piece(1, "C", "C")),
        ],
        side=0,
    )
    action = next(
        candidate
        for candidate in semantic_public_actions(engine, position)
        if getattr(candidate, "from_square", None) == Square(0, 0)
        and getattr(candidate, "to_square", None) == Square(2, 0)
    )
    result = probe_immediate_recaptures(position, action, compiled)
    assert result.status == "verified", result.reason
    assert result.recapture_sources == (Square(1, 0),)


def test_two_action_probe_applies_supported_aux_transition_triggers():
    compiled = compile_ruleset_for_execution(castling_ruleset())
    engine = SemanticEngine(compiled)
    position = _position(
        compiled,
        [
            (Square(4, 0), Piece(0, "K", "K")),
            (Square(7, 0), Piece(0, "R", "R")),
            (Square(3, 7), Piece(1, "K", "K")),
            (Square(0, 7), Piece(1, "R", "R")),
            (Square(6, 0), Piece(1, "R", "R")),
        ],
        side=0,
    )
    action = next(
        candidate
        for candidate in semantic_public_actions(engine, position)
        if getattr(candidate, "from_square", None) == Square(7, 0)
        and getattr(candidate, "to_square", None) == Square(6, 0)
    )
    result = probe_immediate_recaptures(position, action, compiled)
    assert result.status == "verified", result.reason
    assert result.pseudo_recapture_sources == ()
    assert result.recapture_sources == ()


def test_two_action_probe_returns_unknown_for_extra_board_effects():
    ruleset = cannon_ruleset()
    actions = tuple(
        replace(
            action,
            effects=action.effects
            + (
                RuleActionEffect(
                    "move",
                    from_ref=RuleSquareRef(
                        kind="fixed", square=(7, 0), owner_relative=False
                    ),
                    to_ref=RuleSquareRef(
                        kind="fixed", square=(6, 0), owner_relative=False
                    ),
                    piece_owner="self",
                ),
            ),
        )
        if action.name == "cannon_capture"
        else action
        for action in ruleset.semantic_actions
    )
    compiled = compile_semantic_ruleset(
        replace(ruleset, semantic_actions=actions)
    )
    engine = SemanticEngine(compiled)
    position = _position(
        compiled,
        [
            (Square(7, 7), Piece(0, "K", "K")),
            (Square(1, 0), Piece(1, "K", "K")),
            (Square(0, 0), Piece(0, "C", "C")),
            (Square(2, 0), Piece(1, "C", "C")),
            (Square(7, 0), Piece(0, "C", "C")),
        ],
        side=0,
    )
    action = next(
        candidate
        for candidate in semantic_public_actions(engine, position)
        if getattr(candidate, "from_square", None) == Square(0, 0)
        and getattr(candidate, "to_square", None) == Square(2, 0)
    )
    result = probe_immediate_recaptures(position, action, compiled)
    assert result.status == "unknown"
    assert result.recapture_sources == ()
    assert "extra board effects" in result.reason


def test_capture_query_requires_an_occupied_enemy_target(xiangqi):
    compiled, _engine = xiangqi
    position = _xiangqi_cannon_position(compiled, (2,))
    with pytest.raises(ValueError, match="opponent"):
        query_capture_sources(position, Square(0, 4), 0, compiled)
    with pytest.raises(ValueError, match="outside"):
        query_capture_sources(position, Square(9, 4), 0, compiled)


def test_enemy_target_action_without_target_removal_is_not_reported_as_capture():
    ruleset = cannon_ruleset()
    actions = tuple(
        replace(
            action,
            effects=(
                RuleActionEffect(
                    "move",
                    from_ref=RuleSquareRef(kind="source"),
                    to_ref=RuleSquareRef(kind="fixed", square=(0, 1)),
                ),
            ),
        )
        if action.name == "cannon_capture"
        else action
        for action in ruleset.semantic_actions
    )
    compiled = compile_semantic_ruleset(replace(ruleset, semantic_actions=actions))
    engine = SemanticEngine(compiled)
    source = Square(0, 0)
    target = Square(2, 0)
    position = _position(
        compiled,
        [
            (Square(7, 7), Piece(0, "K", "K")),
            (Square(1, 0), Piece(1, "K", "K")),  # one screen
            (target, Piece(1, "C", "C")),
            (source, Piece(0, "C", "C")),
        ],
    )

    result = query_capture_sources(position, target, 0, compiled)
    assert result.pseudo_attack_sources == (source,)
    assert result.pseudo_capture_sources == ()
    assert result.legal_capture_sources == ()

    source_index = square_to_index(source, position.board_shape)
    target_index = square_to_index(target, position.board_shape)
    action = next(
        candidate
        for candidate in engine.iter_legal_actions(position)
        if candidate.source == source_index and candidate.target == target_index
    )
    after = engine.apply(position, action)
    assert after.board[target_index] == Piece(1, "C", "C")
    assert after.board[square_to_index(Square(0, 1), position.board_shape)] == Piece(
        0, "C", "C"
    )


def test_capture_sources_join_verified_history_tokens_across_reoccupancy():
    rows = [[None] * 5 for _ in range(5)]
    rows[0][4] = Piece(0, "K", "K")
    rows[4][0] = Piece(1, "K", "K")
    rows[2][0] = Piece(1, "R", "R")  # persistent attacker
    rows[2][3] = Piece(0, "R", "R")  # A initially occupies target
    rows[2][4] = Piece(0, "R", "R")  # B later reoccupies target
    mask = (True,) * 25
    compiled = compile_ruleset_for_execution(
        RuleSet(
            board_size=5,
            piece_types=(king_type(), rook_type()),
            initial_position=tuple(tuple(row) for row in rows),
            drop_allowed={"R": (mask, mask)},
            promotion_allowed={},
            promotion_forced={},
        )
    )
    state = initial_state(compiled)
    target = Square(3, 2)
    source = Square(0, 2)
    target_index = square_to_index(target, state.position.board_shape)
    source_index = square_to_index(source, state.position.board_shape)

    def move(state, start, end):
        action = next(
            action
            for action in legal_actions(state, compiled)
            if isinstance(action, BoardMove)
            and action.from_square == start
            and action.to_square == end
        )
        return apply_action(state, action, compiled)

    state = move(state, Square(4, 0), Square(4, 1))
    state = move(state, Square(0, 4), Square(1, 4))
    state = move(state, Square(3, 2), Square(3, 1))
    state = move(state, Square(1, 4), Square(2, 4))
    state = move(state, Square(4, 2), target)
    state = move(state, Square(2, 4), Square(2, 3))
    provenance = reconstruct_history_provenance(state, compiled)
    assert provenance.status == "verified"
    assert len(provenance.frames) == 7

    def joined_edges(history):
        if history.status != "verified":
            return ()
        joined = []
        for ply in (0, 6):
            frame = history.frames[ply]
            evidence = query_capture_sources(frame.position, target, 1, compiled)
            if source not in evidence.pseudo_capture_sources:
                continue
            if ply == 0:
                assert evidence.legal_capture_sources is None
            else:
                legal_next = query_counterfactual_legal_capture_sources(
                    frame.position, target, 1, compiled
                )
                assert legal_next is not None and source in legal_next
            attacker_id = frame.identities[source_index]
            target_id = frame.identities[target_index]
            assert attacker_id is not None and target_id is not None
            joined.append((attacker_id, target_id))
        return tuple(joined)

    edges = joined_edges(provenance)
    assert len(edges) == 2

    assert edges[0][0] == edges[1][0]  # attacker continuity
    assert edges[0][1] != edges[1][1]  # same square/type, different target instance
    assert provenance.frames[0].position.board[target_index].base_type_id == "R"
    assert provenance.frames[6].position.board[target_index].base_type_id == "R"

    trace = trace_capture_pressure(state, compiled)
    assert trace.status == "verified"
    threat_to_a = [
        fact for fact in trace.facts
        if fact.source_token == edges[0][0] and fact.target_token == edges[0][1]
    ]
    by_ply = {fact.ply: fact for fact in threat_to_a}
    assert by_ply[1].pseudo_capture_before and by_ply[1].pseudo_capture_after
    assert by_ply[2].pseudo_capture_before and by_ply[2].pseudo_capture_after
    assert by_ply[3].pseudo_capture_before and not by_ply[3].pseudo_capture_after
    assert by_ply[3].target_transition == "moved"
    assert by_ply[3].action_source_token == edges[0][1]

    target_b = provenance.frames[6].identities[target_index]
    assert target_b is not None and target_b != edges[0][1]
    threat_to_b = next(
        fact for fact in trace.facts
        if fact.ply == 5 and fact.source_token == edges[0][0]
        and fact.target_token == target_b
    )
    assert threat_to_b.pseudo_capture_before and threat_to_b.pseudo_capture_after
    assert threat_to_b.target_transition == "moved"

    next_turn = trace_next_turn_legal_captures(state, compiled)
    assert next_turn.status == "verified"
    legal_a = next(
        fact for fact in next_turn.facts
        if fact.frame_ply == 2 and fact.source_token == edges[0][0]
        and fact.target_token == edges[0][1]
    )
    legal_b = next(
        fact for fact in next_turn.facts
        if fact.frame_ply == 6 and fact.source_token == edges[0][0]
        and fact.target_token == target_b
    )
    assert legal_a.target == legal_b.target == target
    assert legal_a.source == legal_b.source == source
    assert legal_a.actor == legal_b.actor == 1
    assert legal_a.side_to_move == legal_b.side_to_move == 0
    assert legal_a.target_token != legal_b.target_token

    incomplete = replace(state, history=state.history[1:])
    unknown = reconstruct_history_provenance(incomplete, compiled)
    assert unknown.status == "unknown"
    assert unknown.frames == ()
    assert joined_edges(unknown) == ()
    unknown_trace = trace_capture_pressure(incomplete, compiled)
    assert unknown_trace.status == "unknown"
    assert unknown_trace.facts == ()

    imported = replace(state, history=())
    imported_provenance = reconstruct_history_provenance(imported, compiled)
    assert imported_provenance.status == "unknown"
    assert imported_provenance.frames == ()
    assert joined_edges(imported_provenance) == ()
    imported_trace = trace_capture_pressure(imported, compiled)
    assert imported_trace.status == "unknown"
    assert imported_trace.facts == ()


def test_next_turn_legal_capture_trace_omits_pinned_pseudo_pressure():
    mask = (True,) * 25
    source = Square(1, 1)
    target = Square(3, 1)
    current_side_target = Square(0, 1)
    def run(pinned):
        rows = [[None] * 5 for _ in range(5)]
        rows[0][1] = Piece(0, "K", "K")
        rows[0][0] = Piece(0, "R", "R")  # unrelated mover
        rows[1][1] = Piece(0, "R", "R")  # candidate recapturer
        rows[1][3] = Piece(1, "R", "R")  # target
        rows[4][4] = Piece(1, "K", "K")
        if pinned:
            rows[4][1] = Piece(1, "R", "R")  # pins the candidate
        compiled = compile_ruleset_for_execution(
            RuleSet(
                board_size=5,
                piece_types=(king_type(), rook_type()),
                initial_position=tuple(tuple(row) for row in rows),
                drop_allowed={"R": (mask, mask)},
                promotion_allowed={},
                promotion_forced={},
            )
        )
        state = initial_state(compiled)
        move = next(
            action for action in legal_actions(state, compiled)
            if isinstance(action, BoardMove)
            and action.from_square == Square(0, 0)
            and action.to_square == current_side_target
        )
        state = apply_action(state, move, compiled)
        provenance = reconstruct_history_provenance(state, compiled)
        assert provenance.status == "verified"
        raw = query_capture_sources(state.position, target, 0, compiled)
        assert raw.pseudo_capture_sources == (source,)
        assert raw.legal_capture_sources is None  # the opponent is to move
        next_actor_sources = query_counterfactual_legal_capture_sources(
            state.position, target, 0, compiled
        )
        trace = trace_next_turn_legal_captures(state, compiled)
        assert trace.status == "verified"
        frame = provenance.frames[1]
        source_token = frame.identities[
            square_to_index(source, frame.position.board_shape)
        ]
        target_token = frame.identities[
            square_to_index(target, frame.position.board_shape)
        ]
        contains_candidate = any(
            fact.frame_ply == 1
            and fact.actor == 0
            and fact.side_to_move == 1
            and fact.source_token == source_token
            and fact.target_token == target_token
            for fact in trace.facts
        )
        assert query_counterfactual_legal_capture_sources(
            state.position, current_side_target, 1, compiled
        ) == ()
        truncated = replace(state, history=state.history[1:])
        unknown = trace_next_turn_legal_captures(truncated, compiled)
        assert unknown.status == "unknown"
        assert unknown.facts == ()
        imported = replace(state, history=())
        unknown_import = trace_next_turn_legal_captures(imported, compiled)
        assert unknown_import.status == "unknown"
        assert unknown_import.facts == ()
        return next_actor_sources, contains_candidate

    pinned_sources, pinned_fact = run(pinned=True)
    unpinned_sources, unpinned_fact = run(pinned=False)
    assert pinned_sources == ()
    assert not pinned_fact
    assert unpinned_sources == (source,)
    assert unpinned_fact


def test_next_turn_legal_capture_trace_fails_closed_for_expiring_aux_state():
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    state = initial_state(compiled)
    move = next(
        action for action in legal_actions(state, compiled)
        if getattr(action, "from_square", None) == Square(4, 1)
        and getattr(action, "to_square", None) == Square(4, 3)
    )
    state = apply_action(state, move, compiled)
    trace = trace_next_turn_legal_captures(state, compiled)
    assert trace.status == "unknown"
    assert trace.facts == ()


def test_capture_pressure_trace_records_capture_of_target_token():
    rows = [[None] * 5 for _ in range(5)]
    rows[0][4] = Piece(0, "K", "K")
    rows[4][0] = Piece(1, "K", "K")
    rows[2][0] = Piece(1, "R", "R")
    rows[2][3] = Piece(0, "R", "R")
    rows[2][4] = Piece(0, "R", "R")
    mask = (True,) * 25
    compiled = compile_ruleset_for_execution(
        RuleSet(
            board_size=5,
            piece_types=(king_type(), rook_type()),
            initial_position=tuple(tuple(row) for row in rows),
            drop_allowed={"R": (mask, mask)},
            promotion_allowed={},
            promotion_forced={},
        )
    )
    state = initial_state(compiled)

    def move(state, start, end):
        action = next(
            action for action in legal_actions(state, compiled)
            if isinstance(action, BoardMove)
            and action.from_square == start and action.to_square == end
        )
        return apply_action(state, action, compiled)

    state = move(state, Square(4, 0), Square(4, 1))
    state = move(state, Square(0, 2), Square(3, 2))
    trace = trace_capture_pressure(state, compiled)
    assert trace.status == "verified"
    captured = next(
        fact for fact in trace.facts
        if fact.ply == 2 and fact.before_target == Square(3, 2)
        and fact.target_transition == "captured"
    )
    assert captured.pseudo_capture_before
    assert not captured.pseudo_capture_after
    assert captured.action_target_token == captured.target_token
