import json
from dataclasses import replace

import pytest

from generic_chess import build_western_chess_ruleset
from generic_chess.core.actions import (
    PassAction,
    SemanticBoardMove,
    SemanticDropMove,
    action_from_dict,
    action_to_dict,
)
from generic_chess.core.coordinates import Square
from generic_chess.core.errors import IllegalActionError
from generic_chess.core.history_provenance import reconstruct_history_provenance
from generic_chess.core.movegen import legal_actions
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.search_runtime import SearchPathRuntime, _full_runtime_hash
from generic_chess.core.transition import apply_action, initial_state, legal_successors
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.backend import PythonSearchBackend
from generic_chess.ai.alphabeta.snapshot import SearchSnapshot
from generic_chess.ai.limits import SearchLimits
from generic_chess.cli.play import _resolve_action_input, visible_action_alias
from generic_chess.rules.compiler import compile_ruleset, compile_ruleset_for_execution
from generic_chess.rules.schema import (
    RuleActionEffect,
    RuleAuxState,
    RuleGeometrySpec,
    RuleInvariant,
    RuleSemanticAction,
    RuleSet,
    RuleReplaceSelector,
    RuleSlotGuard,
    RuleSquareRef,
    RuleTypeRef,
    compute_fingerprint,
    ruleset_to_dict,
)
from generic_chess.native.compiler import (
    NativeUnsupportedRuleError,
    build_compile_payload,
    build_semantic_compile_payload,
)
from generic_chess.session.serialization import deserialize_game_record, serialize_game_record
from generic_chess.session.session import GameSession
from generic_chess.core.terminal import TerminalStatus
from rule_semantics_ir_fixtures import _king_type, _semantic_ruleset


def _legacy_ruleset(pass_enabled=False):
    n = 4
    king = PieceType(
        "K", "Anchor",
        tuple(
            LeapAtom((df, dr))
            for df in (-1, 0, 1)
            for dr in (-1, 0, 1)
            if df or dr
        ),
        is_anchor=True,
    )
    rook = PieceType(
        "R", "Rook",
        tuple(RayAtom(direction) for direction in ((1, 0), (-1, 0), (0, 1), (0, -1))),
    )
    rows = [[None] * n for _ in range(n)]
    rows[0][0] = Piece(0, "K", "K")
    rows[3][3] = Piece(1, "K", "K")
    rows[0][1] = Piece(0, "R", "R")
    mask = (False,) * (n * n)
    return RuleSet(
        board_size=n,
        piece_types=(king, rook),
        initial_position=tuple(tuple(row) for row in rows),
        drop_allowed={"R": (mask, mask)},
        pass_enabled=pass_enabled,
    )


def _compiled(semantic, enabled):
    ruleset = (
        replace(build_western_chess_ruleset(), pass_enabled=enabled)
        if semantic
        else _legacy_ruleset(pass_enabled=enabled)
    )
    return ruleset, (
        compile_ruleset_for_execution(ruleset) if semantic else compile_ruleset(ruleset)
    )


