"""Executable event coverage, rather than compile-only capability coverage."""
from dataclasses import replace

from generic_chess.core.pieces import Piece
from generic_chess.core.transition import apply_action, legal_successors
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.cancellation import CancellationToken
from generic_chess.ai.limits import SearchLimits
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset, serialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record, serialize_game_record
from rule_semantics_ir_fixtures import castling_ruleset, en_passant_ruleset, weird_rulesets


def test_promotion_expiry_and_drop_capacity_through_real_capture_history():
    fixtures = weird_rulesets()
    guard = fixtures[1].semantic_actions[0]
    promotion = fixtures[2].semantic_actions[0]
    board = [[None] * 8 for _ in range(8)]
    for owner, tid, file, rank in (
        (0, "K", 4, 0), (1, "K", 7, 7),
        (0, "R", 0, 0), (0, "R", 0, 1), (0, "R", 0, 2),
        (0, "R", 1, 1), (1, "R", 1, 3), (1, "R", 1, 4),
    ):
        board[rank][file] = Piece(owner, tid, tid)
    definition = replace(
        fixtures[2], initial_position=tuple(map(tuple, board)),
        semantic_actions=(guard, promotion),
        drop_allowed={"R": ((True,) * 64, (True,) * 64),
                      "TP": ((False,) * 64, (False,) * 64)},
    )
    compiled = compile_ruleset_for_execution(definition)
    session = GameSession(compiled)
    route = (
        ((1, 1), (1, 3), False), ((7, 7), (6, 7), False),
        ((1, 3), (1, 4), False), ((6, 7), (5, 7), False),
        ((0, 0), (1, 1), True), ((5, 7), (4, 7), False),
        (None, (0, 0), False), ((4, 7), (3, 7), False),
    )
    for ply in range(9):
        pairs = legal_successors(session.state, compiled)
        assert tuple(a for a, _ in pairs) == session.legal_actions()
        for action, child in pairs:
            assert child == apply_action(session.state, action, compiled)
        drops = [a for a, _ in pairs if hasattr(a, "base_type_id")]
        if ply in (2, 4, 8):
            assert session.state.position.hands[0].count("R") > 0
            assert not drops
        if ply == 4:
            promotion_action, = [action for action in session.legal_actions()
                                 if hasattr(action, "from_square")
                                 and (action.from_square.file, action.from_square.rank) == (0, 0)
                                 and (action.to_square.file, action.to_square.rank) == (1, 1)
                                 and action.pattern_id.startswith("sem_")]
            right_slot, = (slot.slot_id for slot in compiled.ir.aux_slots)

            class PromotionEffectProbe:
                def evaluate(self, state):
                    piece = state.position.board[9]
                    promoted = (
                        piece is not None and piece.owner == 0
                        and piece.base_type_id == "R"
                        and piece.current_type_id == "TP"
                        and piece.promoted
                        and dict(state.position.aux_state).get((right_slot, -1)) == 1
                    )
                    value = 10_000 if promoted else 0
                    return -value if state.position.side_to_move == 1 else value

            player = AlphaBetaPlayer(
                compiled,
                use_disk_cache=False,
                use_native_semantic_legality=True,
                use_tt=False,
                use_ordering=False,
                evaluator_override=PromotionEffectProbe(),
            )
            input_record = session.to_record()
            decision = player.choose_action(session, SearchLimits(
                max_depth=1,
                max_nodes=1_000,
                quiescence_max_depth=0,
                quiescence_hard_max_depth=0,
                quiescence_max_nodes=0,
            ))
            assert decision.completed_depth == 1
            assert decision.action == promotion_action
            assert decision.principal_variation == (promotion_action,)
            assert session.to_record() == input_record

            replay = GameSession(compiled)
            for record in session.history:
                replay.submit(record.action)
            for action in decision.principal_variation:
                assert action in replay.legal_actions()
                replay.submit(action)
            piece = replay.state.position.board[9]
            assert (piece.base_type_id, piece.current_type_id, piece.promoted) == (
                "R", "TP", True)
            assert dict(replay.state.position.aux_state)[(right_slot, -1)] == 1
        if ply == 5:
            promoted = session.state.position.board[9]
            assert (promoted.base_type_id, promoted.current_type_id, promoted.promoted) == (
                "R", "TP", True)
            assert dict(session.state.position.aux_state)[(0, -1)] == 1
        if ply == 6:
            assert dict(session.state.position.aux_state)[(0, -1)] == 0
            assert len(drops) == 58
            drop_to_a1, = [action for action in drops
                           if action.base_type_id == "R"
                           and (action.to_square.file, action.to_square.rank) == (0, 0)]
            hand_before = session.state.position.hands[0].count("R")

            class DropEffectProbe:
                def evaluate(self, state):
                    dropped = (
                        state.position.board[0] == Piece(0, "R", "R")
                        and state.position.hands[0].count("R") == hand_before - 1
                    )
                    value = 10_000 if dropped else 0
                    return -value if state.position.side_to_move == 1 else value

            player = AlphaBetaPlayer(
                compiled,
                use_disk_cache=False,
                use_native_semantic_legality=True,
                use_tt=False,
                use_ordering=False,
                evaluator_override=DropEffectProbe(),
            )
            input_record = session.to_record()
            decision = player.choose_action(session, SearchLimits(
                max_depth=1,
                max_nodes=1_000,
                quiescence_max_depth=0,
                quiescence_hard_max_depth=0,
                quiescence_max_nodes=0,
            ))
            assert decision.completed_depth == 1
            assert decision.action == drop_to_a1
            assert decision.principal_variation == (drop_to_a1,)
            assert session.to_record() == input_record

            replay = GameSession(compiled)
            for record in session.history:
                replay.submit(record.action)
            for action in decision.principal_variation:
                assert action in replay.legal_actions()
                replay.submit(action)
            assert replay.state.position.board[0] == Piece(0, "R", "R")
            assert replay.state.position.hands[0].count("R") == hand_before - 1
        if ply == 8:
            assert session.state.position.hands[0].count("R") == 1
            break
        source, target, semantic = route[ply]
        candidates = []
        for action, _ in pairs:
            if (action.to_square.file, action.to_square.rank) != target:
                continue
            if source is None:
                if hasattr(action, "base_type_id"):
                    candidates.append(action)
            elif (hasattr(action, "from_square")
                  and (action.from_square.file, action.from_square.rank) == source
                  and action.pattern_id.startswith("sem_") == semantic):
                candidates.append(action)
        action, = candidates
        session.submit(action)


