from dataclasses import replace
import json

import pytest

from generic_chess import build_standard_shogi_ruleset, build_western_chess_ruleset
from generic_chess.core.actions import BoardMove, PassAction, SemanticBoardMove
from generic_chess.core.coordinates import Square
from generic_chess.core.errors import IllegalActionError
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.movegen import legal_actions
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.terminal import TerminalStatus, terminal_result
from generic_chess.core.transition import apply_action, initial_state, legal_successors
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.cancellation import CancellationToken
from generic_chess.ai.limits import SearchLimits
from generic_chess.rules.compiler import (
    compile_ruleset,
    compile_ruleset_for_execution,
    compile_semantic_ruleset,
)
from generic_chess.rules.schema import (
    RuleConsecutiveActionAdjudication,
    RuleActionEffect,
    RuleAuxState,
    RuleGeometrySpec,
    RuleInvariant,
    RulePathConstraint,
    RuleReplaceSelector,
    RuleSemanticAction,
    RuleSlotGuard,
    RuleSquareRef,
    RuleTypeRef,
    RuleSet,
    compute_fingerprint,
    ruleset_from_dict,
    ruleset_to_dict,
)
from rule_semantics_ir_fixtures import _king_type, _semantic_ruleset
from generic_chess.rules.validation import RuleValidationError
from generic_chess.rules.xiangqi_diagnostic import build_xiangqi_diagnostic_ruleset
from generic_chess.session.result import SessionStatus
from generic_chess.session.serialization import deserialize_game_record, serialize_game_record
from generic_chess.session.session import GameSession


def _legacy_ruleset(*, pass_enabled=True, policy=True):
    n = 4
    king = PieceType(
        "K",
        "Anchor",
        tuple(
            LeapAtom((df, dr))
            for df in (-1, 0, 1)
            for dr in (-1, 0, 1)
            if df or dr
        ),
        is_anchor=True,
    )
    rook = PieceType(
        "R",
        "Rook",
        tuple(RayAtom(d) for d in ((1, 0), (-1, 0), (0, 1), (0, -1))),
    )
    rows = [[None] * n for _ in range(n)]
    rows[0][0] = Piece(0, "K", "K")
    rows[3][3] = Piece(1, "K", "K")
    rows[0][1] = Piece(0, "R", "R")
    mask = (False,) * (n * n)
    policies = (
        (RuleConsecutiveActionAdjudication("pass", 2, "DRAW"),)
        if policy
        else ()
    )
    return RuleSet(
        board_size=n,
        piece_types=(king, rook),
        initial_position=tuple(tuple(row) for row in rows),
        drop_allowed={"R": (mask, mask)},
        pass_enabled=pass_enabled,
        repetition_limit=2 if policy else 20,
        consecutive_action_adjudications=policies,
    )


def _compiled(semantic=False, *, pass_enabled=True, policy=True):
    if semantic:
        ruleset = replace(
            build_western_chess_ruleset(),
            pass_enabled=pass_enabled,
            repetition_limit=2 if policy else 20,
            consecutive_action_adjudications=(
                (RuleConsecutiveActionAdjudication("pass", 2, "DRAW"),)
                if policy
                else ()
            ),
        )
        return ruleset, compile_ruleset_for_execution(ruleset)
    ruleset = _legacy_ruleset(pass_enabled=pass_enabled, policy=policy)
    return ruleset, compile_ruleset(ruleset)


def _blocked_pass_only_ruleset(*, repetition_limit=20, pass_threshold=None):
    base = _legacy_ruleset(pass_enabled=True, policy=False)
    n = base.board_size
    board = [[None] * n for _ in range(n)]
    board[0][0] = Piece(0, "K", "K")
    board[0][1] = Piece(0, "I", "I")
    board[1][0] = Piece(0, "I", "I")
    board[1][1] = Piece(0, "I", "I")
    board[n - 1][n - 1] = Piece(1, "K", "K")
    board[n - 2][n - 1] = Piece(1, "I", "I")
    board[n - 1][n - 2] = Piece(1, "I", "I")
    board[n - 2][n - 2] = Piece(1, "I", "I")
    mask = (False,) * (n * n)
    policies = (
        (RuleConsecutiveActionAdjudication("pass", pass_threshold, "DRAW"),)
        if pass_threshold is not None
        else ()
    )
    return replace(
        base,
        piece_types=(base.piece_types[0], PieceType("I", "Immobile", ())),
        initial_position=tuple(tuple(row) for row in board),
        drop_allowed={"I": (mask, mask)},
        repetition_limit=repetition_limit,
        consecutive_action_adjudications=policies,
    )