def _semantic_temp_ruleset(pass_enabled=True):
    n = 5
    marker = PieceType("A", "Marker", (LeapAtom((1, 0)),))
    rook = PieceType(
        "R", "Rook", tuple(RayAtom(d) for d in ((1, 0), (-1, 0), (0, 1), (0, -1)))
    )
    temp = RuleAuxState("temp", "bool", "global", "expire_next_turn", 0)
    mark = RuleSemanticAction(
        name="mark_ephemeral",
        type_ids=("A",),
        geometry=RuleGeometrySpec(kind="leap", offset=(1, 0)),
        target_relation="empty",
        aux_state=(temp,),
        effects=(
            RuleActionEffect(
                "move", from_ref=RuleSquareRef("source"), to_ref=RuleSquareRef("target")
            ),
            RuleActionEffect("set_bool", slot_name="temp", value=1),
        ),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    conditional_rook_capture = RuleSemanticAction(
        name="conditional_rook_capture",
        type_ids=("R",),
        geometry=RuleGeometrySpec(kind="legacy_atoms", atom_kind="ray"),
        target_relation="enemy",
        composition="replace_legacy",
        replace_selector=RuleReplaceSelector(
            type_ids=("R",),
            action_family="board",
            target_relation="enemy",
            geometry_kind="ray",
            replace_all_matching=True,
        ),
        aux_state=(temp,),
        slot_guards=(RuleSlotGuard("temp", comparison="eq", value=0),),
        effects=(
            RuleActionEffect(
                "remove",
                square_ref=RuleSquareRef("target"),
                piece_owner="opponent",
                piece_type_ref=RuleTypeRef("any"),
                disposition="remove_from_game",
            ),
            RuleActionEffect(
                "move", from_ref=RuleSquareRef("source"), to_ref=RuleSquareRef("target")
            ),
        ),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    rows = [[None] * n for _ in range(n)]
    rows[0][0] = Piece(0, "K", "K")
    rows[4][4] = Piece(1, "K", "K")
    rows[1][1] = Piece(0, "A", "A")
    rows[2][4] = Piece(1, "R", "R")
    ruleset = _semantic_ruleset(
        (_king_type(), marker, rook),
        (mark, conditional_rook_capture),
        n=n,
        rows=tuple(tuple(row) for row in rows),
    )
    return replace(ruleset, pass_enabled=pass_enabled)


@pytest.mark.parametrize("semantic", [False, True], ids=["legacy", "semantic"])
def test_opt_in_pass_updates_only_turn_history_and_repetition(semantic):
    ruleset, compiled = _compiled(semantic, True)
    state = initial_state(compiled)
    pass_action = PassAction()
    assert pass_action in legal_actions(state, compiled)

    children = dict((action, child) for action, child in legal_successors(state, compiled))
    assert children[pass_action] == apply_action(state, pass_action, compiled)
    state = children[pass_action]
    assert state.position.board == initial_state(compiled).position.board
    assert state.position.hands == initial_state(compiled).position.hands
    assert state.position.side_to_move == 1
    assert state.ply_count == 1
    assert state.history[-1].actor == 0
    assert json.loads(state.history[-1].action_signature) == {"kind": "pass"}
    assert not state.history[-1].gave_check
    assert state.terminal_status.status is TerminalStatus.ONGOING
    assert action_from_dict(action_to_dict(pass_action)) == pass_action

    session = GameSession(compiled)
    session.submit(pass_action)
    record = deserialize_game_record(serialize_game_record(session.to_record()))
    replayed = GameSession.replay(compiled, record)
    assert replayed.state == session.state
    assert replayed.history[0].action == pass_action

    for _ in range(5):
        state = apply_action(state, pass_action, compiled)
    assert state.position.board == initial_state(compiled).position.board
    assert state.position.hands == initial_state(compiled).position.hands
    assert state.position.side_to_move == initial_state(compiled).position.side_to_move
    assert dict(state.repetition_counts)[state.history[-1].position_key] >= 1
    if not semantic:
        assert state.terminal_status.status is TerminalStatus.REPETITION
    assert reconstruct_history_provenance(state, compiled).status == "verified"

    runtime = SearchPathRuntime.from_state(initial_state(compiled), compiled)
    root = runtime.position
    runtime.push(pass_action)
    assert runtime.position.side_to_move == 1
    assert runtime.runtime_hash == _full_runtime_hash(runtime.position, compiled)
    runtime.pop()
    assert runtime.position == root
    runtime.assert_balanced()


@pytest.mark.parametrize("semantic", [False, True], ids=["legacy", "semantic"])
@pytest.mark.parametrize("side", [0, 1], ids=["owner-0", "owner-1"])
def test_disabled_pass_preserves_rule_serialization_fingerprint_and_legal_set(semantic, side):
    ruleset, compiled = _compiled(semantic, False)
    base = build_western_chess_ruleset() if semantic else _legacy_ruleset()
    assert ruleset_to_dict(ruleset) == ruleset_to_dict(base)
    assert compute_fingerprint(ruleset) == compute_fingerprint(base)
    state = initial_state(compiled)
    state = replace(state, position=replace(state.position, side_to_move=side))
    assert PassAction() not in legal_actions(state, compiled)
    with pytest.raises(IllegalActionError):
        apply_action(state, PassAction(), compiled)


@pytest.mark.parametrize("semantic", [False, True], ids=["legacy", "semantic"])
@pytest.mark.parametrize("side", [0, 1], ids=["owner-0", "owner-1"])
def test_checked_side_cannot_pass(semantic, side):
    _, compiled = _compiled(semantic, True)
    state = initial_state(compiled)
    width = state.position.board_shape.width
    height = state.position.board_shape.height
    board = [None] * len(state.position.board)
    if side == 0:
        white_king = Square(width // 2, 0)
        black_king = Square(0, height - 1)
        checking_rook = Square(width // 2, height - 1)
        board[white_king.rank * width + white_king.file] = Piece(0, "K", "K")
        board[black_king.rank * width + black_king.file] = Piece(1, "K", "K")
        board[checking_rook.rank * width + checking_rook.file] = Piece(1, "R", "R")
    else:
        white_king = Square(0, 0)
        black_king = Square(width // 2, height - 1)
        checking_rook = Square(width // 2, 0)
        board[white_king.rank * width + white_king.file] = Piece(0, "K", "K")
        board[black_king.rank * width + black_king.file] = Piece(1, "K", "K")
        board[checking_rook.rank * width + checking_rook.file] = Piece(0, "R", "R")
    position = replace(state.position, board=tuple(board), side_to_move=side)
    state = replace(state, position=position)

    from generic_chess.core.attacks import is_in_check

    assert is_in_check(position, side, compiled)
    assert PassAction() not in legal_actions(state, compiled)
    with pytest.raises(IllegalActionError):
        apply_action(state, PassAction(), compiled)


@pytest.mark.parametrize("semantic", [False, True], ids=["legacy", "semantic"])
def test_native_compilation_fails_closed_for_enabled_pass(semantic):
    _, compiled = _compiled(semantic, True)
    if semantic:
        with pytest.raises(NativeUnsupportedRuleError, match="pass actions"):
            build_semantic_compile_payload(compiled)
    else:
        with pytest.raises(NativeUnsupportedRuleError, match="pass actions"):
            build_compile_payload(compiled)


def test_semantic_pass_expires_aux_and_replays_history() -> None:
    _, compiled = _compiled_semantic_temp()
    state = initial_state(compiled)
    marker = next(
        action
        for action in legal_actions(state, compiled)
        if getattr(action, "pattern_id", "").endswith("mark_ephemeral")
        if getattr(action, "from_square", None) == Square(1, 1)
        and getattr(action, "to_square", None) == Square(2, 1)
    )
    marked = apply_action(state, marker, compiled)
    before_board = marked.position.board
    before_hands = marked.position.hands
    assert marked.position.side_to_move == 1
    slot = next(slot for slot in compiled.ir.aux_slots if slot.value_kind == "bool")
    assert dict(marked.position.aux_state)[(slot.slot_id, -1)] == 1
    assert PassAction() in legal_actions(marked, compiled)

    successor = dict(legal_successors(marked, compiled))[PassAction()]
    applied = apply_action(marked, PassAction(), compiled)
    assert successor == applied
    assert applied.position.board == before_board
    assert applied.position.hands == before_hands
    assert applied.position.side_to_move == 0
    assert dict(applied.position.aux_state)[(slot.slot_id, -1)] == slot.initial
    assert reconstruct_history_provenance(applied, compiled).status == "verified"


def _compiled_semantic_temp():
    ruleset = _semantic_temp_ruleset()
    return ruleset, compile_ruleset_for_execution(ruleset)


def test_cli_input_resolution_handles_pass_in_mixed_semantic_actions(tmp_path):
    from io import StringIO

    from generic_chess.cli.play import main
    from generic_chess.rules.serialization import serialize_ruleset
    from generic_chess.session.serialization import deserialize_game_record

    ruleset, compiled = _compiled_semantic_temp()
    actions = tuple(legal_actions(initial_state(compiled), compiled))
    pass_action = PassAction()
    board_action = next(
        action for action in actions if isinstance(action, SemanticBoardMove)
    )

    assert pass_action in actions
    assert visible_action_alias(pass_action) == "pass"
    assert _resolve_action_input("pass", actions) == (pass_action, None)
    assert _resolve_action_input(str(board_action), actions) == (board_action, None)
    alias = visible_action_alias(board_action)
    assert _resolve_action_input(alias, actions) == (
        None,
        f"ambiguous action alias: {alias!r} (use a number or exact action string)",
    )
    assert _resolve_action_input("not-a-move", actions) == (None, None)

    rules_path = tmp_path / "pass-enabled-semantic-rules.json"
    record_path = tmp_path / "pass-enabled-semantic-record.json"
    rules_path.write_text(serialize_ruleset(ruleset), encoding="utf-8")
    output = StringIO()
    assert main(
        ["--ruleset", str(rules_path), "--record-out", str(record_path)],
        stdin=StringIO(
            f"{alias}\nnot-a-move\npass\nquit\n"
        ),
        stdout=output,
    ) == 0, output.getvalue()
    assert f"ambiguous action alias: {alias!r}" in output.getvalue()
    assert "unknown input: 'not-a-move'" in output.getvalue()
    record = deserialize_game_record(record_path.read_text(encoding="utf-8"))
    assert record.actions == (pass_action,)


def test_public_alphabeta_root_selects_pass_and_generated_semantic_action() -> None:
    _, compiled = _compiled_semantic_temp()
    initial = initial_state(compiled)
    core_root = set(legal_actions(initial, compiled))
    runtime_root = set(SearchPathRuntime.from_state(initial, compiled).legal_actions())
    semantic_actions = {
        action
        for action in core_root
        if isinstance(action, (SemanticBoardMove, SemanticDropMove))
    }
    assert runtime_root == core_root
    assert PassAction() in core_root
    assert any(getattr(action, "pattern_id", "").endswith("mark_ephemeral")
               for action in semantic_actions)

    class PreferPassEvaluator:
        def evaluate(self, state):
            return -10_000 if state.position.board == initial.position.board else 10_000

    class PreferMarkedEvaluator:
        def evaluate(self, state):
            return -10_000 if any(value == 1 for _, value in state.position.aux_state) else 10_000

    limits = SearchLimits(
        max_depth=1,
        max_nodes=10_000,
        max_time_seconds=5,
        quiescence_max_depth=0,
        quiescence_hard_max_depth=0,
    )
    for evaluator, expected_type in (
        (PreferPassEvaluator(), PassAction),
        (PreferMarkedEvaluator(), (SemanticBoardMove, SemanticDropMove)),
    ):
        session = GameSession(compiled)
        player = AlphaBetaPlayer(
            compiled,
            evaluator_override=evaluator,
            use_disk_cache=False,
        )
        # Native semantic legality rejects coordinate-free PassAction; the
        # default AlphaBeta caller must retain its Core route for this ruleset.
        assert player.use_native_semantic_legality
        assert player.native_legality_provider is None
        decision = player.choose_action(session, limits)
        assert decision.completed_depth == 1
        assert isinstance(decision.action, expected_type)
        assert decision.action in core_root
        assert decision.principal_variation
        assert decision.principal_variation[0] == decision.action
        assert apply_action(session.state, decision.action, compiled) == apply_action(
            session.state, decision.principal_variation[0], compiled
        )
        session.submit(decision.action)
        record = deserialize_game_record(serialize_game_record(session.to_record()))
        replayed = GameSession.replay(compiled, record)
        assert replayed.state == session.state
        assert replayed.result == session.result


def test_python_search_backend_preserves_generated_pass_action_and_snapshot() -> None:
    _, compiled = _compiled_semantic_temp()
    session = GameSession(compiled)
    before = session.state

    class PreferPassEvaluator:
        def evaluate(self, state):
            return -10_000 if state.position.board == before.position.board else 10_000

    player = AlphaBetaPlayer(
        compiled,
        evaluator_override=PreferPassEvaluator(),
        use_disk_cache=False,
    )
    assert player.native_legality_provider is None
    backend = PythonSearchBackend(player)
    snapshot = SearchSnapshot(
        session=session,
        limits=SearchLimits(
            max_depth=1,
            max_nodes=10_000,
            max_time_seconds=5,
            quiescence_max_depth=0,
            quiescence_hard_max_depth=0,
        ),
        ruleset_fingerprint=compiled.ruleset_fingerprint,
        root_key="pass-enabled-root",
        generation=0,
    )

    decision = backend.search(snapshot)

    assert decision.action == PassAction()
    assert decision.principal_variation[0] == PassAction()
    assert decision.action in session.legal_actions()
    assert session.state is before


@pytest.mark.parametrize("side", [0, 1], ids=["owner-0", "owner-1"])
def test_semantic_pass_rejects_post_expiry_anchor_check(side: int) -> None:
    from generic_chess.core.semantic_executor import semantic_engine_for

    _, compiled = _compiled_semantic_temp()
    state = initial_state(compiled)
    width = state.position.board_shape.width
    height = state.position.board_shape.height
    board = [None] * state.position.board_shape.area
    if side == 0:
        board[width - 1] = Piece(0, "K", "K")
        board[(height - 1) * width] = Piece(1, "K", "K")
        board[(height - 1) * width + width - 1] = Piece(1, "R", "R")
    else:
        board[0] = Piece(0, "K", "K")
        board[(height - 1) * width + width - 1] = Piece(1, "K", "K")
        board[width - 1] = Piece(0, "R", "R")
    slot = next(slot for slot in compiled.ir.aux_slots if slot.value_kind == "bool")
    position = replace(
        state.position,
        board=tuple(board),
        side_to_move=side,
        aux_state=(((slot.slot_id, -1), 1),),
    )
    engine = semantic_engine_for(compiled)
    assert engine is not None
    assert not engine.in_check(position, side)
    after = engine.transition_pass(position)
    assert dict(after.aux_state)[(slot.slot_id, -1)] == slot.initial
    assert engine.in_check(after, side)

    checked_later = replace(state, position=position)
    assert PassAction() not in legal_actions(checked_later, compiled)
    with pytest.raises(IllegalActionError):
        apply_action(checked_later, PassAction(), compiled)