def test_alphabeta_preserves_compound_action_identity_and_replayable_pv(monkeypatch):
    definition = weird_rulesets()[3]
    board = [[None] * 8 for _ in range(8)]
    for owner, type_id, file, rank in (
        (0, "K", 0, 0), (1, "K", 7, 7),
        (0, "R", 3, 3), (0, "R", 3, 4),
    ):
        board[rank][file] = Piece(owner, type_id, type_id)
    definition = replace(
        definition, initial_position=tuple(tuple(row) for row in board))
    serialized = serialize_ruleset(definition)
    definition = deserialize_ruleset(serialized)
    assert serialize_ruleset(definition) == serialized
    compiled = compile_ruleset_for_execution(definition)
    session = GameSession(compiled)

    # Establish a real, replayable history without changing the R compound
    # action's geometry: both moves use the public session boundary.
    for source, target in (((0, 0), (0, 1)), ((7, 7), (7, 6))):
        action, = [candidate for candidate in session.legal_actions()
                   if hasattr(candidate, "from_square")
                   and (candidate.from_square.file, candidate.from_square.rank) == source
                   and (candidate.to_square.file, candidate.to_square.rank) == target]
        session.submit(action)
    saved_history = session.to_record()
    session = GameSession.replay(
        compiled, deserialize_game_record(serialize_game_record(saved_history)))
    assert session.to_record() == saved_history
    compound, = [action for action in session.legal_actions()
                 if action.pattern_id == "sem_00_move_and_shift_adjacent_friendly"]

    class CompoundEffectProbe:
        def evaluate(self, state):
            # Controlled interface fixture: only the intended two-piece
            # transition receives a score. This makes no playing-strength claim.
            board = state.position.board
            shifted = all(
                piece is not None and piece.owner == 0 and piece.current_type_id == "R"
                for piece in (board[4 * 8 + 4], board[5 * 8 + 3])
            )
            value = 10_000 if shifted else 0
            return -value if state.position.side_to_move == 1 else value

    player = AlphaBetaPlayer(
        compiled,
        use_disk_cache=False,
        use_native_semantic_legality=True,
        use_tt=False,
        use_ordering=False,
        evaluator_override=CompoundEffectProbe(),
    )
    input_record = session.to_record()
    decision = player.choose_action(session, SearchLimits(
        max_depth=2,
        max_nodes=3_000,
        quiescence_max_depth=0,
        quiescence_hard_max_depth=0,
        quiescence_max_nodes=0,
    ))

    assert decision.completed_depth == 2
    assert decision.action == compound
    assert decision.principal_variation[0] == compound
    assert decision.native_legality_calls > 0
    assert decision.native_legality_fallbacks == 0
    assert decision.native_legality_operational_failures == 0
    assert session.to_record() == input_record

    replay = GameSession(compiled)
    for record in session.history:
        replay.submit(record.action)
    assert replay.to_record() == session.to_record()
    for action in decision.principal_variation:
        assert action in replay.legal_actions()
        replay.submit(action)

    assert replay.state.position.board[4 * 8 + 4] == Piece(0, "R", "R")
    assert replay.state.position.board[5 * 8 + 3] == Piece(0, "R", "R")

    # A node cap can interrupt before any full iteration or during a later
    # iteration. In both cases the separately returned action remains a legal
    # caller choice; the PV represents only a completed line, so it may be
    # empty at depth zero and otherwise starts with that action.
    for node_cap, minimum_depth in ((30, 0), (80, 1)):
        limited = player.choose_action(session, SearchLimits(
            max_depth=3,
            max_nodes=node_cap,
            quiescence_max_depth=0,
            quiescence_hard_max_depth=0,
            quiescence_max_nodes=0,
        ))
        assert limited.termination_reason == "node_limit"
        assert limited.completed_depth >= minimum_depth
        assert limited.completed_depth < 3
        assert limited.nodes <= node_cap
        assert limited.action in session.legal_actions()
        if limited.completed_depth == 0:
            assert limited.principal_variation == ()
        else:
            assert limited.principal_variation[0] == limited.action
            replay = GameSession.replay(compiled, session.to_record())
            for action in limited.principal_variation:
                assert action in replay.legal_actions()
                replay.submit(action)
        assert session.to_record() == input_record

    token = CancellationToken()
    completed_callbacks = []

    def cancel_after_first_iteration(depth, nodes, qnodes):
        completed_callbacks.append((depth, nodes, qnodes))
        if depth == 1:
            token.cancel()

    cancelled = player.choose_action(
        session,
        SearchLimits(
            max_depth=3,
            quiescence_max_depth=0,
            quiescence_hard_max_depth=0,
            quiescence_max_nodes=0,
        ),
        cancel_token=token,
        progress_callback=cancel_after_first_iteration,
    )
    assert completed_callbacks and completed_callbacks[0][0] == 1
    assert cancelled.termination_reason == "cancelled"
    assert cancelled.completed_depth == 1
    assert cancelled.action == compound
    assert cancelled.principal_variation[0] == cancelled.action
    replay = GameSession.replay(compiled, session.to_record())
    for action in cancelled.principal_variation:
        assert action in replay.legal_actions()
        replay.submit(action)
    assert session.to_record() == input_record

    clock = [0.0]
    deadline_callbacks = []
    monkeypatch.setattr(
        "generic_chess.ai.alphabeta.search.time.perf_counter",
        lambda: clock[0],
    )

    def expire_after_first_iteration(depth, nodes, qnodes):
        deadline_callbacks.append((depth, nodes, qnodes))
        if depth == 1:
            clock[0] = 2.0

    deadline = player.choose_action(
        session,
        SearchLimits(
            max_depth=3,
            max_time_seconds=1.0,
            quiescence_max_depth=0,
            quiescence_hard_max_depth=0,
            quiescence_max_nodes=0,
        ),
        progress_callback=expire_after_first_iteration,
    )
    assert deadline_callbacks and deadline_callbacks[0][0] == 1
    assert deadline.termination_reason == "time_limit"
    assert deadline.completed_depth == 1
    assert deadline.action == compound
    assert deadline.principal_variation[0] == deadline.action
    replay = GameSession.replay(compiled, session.to_record())
    for action in deadline.principal_variation:
        assert action in replay.legal_actions()
        replay.submit(action)
    assert session.to_record() == input_record