def _pass_mate_ruleset(threshold):
    active = RuleAuxState("active", "bool", "global", "expire_next_turn", 0)
    spent = RuleAuxState("spent", "bool", "global", "persistent", 0)
    rook = PieceType(
        "R",
        "Rook",
        tuple(RayAtom(direction) for direction in ((1, 0), (-1, 0), (0, 1), (0, -1))),
    )
    bishop = PieceType(
        "B",
        "Bishop",
        tuple(RayAtom(direction) for direction in ((1, 1), (1, -1), (-1, 1), (-1, -1))),
    )
    screen_mover = PieceType("M", "ScreenMover", ())
    immobile = PieceType("I", "Immobile", ())
    rook_capture = RuleSemanticAction(
        name="conditional_rook_capture",
        type_ids=("R",),
        geometry=RuleGeometrySpec(kind="legacy_atoms", atom_kind="ray"),
        target_relation="enemy",
        composition="replace_legacy",
        path_constraints=(RulePathConstraint("path_clear"),),
        replace_selector=RuleReplaceSelector(
            type_ids=("R",),
            action_family="board",
            target_relation="enemy",
            geometry_kind="ray",
            replace_all_matching=True,
        ),
        aux_state=(active,),
        slot_guards=(RuleSlotGuard("active", comparison="eq", value=0),),
        effects=(
            RuleActionEffect(
                "remove",
                square_ref=RuleSquareRef("target"),
                piece_owner="opponent",
                piece_type_ref=RuleTypeRef("any"),
                disposition="remove_from_game",
            ),
            RuleActionEffect(
                "move",
                from_ref=RuleSquareRef("source"),
                to_ref=RuleSquareRef("target"),
            ),
        ),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    clear_screen = RuleSemanticAction(
        name="clear_screen",
        type_ids=("M",),
        geometry=RuleGeometrySpec(
            kind="leap", offset=(-1, -1), owner_relative=False
        ),
        target_relation="empty",
        aux_state=(active, spent),
        slot_guards=(RuleSlotGuard("spent", comparison="eq", value=0),),
        effects=(
            RuleActionEffect(
                "move",
                from_ref=RuleSquareRef("source"),
                to_ref=RuleSquareRef("target"),
            ),
            RuleActionEffect("set_bool", slot_name="active", value=1),
            RuleActionEffect("set_bool", slot_name="spent", value=1),
        ),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    rows = [[None] * 5 for _ in range(5)]
    rows[0][0] = Piece(0, "K", "K")
    rows[0][1] = Piece(0, "B", "B")
    rows[0][4] = Piece(0, "R", "R")
    rows[4][4] = Piece(1, "K", "K")
    rows[2][4] = Piece(1, "M", "M")
    for file, rank in ((3, 4), (3, 3)):
        rows[rank][file] = Piece(1, "I", "I")
    ruleset = _semantic_ruleset(
        (_king_type(), rook, bishop, screen_mover, immobile),
        (rook_capture, clear_screen),
        n=5,
        rows=tuple(tuple(row) for row in rows),
    )
    return replace(
        ruleset,
        pass_enabled=True,
        repetition_limit=20,
        consecutive_action_adjudications=(
            RuleConsecutiveActionAdjudication("pass", threshold, "DRAW"),
        ),
    )


def _blocked_pass_only_semantic_ruleset(*, repetition_limit=20, pass_threshold=3):
    base = _pass_mate_ruleset(threshold=pass_threshold or 3)
    n = base.board_size
    board = [[None] * n for _ in range(n)]
    board[0][0] = Piece(0, "K", "K")
    board[0][1] = Piece(0, "I", "I")
    board[1][0] = Piece(0, "I", "I")
    board[1][1] = Piece(0, "I", "I")
    board[n - 1][n - 1] = Piece(1, "K", "K")
    board[n - 2][n - 1] = Piece(1, "I", "I")
    board[n - 1][n - 2] = Piece(1, "I", "I")
    board[n - 2][n - 2] = Piece(1, "I", "I")
    policies = (
        base.consecutive_action_adjudications
        if pass_threshold is not None
        else ()
    )
    return replace(
        base,
        initial_position=tuple(tuple(row) for row in board),
        repetition_limit=repetition_limit,
        consecutive_action_adjudications=policies,
    )


def _start_with_side(state, compiled, side):
    position = replace(state.position, side_to_move=side)
    key = repetition_identity_key(position, compiled)
    history = (replace(state.history[0], position_key=key),)
    return replace(
        state,
        position=position,
        repetition_counts=((key, 1),),
        history=history,
    )


@pytest.mark.parametrize("semantic", [False, True], ids=["legacy", "semantic"])
@pytest.mark.parametrize("side", [0, 1], ids=["owner-0-first", "owner-1-first"])
def test_two_consecutive_passes_draw_and_trial_matches_commit(semantic, side):
    _, compiled = _compiled(semantic)
    state = _start_with_side(initial_state(compiled), compiled, side)
    initial_key = repetition_identity_key(state.position, compiled)
    first = dict(legal_successors(state, compiled))[PassAction()]
    assert apply_action(state, PassAction(), compiled) == first
    assert first.terminal_status.status is TerminalStatus.ONGOING

    second = dict(legal_successors(first, compiled))[PassAction()]
    committed = apply_action(first, PassAction(), compiled)
    assert committed == second
    assert committed.position.board == state.position.board
    assert repetition_identity_key(committed.position, compiled) == initial_key
    assert dict(committed.repetition_counts)[initial_key] == 2
    assert committed.terminal_status.status is TerminalStatus.ACTION_CLASS_DRAW
    assert committed.terminal_status.winner is None
    assert terminal_result(committed, compiled).status is TerminalStatus.ACTION_CLASS_DRAW
    assert not legal_actions(committed, compiled)


def test_public_alphabeta_pass_pv_submits_and_replays_consecutive_pass_draw():
    _, compiled = _compiled(semantic=False, pass_enabled=True, policy=True)
    session = GameSession(compiled)
    initial = session.state

    class PreferPassEvaluator:
        def evaluate(self, state):
            # The mutable search view and public GameState share this position
            # field. Pass preserves the board; every ordinary action changes it.
            return -10_000 if state.position.board == initial.position.board else 10_000

    player = AlphaBetaPlayer(
        compiled,
        evaluator_override=PreferPassEvaluator(),
        use_disk_cache=False,
    )
    limits = SearchLimits(
        max_depth=1,
        max_nodes=10_000,
        max_time_seconds=5,
        quiescence_max_depth=0,
        quiescence_hard_max_depth=0,
    )

    for expected_status in (SessionStatus.ONGOING, SessionStatus.ACTION_CLASS_DRAW):
        before = session.state
        decision = player.choose_action(session, limits)
        assert decision.completed_depth == 1
        assert isinstance(decision.action, PassAction)
        assert decision.principal_variation
        assert decision.principal_variation[0] == decision.action

        pv_state = before
        for action in decision.principal_variation:
            pv_state = apply_action(pv_state, action, compiled)
        committed_state = apply_action(before, decision.action, compiled)
        assert pv_state == committed_state

        session.submit(decision.action)
        assert session.state == committed_state
        assert session.state.terminal_status.status.value == expected_status.value

    assert session.result.status is SessionStatus.ACTION_CLASS_DRAW
    terminal_decision = player.choose_action(session, limits)
    assert terminal_decision.action is None
    assert terminal_decision.choice_kind == "TERMINAL"
    assert terminal_decision.termination_reason == "terminal_position"
    pass_signatures = [
        json.loads(record.action_signature)
        for record in session.state.history
        if record.action_signature
    ]
    assert pass_signatures == [{"kind": "pass"}, {"kind": "pass"}]

    record = deserialize_game_record(serialize_game_record(session.to_record()))
    replayed = GameSession.replay(compiled, record)
    assert replayed.state == session.state
    assert replayed.result == session.result
    assert replayed.state.position.board == initial.position.board
    assert replayed.state.position.hands == initial.position.hands


@pytest.mark.parametrize(
    "threshold, expected_qscore",
    [(3, 0), (4, -1_000)],
    ids=["include-terminal-pass", "exclude-quiet-pass"],
)
def test_public_qsearch_pass_child_policy(threshold, expected_qscore):
    ruleset = _blocked_pass_only_ruleset(pass_threshold=threshold)
    compiled = compile_ruleset(ruleset)
    initial = GameSession(compiled).state
    first_pass = dict(legal_successors(initial, compiled))[PassAction()]
    second_pass = dict(legal_successors(first_pass, compiled))[PassAction()]
    assert legal_actions(initial, compiled) == [PassAction()]
    assert legal_actions(first_pass, compiled) == [PassAction()]
    assert second_pass.terminal_status.status is TerminalStatus.ONGOING
    third_pass = dict(legal_successors(second_pass, compiled))[PassAction()]
    assert third_pass.terminal_status.status is (
        TerminalStatus.ACTION_CLASS_DRAW
        if threshold == 3
        else TerminalStatus.ONGOING
    )
    if threshold == 4:
        fourth_pass = dict(legal_successors(third_pass, compiled))[PassAction()]
        assert fourth_pass.terminal_status.status is TerminalStatus.ACTION_CLASS_DRAW

    class PreferDrawOverStaticLeaf:
        def evaluate(self, state):
            return -1_000 if state.position.side_to_move == 0 else 1_000

    def search(qdepth):
        return AlphaBetaPlayer(
            compiled,
            evaluator_override=PreferDrawOverStaticLeaf(),
            use_disk_cache=False,
        ).choose_action(
            GameSession(compiled),
            SearchLimits(
                max_depth=2,
                max_nodes=1_000,
                max_time_seconds=5,
                quiescence_max_depth=qdepth,
                quiescence_hard_max_depth=2,
            ),
        )

    without_qsearch = search(0)
    with_qsearch = search(1)
    assert without_qsearch.completed_depth == with_qsearch.completed_depth == 2
    assert without_qsearch.score == -1_000
    assert with_qsearch.score == expected_qscore
    assert with_qsearch.qnodes > 0
    assert isinstance(with_qsearch.action, PassAction)


def test_public_semantic_qsearch_includes_terminal_pass_child():
    ruleset = _blocked_pass_only_semantic_ruleset()
    compiled = compile_ruleset_for_execution(
        ruleset
    )
    initial = GameSession(compiled).state
    first_pass = dict(legal_successors(initial, compiled))[PassAction()]
    second_pass = dict(legal_successors(first_pass, compiled))[PassAction()]
    third_pass = dict(legal_successors(second_pass, compiled))[PassAction()]
    assert type(compiled).__name__ == "ExecutableSemanticRuleset"
    assert len(ruleset.semantic_actions) == 2
    assert legal_actions(initial, compiled) == [PassAction()]
    assert legal_actions(first_pass, compiled) == [PassAction()]
    assert second_pass.terminal_status.status is TerminalStatus.ONGOING
    assert third_pass.terminal_status.status is TerminalStatus.ACTION_CLASS_DRAW

    class PreferDrawOverStaticLeaf:
        def evaluate(self, state):
            return -1_000 if state.position.side_to_move == 0 else 1_000

    def search(qdepth):
        return AlphaBetaPlayer(
            compiled,
            evaluator_override=PreferDrawOverStaticLeaf(),
            use_disk_cache=False,
        ).choose_action(
            GameSession(compiled),
            SearchLimits(
                max_depth=2,
                max_nodes=1_000,
                max_time_seconds=5,
                quiescence_max_depth=qdepth,
                quiescence_hard_max_depth=2,
            ),
        )

    without_qsearch = search(0)
    with_qsearch = search(1)
    assert without_qsearch.completed_depth == with_qsearch.completed_depth == 2
    assert without_qsearch.score == -1_000
    assert with_qsearch.score == 0
    assert with_qsearch.qnodes > 0
    assert isinstance(with_qsearch.action, PassAction)


def test_public_qsearch_includes_repetition_pass_child():
    compiled = compile_ruleset(
        _blocked_pass_only_ruleset(repetition_limit=3)
    )
    states = [GameSession(compiled).state]
    for _ in range(4):
        states.append(dict(legal_successors(states[-1], compiled))[PassAction()])
    assert legal_actions(states[0], compiled) == [PassAction()]
    assert legal_actions(states[2], compiled) == [PassAction()]
    assert states[3].terminal_status.status is TerminalStatus.ONGOING
    assert states[4].terminal_status.status is TerminalStatus.REPETITION

    class PreferDrawOverStaticLeaf:
        def evaluate(self, state):
            return -1_000 if state.position.side_to_move == 1 else 1_000

    def search(qdepth):
        return AlphaBetaPlayer(
            compiled,
            evaluator_override=PreferDrawOverStaticLeaf(),
            use_disk_cache=False,
        ).choose_action(
            GameSession(compiled),
            SearchLimits(
                max_depth=3,
                max_nodes=1_000,
                max_time_seconds=5,
                quiescence_max_depth=qdepth,
                quiescence_hard_max_depth=2,
            ),
        )

    without_qsearch = search(0)
    with_qsearch = search(1)
    assert without_qsearch.completed_depth == with_qsearch.completed_depth == 3
    assert without_qsearch.score == 1_000
    assert with_qsearch.score == 0
    assert with_qsearch.qnodes > 0
    assert isinstance(with_qsearch.action, PassAction)


def test_public_semantic_qsearch_includes_repetition_pass_child():
    ruleset = _blocked_pass_only_semantic_ruleset(
        repetition_limit=3,
        pass_threshold=None,
    )
    compiled = compile_ruleset_for_execution(ruleset)
    states = [GameSession(compiled).state]
    for _ in range(4):
        states.append(dict(legal_successors(states[-1], compiled))[PassAction()])
    assert type(compiled).__name__ == "ExecutableSemanticRuleset"
    assert len(ruleset.semantic_actions) == 2
    assert legal_actions(states[0], compiled) == [PassAction()]
    assert states[3].terminal_status.status is TerminalStatus.ONGOING
    assert states[4].terminal_status.status is TerminalStatus.REPETITION

    class PreferDrawOverStaticLeaf:
        def evaluate(self, state):
            return -1_000 if state.position.side_to_move == 1 else 1_000

    def search(qdepth):
        return AlphaBetaPlayer(
            compiled,
            evaluator_override=PreferDrawOverStaticLeaf(),
            use_disk_cache=False,
        ).choose_action(
            GameSession(compiled),
            SearchLimits(
                max_depth=3,
                max_nodes=1_000,
                max_time_seconds=5,
                quiescence_max_depth=qdepth,
                quiescence_hard_max_depth=2,
            ),
        )

    without_qsearch = search(0)
    with_qsearch = search(1)
    assert without_qsearch.completed_depth == with_qsearch.completed_depth == 3
    assert without_qsearch.score == 1_000
    assert with_qsearch.score == 0
    assert with_qsearch.qnodes > 0
    assert isinstance(with_qsearch.action, PassAction)


def test_compiled_semantic_pass_rules_decline_native_and_keep_core_qsearch():
    ruleset = _blocked_pass_only_semantic_ruleset(
        repetition_limit=3,
        pass_threshold=None,
    )
    compiled = compile_semantic_ruleset(ruleset)
    session = GameSession(compiled)

    class PreferDrawOverStaticLeaf:
        def evaluate(self, state):
            return -1_000 if state.position.side_to_move == 1 else 1_000

    player = AlphaBetaPlayer(
        compiled,
        evaluator_override=PreferDrawOverStaticLeaf(),
        use_disk_cache=False,
    )
    assert type(compiled).__name__ == "CompiledSemanticRuleset"
    assert player.native_legality_provider is None
    decision = player.choose_action(
        session,
        SearchLimits(
            max_depth=3,
            max_nodes=1_000,
            max_time_seconds=5,
            quiescence_max_depth=1,
            quiescence_hard_max_depth=2,
        ),
    )

    assert isinstance(decision.action, PassAction)
    assert decision.score == 0
    assert decision.completed_depth == 3
    assert decision.qnodes == 4
    assert decision.native_legality_calls == 0
    assert decision.native_legality_fallbacks == 0
    assert decision.native_legality_operational_failures == 0
    assert len(session.state.history) == 1


def test_pre_cancelled_public_alphabeta_returns_legal_fallback_with_pass_available():
    _, compiled = _compiled(semantic=False, pass_enabled=True, policy=True)
    session = GameSession(compiled)
    before = session.state
    legal = legal_actions(before, compiled)
    assert PassAction() in legal

    token = CancellationToken()
    token.cancel()
    decision = AlphaBetaPlayer(compiled, use_disk_cache=False).choose_action(
        session,
        SearchLimits(
            max_depth=2,
            max_nodes=1_000,
            max_time_seconds=5,
            quiescence_max_depth=0,
            quiescence_hard_max_depth=0,
        ),
        cancel_token=token,
    )

    assert decision.termination_reason == "cancelled"
    assert decision.completed_depth == 0
    assert decision.action in legal
    assert session.state is before


def test_nonpass_action_resets_consecutive_pass_count():
    _, compiled = _compiled()
    state = initial_state(compiled)
    after_pass = apply_action(state, PassAction(), compiled)
    ordinary = next(
        action
        for action in legal_actions(after_pass, compiled)
        if isinstance(action, (BoardMove, SemanticBoardMove))
    )
    after_ordinary = apply_action(after_pass, ordinary, compiled)
    after_one_new_pass = apply_action(after_ordinary, PassAction(), compiled)
    assert after_one_new_pass.terminal_status.status is TerminalStatus.ONGOING
    after_two_new_passes = apply_action(after_one_new_pass, PassAction(), compiled)
    assert after_two_new_passes.terminal_status.status is TerminalStatus.ACTION_CLASS_DRAW

    ordinary_first = next(
        action
        for action in legal_actions(initial_state(compiled), compiled)
        if isinstance(action, BoardMove)
    )
    reset = apply_action(initial_state(compiled), ordinary_first, compiled)
    reset = apply_action(reset, PassAction(), compiled)
    reset = apply_action(reset, PassAction(), compiled)
    assert reset.terminal_status.status is TerminalStatus.ACTION_CLASS_DRAW


@pytest.mark.parametrize("semantic", [False, True], ids=["legacy", "semantic"])
def test_mutable_trial_path_uses_the_same_terminal_policy(semantic):
    _, compiled = _compiled(semantic)
    runtime = SearchPathRuntime.from_state(initial_state(compiled), compiled)
    runtime.push(PassAction())
    assert runtime.terminal_status.status is TerminalStatus.ONGOING
    runtime.push(PassAction())
    assert runtime.terminal_status.status is TerminalStatus.ACTION_CLASS_DRAW
    runtime.pop()
    assert runtime.terminal_status.status is TerminalStatus.ONGOING
    runtime.pop()
    runtime.assert_balanced()


def _pass_mate_prefix(compiled):
    state = initial_state(compiled)
    king_move = next(
        action
        for action in legal_actions(state, compiled)
        if getattr(action, "from_square", None) == Square(0, 0)
        and getattr(action, "to_square", None) == Square(1, 1)
    )
    state = apply_action(state, king_move, compiled)
    screen_move = next(
        action
        for action in legal_actions(state, compiled)
        if getattr(action, "from_square", None) == Square(4, 2)
        and getattr(action, "to_square", None) == Square(3, 1)
    )
    return apply_action(state, screen_move, compiled)


def _action_between(state, compiled, source, target):
    return next(
        action
        for action in legal_actions(state, compiled)
        if getattr(action, "from_square", None) == source
        and getattr(action, "to_square", None) == target
    )


def test_action_class_draw_at_threshold_precedes_no_legal_reply():
    compiled = compile_ruleset_for_execution(_pass_mate_ruleset(threshold=1))
    state = _pass_mate_prefix(compiled)
    assert PassAction() in legal_actions(state, compiled)

    successors = dict(legal_successors(state, compiled))
    after_pass = successors[PassAction()]
    assert not legal_actions(after_pass, compiled)
    assert after_pass.terminal_status.status is TerminalStatus.ACTION_CLASS_DRAW
    assert apply_action(state, PassAction(), compiled) == after_pass
    assert terminal_result(after_pass, compiled).status is TerminalStatus.ACTION_CLASS_DRAW

    runtime = SearchPathRuntime.from_state(state, compiled)
    runtime.push(PassAction())
    assert runtime.terminal_status.status is TerminalStatus.ACTION_CLASS_DRAW
    runtime.pop()
    runtime.assert_balanced()

    session = GameSession(compiled)
    session.submit(_action_between(session.state, compiled, Square(0, 0), Square(1, 1)))
    session.submit(_action_between(session.state, compiled, Square(4, 2), Square(3, 1)))
    session.submit(PassAction())
    assert session.state == after_pass
    assert session.result.status is SessionStatus.ACTION_CLASS_DRAW
    record = deserialize_game_record(serialize_game_record(session.to_record()))
    replayed = GameSession.replay(compiled, record)
    assert replayed.result.status is SessionStatus.ACTION_CLASS_DRAW
    assert replayed.state == session.state


def test_below_action_class_threshold_no_legal_reply_keeps_checkmate():
    compiled = compile_ruleset_for_execution(_pass_mate_ruleset(threshold=2))
    state = _pass_mate_prefix(compiled)
    after_pass = apply_action(state, PassAction(), compiled)

    assert not legal_actions(after_pass, compiled)
    assert after_pass.terminal_status.status is TerminalStatus.CHECKMATE
    assert after_pass.terminal_status.winner == 0
    assert terminal_result(after_pass, compiled).status is TerminalStatus.CHECKMATE


def test_legacy_terminal_paths_keep_action_class_precedence(monkeypatch):
    import generic_chess.core.terminal as terminal_module

    ruleset = replace(
        _legacy_ruleset(),
        repetition_limit=20,
        consecutive_action_adjudications=(
        RuleConsecutiveActionAdjudication("pass", 1, "DRAW"),
        ),
    )
    compiled = compile_ruleset(ruleset)
    start = initial_state(compiled)
    assert PassAction() in legal_actions(start, compiled)
    after = apply_action(start, PassAction(), compiled)
    assert after.terminal_status.status is TerminalStatus.ACTION_CLASS_DRAW

    # Legacy pass preserves the board, so a no-reply child cannot be produced
    # by this action. Force that terminal probe branch to verify policy order;
    # the semantic end-to-end fixture above covers the reachable no-reply case.
    monkeypatch.setattr(terminal_module, "has_legal_action", lambda *_args: False)
    monkeypatch.setattr(terminal_module, "is_in_check", lambda *_args: True)
    assert terminal_result(after, compiled).status is TerminalStatus.ACTION_CLASS_DRAW

    runtime = SearchPathRuntime.from_state(start, compiled)
    runtime.push(PassAction())
    assert runtime.terminal_status.status is TerminalStatus.ACTION_CLASS_DRAW
    runtime.pop()
    runtime.assert_balanced()


def test_rejected_checked_pass_does_not_advance_action_history():
    _, compiled = _compiled()
    state = apply_action(initial_state(compiled), PassAction(), compiled)
    board = [None] * 16
    board[0] = Piece(0, "K", "K")
    board[15] = Piece(1, "K", "K")
    board[3] = Piece(0, "R", "R")
    checked = replace(state, position=replace(state.position, board=tuple(board)))
    with pytest.raises(IllegalActionError):
        apply_action(checked, PassAction(), compiled)
    assert len(checked.history) == 2

    board[3] = None
    legal_after_repair = replace(
        checked,
        position=replace(checked.position, board=tuple(board)),
    )
    finished = apply_action(legal_after_repair, PassAction(), compiled)
    assert finished.terminal_status.status is TerminalStatus.ACTION_CLASS_DRAW


def test_disabled_policy_and_disabled_pass_are_inert():
    _, pass_only = _compiled(policy=False)
    state = initial_state(pass_only)
    state = apply_action(state, PassAction(), pass_only)
    state = apply_action(state, PassAction(), pass_only)
    assert state.terminal_status.status is TerminalStatus.ONGOING

    _, pass_disabled = _compiled(pass_enabled=False, policy=False)
    state = initial_state(pass_disabled)
    assert PassAction() not in legal_actions(state, pass_disabled)
    with pytest.raises(IllegalActionError):
        apply_action(state, PassAction(), pass_disabled)

    with pytest.raises(RuleValidationError, match="CONSECUTIVE_ACTION_CLASS_DISABLED"):
        compile_ruleset(_legacy_ruleset(pass_enabled=False, policy=True))


def test_policy_roundtrip_fingerprint_session_replay_and_legacy_identity():
    base = build_western_chess_ruleset()
    assert "consecutive_action_adjudications" not in ruleset_to_dict(base)
    assert compute_fingerprint(ruleset_from_dict(ruleset_to_dict(base))) == compute_fingerprint(base)
    assert compute_fingerprint(
        replace(base, consecutive_action_adjudications=())
    ) == compute_fingerprint(base)

    ruleset, compiled = _compiled()
    data = ruleset_to_dict(ruleset)
    assert data["consecutive_action_adjudications"] == [
        {"action_class": "pass", "threshold": 2, "outcome": "DRAW"}
    ]
    restored = ruleset_from_dict(data)
    assert compute_fingerprint(restored) == compute_fingerprint(ruleset)
    assert ruleset_to_dict(restored) == data
    compiled = compile_ruleset(restored)
    assert tuple(
        (item.action_class, item.threshold, item.outcome)
        for item in compiled.consecutive_action_adjudications
    ) == (("pass", 2, "DRAW"),)

    session = GameSession(compiled)
    session.submit(PassAction())
    assert session.result.status is SessionStatus.ONGOING
    session.submit(PassAction())
    assert session.result.status is SessionStatus.ACTION_CLASS_DRAW
    assert session.result.winner is None
    record = deserialize_game_record(serialize_game_record(session.to_record()))
    replayed = GameSession.replay(compiled, record)
    assert replayed.state == session.state
    assert replayed.result.status is SessionStatus.ACTION_CLASS_DRAW
    assert json.loads(session.state.history[-1].action_signature) == {"kind": "pass"}


@pytest.mark.parametrize(
    "data, message",
    [
        ({"action_class": "castle", "threshold": 2, "outcome": "DRAW"}, "CONSECUTIVE_ACTION_CLASS_UNSUPPORTED"),
        ({"action_class": "pass", "threshold": 0, "outcome": "DRAW"}, "CONSECUTIVE_ACTION_THRESHOLD_INVALID"),
        ({"action_class": "pass", "threshold": 2, "outcome": "LOSS"}, "CONSECUTIVE_ACTION_OUTCOME_INVALID"),
        ({"action_class": "pass", "threshold": 2, "outcome": "DRAW", "trigger_ply": 4}, "UNKNOWN_FIELD"),
    ],
)
def test_malformed_and_unsupported_policy_definitions_fail_closed(data, message):
    payload = ruleset_to_dict(_legacy_ruleset())
    payload["consecutive_action_adjudications"] = [data]
    with pytest.raises(RuleValidationError, match=message):
        ruleset_from_dict(payload)


@pytest.mark.parametrize(
    "definitions",
    [None, "pass", (object(),)],
    ids=["not-a-sequence", "string-sequence", "wrong-entry-type"],
)
def test_programmatic_malformed_policy_definitions_fail_closed(definitions):
    ruleset = replace(
        _legacy_ruleset(), consecutive_action_adjudications=definitions
    )
    with pytest.raises(RuleValidationError, match="CONSECUTIVE_ACTION_ADJUDICATION"):
        compile_ruleset(ruleset)


def test_standard_products_keep_their_default_policy_disabled():
    for ruleset in (
        build_western_chess_ruleset(),
        build_standard_shogi_ruleset(),
        build_xiangqi_diagnostic_ruleset(),
    ):
        assert not ruleset.pass_enabled
        assert ruleset.consecutive_action_adjudications == ()
        compiled = compile_ruleset_for_execution(ruleset)
        assert compiled.consecutive_action_adjudications == ()
        state = initial_state(compiled)
        assert PassAction() not in legal_actions(state, compiled)
        assert state.terminal_status.status is TerminalStatus.ONGOING
