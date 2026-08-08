"""Frozen specification for Phase 1.9B-3: Python bounded S4 post-action
probe (ADR-016).

Do not weaken, skip, or xfail these tests.  Until the B-3 implementation
lands, tests whose target behavior requires S4 execution fail with the
explicit fail-closed RuntimeError from ``SemanticEngine`` (EXPECTED_RED);
each test first asserts fixture validity and current capability state so a
red can be attributed to "S4 still fail-closed" and not to a broken
fixture, bad import, or test bug.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from generic_chess.core.actions import SemanticDropMove
from generic_chess.core.coordinates import Square
from generic_chess.core.errors import IllegalActionError
from generic_chess.core.movegen import legal_actions
from generic_chess.core.pieces import Piece
from generic_chess.core.position import GameState, Hands, Position
from generic_chess.core.semantic_executor import SemanticEngine
from generic_chess.core.terminal import TerminalResult, TerminalStatus
from generic_chess.core.transition import apply_action, initial_state, legal_successors
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.ir import MAX_PROBE_STRATUM
from generic_chess.rules.schema import RulePostcondition
from generic_chess.rules.validation import RuleValidationError

from phase19b3_s4_fixtures import (
    forbidden_no_reply_drop_ruleset,
    forbidden_no_reply_drop_position,
    full_child_state_ruleset,
    full_child_state_position,
    multiple_replies_ruleset,
    multiple_replies_position,
    nested_s4_option_b_ruleset,
    nested_s4_option_b_position,
    opponent_checked_mover_checked_position,
    opponent_checked_perspective_ruleset,
    opponent_checked_reply_checked_position,
    restricted_finish_ruleset,
    restricted_finish_position,
)
from rule_semantics_ir_fixtures import (
    cannon_ruleset,
    castling_ruleset,
    en_passant_ruleset,
    nifu_ruleset,
)


def _compile(ruleset):
    return compile_semantic_ruleset(ruleset)


def _idx(support, file, rank):
    return rank * support.board_size + file


def _position(support, entries, side=0, hands=None, aux_state=()):
    board = [None] * (support.board_size * support.board_size)
    for file, rank, piece in entries:
        board[_idx(support, file, rank)] = piece
    if hands is None:
        hands = (Hands.empty(), Hands.empty())
    return Position(
        board=tuple(board),
        hands=hands,
        side_to_move=side,
        ruleset_fingerprint=support.ruleset_fingerprint,
        aux_state=aux_state,
    )


def _forbidden_drop_pattern(compiled):
    return next(p for p in compiled.ir.patterns if p.postconditions)


# ------------------------------------------------------------------ SPEC-01


def test_spec01_no_reply_checking_action_rejected():
    compiled = _compile(forbidden_no_reply_drop_ruleset())
    pattern = _forbidden_drop_pattern(compiled)
    assert [p.kind for p in pattern.postconditions] == [
        "opponent_checked",
        "no_legal_reply",
    ]
    assert pattern.postconditions[1].max_stratum == MAX_PROBE_STRATUM
    assert compiled.ir.capabilities.contains_postcondition is True
    # EXPECTED_RED until B-3: engine construction fails closed on S4.
    engine = SemanticEngine(compiled)
    pos = forbidden_no_reply_drop_position(engine.support, cage=True)
    actions = engine.legal_actions(pos)
    pattern_id = "sem_00_drop_no_legal_reply_forbidden"
    forbidden_target = _idx(engine.support, 7, 5)
    allowed_control_target = _idx(engine.support, 0, 1)
    pattern_actions = [a for a in actions if a.pattern_id == pattern_id]
    assert not [
        a for a in pattern_actions if a.target == forbidden_target
    ]
    assert [
        a for a in pattern_actions if a.target == allowed_control_target
    ]


# ------------------------------------------------------------------ SPEC-02


def test_spec02_checking_action_with_reply_remains_legal():
    compiled = _compile(forbidden_no_reply_drop_ruleset())
    pattern = _forbidden_drop_pattern(compiled)
    assert [p.kind for p in pattern.postconditions] == [
        "opponent_checked",
        "no_legal_reply",
    ]
    # EXPECTED_RED until B-3.
    engine = SemanticEngine(compiled)
    pos = forbidden_no_reply_drop_position(engine.support, cage=False)
    actions = engine.legal_actions(pos)
    checking_target = _idx(engine.support, 7, 5)
    assert [
        a
        for a in actions
        if a.pattern_id == "sem_00_drop_no_legal_reply_forbidden"
        and a.target == checking_target
    ]


# ------------------------------------------------------------------ SPEC-03


def test_spec03_opponent_checked_binds_to_reply_side():
    compiled = _compile(opponent_checked_perspective_ruleset())
    assert compiled.ir.capabilities.contains_postcondition is True
    # EXPECTED_RED until B-3.
    engine = SemanticEngine(compiled)
    reply_checked = opponent_checked_reply_checked_position(engine.support)
    checking_target = _idx(engine.support, 2, 1)
    reply_checked_actions = [
        a
        for a in engine.legal_actions(reply_checked)
        if a.pattern_id == "sem_00_checking_restriction"
    ]
    assert not [
        a for a in reply_checked_actions if a.target == checking_target
    ]
    mover_checked = opponent_checked_mover_checked_position(engine.support)
    mover_checked_actions = [
        a
        for a in engine.legal_actions(mover_checked)
        if a.pattern_id == "sem_00_checking_restriction"
    ]
    assert [
        a for a in mover_checked_actions if a.target == checking_target
    ]


# ------------------------------------------------------------------ SPEC-04


def test_spec04_nested_s4_disabled_option_b():
    compiled = _compile(nested_s4_option_b_ruleset())
    assert compiled.ir.capabilities.contains_postcondition is True
    # EXPECTED_RED until B-3.
    engine = SemanticEngine(compiled)
    pos = nested_s4_option_b_position(engine.support)
    actions = engine.legal_actions(pos)
    # The opponent's only S0-S3 reply is itself S4-forbidden; Option B still
    # counts it as a reply, so the parent action stays legal.
    assert [
        a for a in actions if a.pattern_id == "sem_00_parent_no_reply"
    ]


# ------------------------------------------------------------------ SPEC-05


def test_spec05_non_drop_restricted_finish():
    compiled = _compile(restricted_finish_ruleset())
    pattern = _forbidden_drop_pattern(compiled)
    assert [p.kind for p in pattern.postconditions] == [
        "opponent_checked",
        "no_legal_reply",
    ]
    assert "P" not in pattern.type_ids  # board capture, not a drop
    # EXPECTED_RED until B-3.
    engine = SemanticEngine(compiled)
    caged = restricted_finish_position(engine.support, cage=True)
    assert not [
        a
        for a in engine.legal_actions(caged)
        if a.pattern_id == "sem_00_capture_no_legal_reply_forbidden"
    ]
    open_pos = restricted_finish_position(engine.support, cage=False)
    assert [
        a
        for a in engine.legal_actions(open_pos)
        if a.pattern_id == "sem_00_capture_no_legal_reply_forbidden"
    ]


# ------------------------------------------------------------------ SPEC-06


def test_spec06_probe_uses_full_child_state():
    compiled = _compile(full_child_state_ruleset())
    assert compiled.ir.capabilities.contains_postcondition is True
    assert any(s.value_kind == "bool" for s in compiled.ir.aux_slots)
    # EXPECTED_RED until B-3.
    engine = SemanticEngine(compiled)
    pos = full_child_state_position(engine.support)
    parents = [
        a
        for a in engine.legal_actions(pos)
        if a.pattern_id == "sem_00_parent_sets_flag"
    ]
    assert parents
    child = engine.apply(pos, parents[0])
    slot = next(s for s in engine.ir.aux_slots if s.value_kind == "bool")
    # The probe must observe the flag set by the parent transition; without
    # the real child aux state the only reply would vanish.
    assert dict(child.aux_state)[(slot.slot_id, -1)] == 1


# ------------------------------------------------------------------ SPEC-07


def test_spec07_s4_action_excluded_from_public_membership():
    from generic_chess.core.keys import semantic_position_key

    compiled = _compile(forbidden_no_reply_drop_ruleset())
    pattern = _forbidden_drop_pattern(compiled)
    drop_gid = pattern.geometry_ids[0]
    assert compiled.ir.capabilities.contains_postcondition is True
    # EXPECTED_RED until B-3: initial_state already fails closed on S4.
    _ = initial_state(compiled)
    pos = forbidden_no_reply_drop_position(compiled.support, cage=True)
    key = semantic_position_key(pos, compiled.support, compiled.ir.aux_slots)
    state = GameState(
        position=pos,
        ply_count=0,
        repetition_counts=((key, 1),),
        terminal_status=TerminalResult(TerminalStatus.ONGOING),
    )
    actions = legal_actions(state, compiled)
    forbidden_square = Square(7, 5)
    allowed_control_square = Square(0, 1)
    assert not [
        a
        for a in actions
        if getattr(a, "pattern_id", "") == pattern.pattern_id
        and getattr(a, "to_square", None) == forbidden_square
    ]
    assert [
        a
        for a in actions
        if getattr(a, "pattern_id", "") == pattern.pattern_id
        and getattr(a, "to_square", None) == allowed_control_square
    ]
    successors = legal_successors(state, compiled)
    assert not [
        a
        for a, _ in successors
        if getattr(a, "pattern_id", "") == pattern.pattern_id
        and getattr(a, "to_square", None) == forbidden_square
    ]
    assert [
        a
        for a, _ in successors
        if getattr(a, "pattern_id", "") == pattern.pattern_id
        and getattr(a, "to_square", None) == allowed_control_square
    ]
    with pytest.raises(IllegalActionError):
        apply_action(
            state,
            SemanticDropMove(
                pattern_id=pattern.pattern_id,
                geometry_id=drop_gid,
                base_type_id="P",
                to_square=Square(7, 5),
            ),
            compiled,
        )


# ------------------------------------------------------------------ SPEC-08


def test_spec08_s0s3_unchanged():
    """Cannon / Castling / En Passant / Nifu / legacy differential must be
    unchanged by the S4 layer (green at B-2; must stay green)."""
    from generic_chess.ai.benchmark.audit_suite import (
        build_compiled,
        standard_ruleset_specs,
    )
    from generic_chess.core.movegen import legal_actions_from_position
    from generic_chess.rules.compiler import (
        _build_semantic_support,
        lower_legacy_to_ir,
    )
    from generic_chess.rules.ir import CompiledSemanticRuleset

    # Cannon
    engine = SemanticEngine(_compile(cannon_ruleset()))
    s = engine.support

    def cannon_pos(enemy_file, screen=True, extra_screens=()):
        entries = [
            (0, 0, Piece(0, "C", "C")),
            (s.board_size - 1, s.board_size - 1, Piece(1, "K", "K")),
        ]
        if screen:
            entries.append((1, 0, Piece(1, "P", "P")))
        for f in extra_screens:
            entries.append((f, 0, Piece(1, "P", "P")))
        if enemy_file:
            entries.append((enemy_file, 0, Piece(1, "P", "P")))
        return _position(s, entries)

    p0 = cannon_pos(enemy_file=1, screen=False)
    assert [a for a in engine.legal_actions(p0) if a.pattern_id == "sem_00_cannon_quiet"]
    assert not [
        a
        for a in engine.legal_actions(p0)
        if a.pattern_id == "sem_01_cannon_capture" and a.target == _idx(s, 1, 0)
    ]
    p1 = cannon_pos(enemy_file=2, screen=True)
    assert [
        a
        for a in engine.legal_actions(p1)
        if a.pattern_id == "sem_01_cannon_capture" and a.target == _idx(s, 2, 0)
    ]
    p2 = cannon_pos(enemy_file=4, screen=True, extra_screens=(2,))
    assert not [
        a
        for a in engine.legal_actions(p2)
        if a.pattern_id == "sem_01_cannon_capture" and a.target == _idx(s, 4, 0)
    ]

    # Castling: per-owner rights + ordinary king movement preserved.
    engine = SemanticEngine(_compile(castling_ruleset()))
    s = engine.support
    n = s.board_size
    pos = _position(
        s,
        [
            (4, 0, Piece(0, "K", "K")),
            (7, 0, Piece(0, "R", "R")),
            (3, n - 1, Piece(1, "K", "K")),
            (0, n - 1, Piece(1, "R", "R")),
        ],
        side=0,
    )
    castle = [
        a
        for a in engine.legal_actions(pos)
        if a.pattern_id == "sem_00_king_side_shift"
    ]
    assert castle
    child = engine.apply(pos, castle[0])
    assert dict(child.aux_state)[(0, 0)] == 0
    assert [
        a
        for a in engine.legal_actions(child)
        if a.pattern_id == "sem_00_king_side_shift"
        and a.source == _idx(s, 3, n - 1)
    ]

    # En passant: token lifecycle + off-target capture.
    engine = SemanticEngine(_compile(en_passant_ruleset()))
    s = engine.support
    pos = _position(
        s,
        [
            (4, 1, Piece(0, "P", "P")),
            (3, 3, Piece(1, "P", "P")),
            (4, 0, Piece(0, "K", "K")),
            (3, 7, Piece(1, "K", "K")),
        ],
        side=0,
    )
    double = [
        a
        for a in engine.legal_actions(pos)
        if a.pattern_id == "sem_00_double_step_creates_token"
    ]
    assert double
    child = engine.apply(pos, double[0])
    token = next(x for x in engine.ir.aux_slots if x.value_kind == "square_or_none")
    assert dict(child.aux_state)[(token.slot_id, -1)] == (4, 2)
    assert [
        a
        for a in engine.legal_actions(child)
        if a.pattern_id.startswith("sem_") and "capture" in a.pattern_id
    ]

    # Nifu: same-file unpromoted P blocks the drop.
    engine = SemanticEngine(_compile(nifu_ruleset()))
    s = engine.support
    board = [None] * (s.board_size * s.board_size)
    board[_idx(s, 4, 0)] = Piece(0, "P", "P")
    pos = Position(
        board=tuple(board),
        hands=(Hands((("P", 1),)), Hands.empty()),
        side_to_move=0,
        ruleset_fingerprint=s.ruleset_fingerprint,
        aux_state=(),
    )
    drops = [
        a
        for a in engine.legal_actions(pos)
        if a.pattern_id == "sem_00_drop_file_occupancy_guard"
    ]
    assert not [d for d in drops if d.target % s.board_size == 4]
    assert [d for d in drops if d.target % s.board_size == 3]

    # Legacy differential (compact): semantic engine matches legacy actions
    # for the initial state and two deterministic plies.
    specs = {spec.fixture_id: spec for spec in standard_ruleset_specs()}
    legacy = build_compiled(specs["gen_classic_like_4_101"])
    ir = lower_legacy_to_ir(legacy)
    semantic = CompiledSemanticRuleset(
        ir=replace(
            ir,
            capabilities=replace(ir.capabilities, new_ir_core_executable=True),
        ),
        _legacy_compiled=legacy,
        support=_build_semantic_support(legacy),
    )
    engine = SemanticEngine(semantic)
    state = initial_state(legacy)

    def legacy_list(position):
        from generic_chess.core.actions import BoardMove, DropMove

        out = []
        for action in legal_actions_from_position(position, legacy):
            if isinstance(action, BoardMove):
                out.append(
                    (
                        "board",
                        action.from_square.file,
                        action.from_square.rank,
                        action.to_square.file,
                        action.to_square.rank,
                        action.promotion_target_id or "",
                    )
                )
            else:
                out.append(
                    ("drop", action.base_type_id, action.to_square.file, action.to_square.rank)
                )
        return sorted(out)

    def semantic_list(position):
        from generic_chess.core.coordinates import index_to_square

        out = []
        for action in engine.legal_actions(position):
            if action.source is None:
                sq = index_to_square(action.target, engine.support.board_size)
                out.append(("drop", action.actor_type, sq.file, sq.rank))
            else:
                f = index_to_square(action.source, engine.support.board_size)
                t = index_to_square(action.target, engine.support.board_size)
                out.append(
                    (
                        "board",
                        f.file,
                        f.rank,
                        t.file,
                        t.rank,
                        action.promotion_target_id or "",
                    )
                )
        return sorted(out)

    import random

    rng = random.Random(7)
    for _ in range(3):
        assert legacy_list(state.position) == semantic_list(state.position)
        legal = legal_actions_from_position(state.position, legacy)
        if not legal:
            break
        action = sorted(legal, key=str)[rng.randrange(len(legal))]
        state = apply_action(state, action, legacy)


# ------------------------------------------------------------------ SPEC-09


def test_spec09a_unsupported_probe_fails_closed():
    base = forbidden_no_reply_drop_ruleset()
    bad_stratum = replace(
        base,
        semantic_actions=(
            replace(
                base.semantic_actions[0],
                postconditions=(RulePostcondition("no_legal_reply", max_stratum="S4"),),
            ),
        ),
    )
    with pytest.raises(RuleValidationError):
        compile_semantic_ruleset(bad_stratum)
    bad_kind = replace(
        base,
        semantic_actions=(
            replace(
                base.semantic_actions[0],
                postconditions=(RulePostcondition("mate", max_stratum="S3"),),
            ),
        ),
    )
    with pytest.raises(RuleValidationError):
        compile_semantic_ruleset(bad_kind)


def test_spec09b_capability_transition_for_supported_s4():
    compiled = _compile(forbidden_no_reply_drop_ruleset())
    assert compiled.ir.capabilities.contains_postcondition is True
    # EXPECTED_RED until B-3: currently still fail-closed by capability.
    assert compiled.ir.capabilities.new_ir_core_executable is True, (
        "B-3 target: a supported S0-S4 ruleset must flip new_ir_core_executable"
    )


# ------------------------------------------------------------------ SPEC-10


def test_spec10_probe_never_enters_s5(monkeypatch):
    import generic_chess.core.terminal as terminal_mod

    from generic_chess.core.semantic_executor import SemanticEngine as EngineCls

    def _boom(*_args, **_kwargs):
        raise AssertionError("S5 terminal/repetition/max-ply consulted by S4 probe")

    monkeypatch.setattr(terminal_mod, "terminal_result", _boom)
    monkeypatch.setattr(EngineCls, "terminal_result", _boom)
    compiled = _compile(forbidden_no_reply_drop_ruleset())
    assert compiled.ir.capabilities.contains_postcondition is True
    # EXPECTED_RED until B-3.
    engine = SemanticEngine(compiled)
    pos = forbidden_no_reply_drop_position(engine.support, cage=True)
    engine.legal_actions(pos)


# ------------------------------------------------------------------ SPEC-11


def test_spec11_early_exit_contract():
    compiled = _compile(multiple_replies_ruleset())
    assert compiled.ir.capabilities.contains_postcondition is True
    # EXPECTED_RED until B-3.  Early exit is a MUST (ADR-016 section 10);
    # it is not frozen as a brittle source-shape test.
    engine = SemanticEngine(compiled)
    pos = multiple_replies_position(engine.support)
    actions = engine.legal_actions(pos)
    assert [
        a for a in actions if a.pattern_id == "sem_00_parent_no_reply"
    ]