def test_alphabeta_preserves_auxiliary_state_action_and_pv():
    compiled = compile_ruleset_for_execution(castling_ruleset())
    session = GameSession(compiled)
    castle, = [action for action in session.legal_actions()
               if action.pattern_id == "sem_00_king_side_shift"]

    right_slot, = (slot.slot_id for slot in compiled.ir.aux_slots)

    class CastleEffectProbe:
        def evaluate(self, state):
            board = state.position.board
            castled = (
                board[6] == Piece(0, "K", "K")
                and board[5] == Piece(0, "R", "R")
                and dict(state.position.aux_state).get((right_slot, 0)) == 0
            )
            value = 10_000 if castled else 0
            return -value if state.position.side_to_move == 1 else value

    player = AlphaBetaPlayer(
        compiled,
        use_disk_cache=False,
        use_native_semantic_legality=True,
        use_tt=False,
        use_ordering=False,
        evaluator_override=CastleEffectProbe(),
    )
    input_record = session.to_record()
    decision = player.choose_action(session, SearchLimits(
        max_depth=1,
        max_nodes=1_000,
        quiescence_max_depth=0,
        quiescence_hard_max_depth=0,
        quiescence_max_nodes=0,
    ))

    assert decision.completed_depth == 1
    assert decision.action == castle
    assert decision.principal_variation == (castle,)
    assert decision.native_legality_calls > 0
    assert decision.native_legality_fallbacks == 0
    assert decision.native_legality_operational_failures == 0
    assert session.to_record() == input_record

    session.submit(decision.principal_variation[0])
    assert session.state.position.board[6] == Piece(0, "K", "K")
    assert session.state.position.board[5] == Piece(0, "R", "R")
    assert dict(session.state.position.aux_state)[(right_slot, 0)] == 0


def test_alphabeta_preserves_history_dependent_off_target_capture_action():
    board = [[None] * 8 for _ in range(8)]
    for owner, type_id, file, rank in (
        (0, "K", 0, 0), (1, "K", 7, 7),
        (0, "P", 2, 1), (1, "P", 1, 3),
    ):
        board[rank][file] = Piece(owner, type_id, type_id)
    compiled = compile_ruleset_for_execution(replace(
        en_passant_ruleset(), initial_position=tuple(tuple(row) for row in board)))
    session = GameSession(compiled)
    double_step, = [action for action in session.legal_actions()
                    if action.pattern_id == "sem_00_double_step_creates_token"
                    and (action.from_square.file, action.from_square.rank) == (2, 1)
                    and (action.to_square.file, action.to_square.rank) == (2, 3)]
    session.submit(double_step)
    off_target, = [action for action in session.legal_actions()
                   if action.pattern_id == "sem_02_token_adjacent_capture_left"]
    token_slot, = (slot.slot_id for slot in compiled.ir.aux_slots)

    class OffTargetCaptureProbe:
        def evaluate(self, state):
            board = state.position.board
            captured = (
                board[2 * 8 + 2] == Piece(1, "P", "P")
                and board[3 * 8 + 2] is None
                and state.position.hands[1].count("P") == 1
                and dict(state.position.aux_state).get((token_slot, -1)) is None
            )
            value = 10_000 if captured else 0
            return -value if state.position.side_to_move == 0 else value

    player = AlphaBetaPlayer(
        compiled,
        use_disk_cache=False,
        use_native_semantic_legality=True,
        use_tt=False,
        use_ordering=False,
        evaluator_override=OffTargetCaptureProbe(),
    )
    input_record = session.to_record()
    decision = player.choose_action(session, SearchLimits(
        max_depth=2,
        max_nodes=1_000,
        quiescence_max_depth=0,
        quiescence_hard_max_depth=0,
        quiescence_max_nodes=0,
    ))

    assert decision.completed_depth == 2
    assert decision.action == off_target
    assert decision.principal_variation[0] == off_target
    assert session.to_record() == input_record

    replay = GameSession(compiled)
    for record in session.history:
        replay.submit(record.action)
    for action in decision.principal_variation:
        assert action in replay.legal_actions()
        replay.submit(action)
    assert replay.state.position.board[2 * 8 + 2] == Piece(1, "P", "P")
    assert replay.state.position.board[3 * 8 + 2] is None
    assert replay.state.position.hands[1].count("P") == 1
    assert dict(replay.state.position.aux_state)[(token_slot, -1)] is None

    # The same return contract applies when semantic action-base removal
    # deliberately routes legality through Core rather than Native.
    assert player.native_legality_provider is None
    for node_cap, minimum_depth in ((1, 0), (25, 1)):
        limited = player.choose_action(session, SearchLimits(
            max_depth=3,
            max_nodes=node_cap,
            quiescence_max_depth=0,
            quiescence_hard_max_depth=0,
            quiescence_max_nodes=0,
        ))
        assert limited.termination_reason == "node_limit"
        assert limited.completed_depth >= minimum_depth
        assert limited.completed_depth < 3
        assert limited.nodes <= node_cap
        assert limited.action in session.legal_actions()
        if limited.completed_depth == 0:
            assert limited.principal_variation == ()
        else:
            assert limited.principal_variation[0] == limited.action
            replay = GameSession.replay(compiled, session.to_record())
            for action in limited.principal_variation:
                assert action in replay.legal_actions()
                replay.submit(action)
        assert limited.native_legality_calls == 0
        assert limited.native_legality_fallbacks == 0
        assert limited.native_legality_operational_failures == 0
        assert session.to_record() == input_record
