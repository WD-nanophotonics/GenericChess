"""Phase 1.9B-3 frozen-specification fixtures (S4 bounded post-action probe).

These builders express generic ``opponent_checked`` /
``no_legal_reply(max_stratum=S3)`` patterns for the S4 specification tests.
No game-name semantics appear in the patterns; ``uchifuzume`` / restricted
finish are only exercised as generic fixtures.
"""

from __future__ import annotations

from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.rules.schema import (
    RuleActionEffect,
    RuleAuxState,
    RuleGeometrySpec,
    RuleInvariant,
    RulePostcondition,
    RuleReplaceSelector,
    RuleSemanticAction,
    RuleSlotGuard,
    RuleSquareRef,
    RuleTypeRef,
)

from rule_semantics_ir_fixtures import _king_type, _semantic_ruleset


def _ref(kind, **kwargs):
    return RuleSquareRef(kind=kind, **kwargs)


def _own_anchor():
    return (RuleInvariant("own_anchor_safe"),)


def _forbidden_reply_postconditions():
    return (
        RulePostcondition("opponent_checked"),
        RulePostcondition("no_legal_reply", max_stratum="S3"),
    )


def _no_reply_postcondition():
    return (RulePostcondition("no_legal_reply", max_stratum="S3"),)


def _replace_quiet(type_id: str) -> RuleReplaceSelector:
    return RuleReplaceSelector(
        type_ids=(type_id,),
        action_family="board",
        target_relation="empty",
        geometry_kind="ray",
        replace_all_matching=True,
    )


def _quiet_action(
    name: str,
    type_id: str,
    direction,
    *,
    postconditions,
    slot_guards=(),
    effects=None,
    replace=True,
    invariants=None,
) -> RuleSemanticAction:
    """One generic quiet ray move with optional S4 postconditions/guards."""
    action = RuleSemanticAction(
        name=name,
        type_ids=(type_id,),
        geometry=RuleGeometrySpec(kind="legacy_atoms", atom_kind="ray"),
        target_relation="empty",
        composition="replace_legacy" if replace else "augment",
        replace_selector=_replace_quiet(type_id) if replace else None,
        path_constraints=(),
        slot_guards=slot_guards,
        effects=effects
        or (
            RuleActionEffect(
                "move",
                from_ref=_ref("source"),
                to_ref=_ref("target"),
            ),
        ),
        invariants=_own_anchor() if invariants is None else invariants,
        postconditions=postconditions,
    )
    return action


# --------------------------------------------------------------------- types


def _leaper(tid: str, offset) -> PieceType:
    return PieceType(tid, tid, (LeapAtom(offset),))


def _rayer(tid: str, direction) -> PieceType:
    from generic_chess.core.movement import RayAtom

    return PieceType(tid, tid, (RayAtom(direction),))


def _blocker_types():
    """Reusable immobile blocker types: every single leap points at an
    occupied square / off-board edge in the SPEC fixtures."""
    return (
        _leaper("EU", (0, 1)),
        _leaper("ER", (1, 0)),
        _leaper("EL", (-1, 0)),
    )


# ------------------------------------------------------------------ helpers


def _empty_board(support):
    return [None] * (support.board_size * support.board_size)


def _idx(support, file, rank):
    return rank * support.board_size + file


def _put(board, support, file, rank, piece):
    idx = _idx(support, file, rank)
    assert board[idx] is None, (file, rank)
    board[idx] = piece


def _board(support, entries):
    board = _empty_board(support)
    for file, rank, piece in entries:
        _put(board, support, file, rank, piece)
    return tuple(board)


def _rows(support, board):
    n = support.board_size
    return tuple(
        tuple(board[r * n + f] for f in range(n)) for r in range(n)
    )


def _position(support, entries, side=0, hands=None, aux_state=()):
    from generic_chess.core.position import Hands, Position

    board = _board(support, entries)
    if hands is None:
        hands = (Hands.empty(), Hands.empty())
    return Position(
        board=board,
        hands=hands,
        side_to_move=side,
        ruleset_fingerprint=support.ruleset_fingerprint,
        aux_state=aux_state,
    )


# ================================================================ SPEC-03


def opponent_checked_perspective_ruleset():
    """A quiet ray move whose legality is restricted by ``opponent_checked``
    only (no no_legal_reply, no own-anchor invariant) so the perspective of
    the postcondition can be pinned to the *reply side*."""
    a = _rayer("A", (1, 0))
    er = _leaper("ER", (1, 0))
    action = _quiet_action(
        "checking_restriction",
        "A",
        (1, 0),
        postconditions=(RulePostcondition("opponent_checked"),),
        invariants=(),
    )
    return _semantic_ruleset((_king_type(), a, er), (action,), n=5)


def opponent_checked_reply_checked_position(support):
    """Mover safe, reply-side anchor checked after the move."""
    return _position(
        support,
        [
            (0, 0, Piece(0, "K", "K")),
            (0, 1, Piece(0, "A", "A")),
            (3, 1, Piece(1, "K", "K")),
        ],
        side=0,
    )


def opponent_checked_mover_checked_position(support):
    """Mover-side anchor checked after the move, reply-side anchor safe:
    a wrong parent-side perspective would evaluate the postcondition true."""
    return _position(
        support,
        [
            (0, 0, Piece(0, "K", "K")),
            (0, 1, Piece(0, "A", "A")),
            (1, 0, Piece(1, "ER", "ER")),  # owner-1 rotation -> attacks (0,0)
            (4, 4, Piece(1, "K", "K")),
        ],
        side=0,
    )


# ============================================================ SPEC-04 cage


def nested_s4_option_b_ruleset():
    """Parent A quiet move and reply B quiet move both carry
    ``no_legal_reply(S3)``.  Under Option B the parent's probe counts the
    (itself S4-forbidden) reply, so the parent action stays legal."""
    a = _rayer("A", (1, 0))
    b = _rayer("B", (1, 0))
    eu, er, el = _blocker_types()
    parent = _quiet_action(
        "parent_no_reply",
        "A",
        (1, 0),
        postconditions=_no_reply_postcondition(),
    )
    reply = _quiet_action(
        "reply_no_reply",
        "B",
        (1, 0),
        postconditions=_no_reply_postcondition(),
    )
    return _semantic_ruleset(
        (_king_type(), a, b, eu, er, el),
        (parent, reply),
        n=5,
    )


def nested_s4_option_b_position(support):
    """A's only relevant move gives B exactly one S3 reply (B's own
    no-reply move); that reply is itself S4-forbidden, which Option B must
    ignore inside the parent probe."""
    return _position(
        support,
        [
            # A side
            (0, 0, Piece(0, "K", "K")),
            (0, 1, Piece(0, "ER", "ER")),
            (1, 0, Piece(0, "EU", "EU")),
            (1, 1, Piece(0, "EL", "EL")),
            (2, 0, Piece(0, "A", "A")),
            (4, 0, Piece(0, "EL", "EL")),
            # B side
            (1, 3, Piece(1, "B", "B")),
            (4, 4, Piece(1, "K", "K")),
            # K1 cage: evasions occupied and protected
            (3, 2, Piece(0, "EU", "EU")),
            (3, 3, Piece(0, "EU", "EU")),
            (3, 4, Piece(0, "EU", "EU")),
            (2, 4, Piece(0, "ER", "ER")),
            (4, 2, Piece(0, "EU", "EU")),
            (4, 3, Piece(0, "ER", "ER")),
        ],
        side=0,
    )


# ============================================================ SPEC-06 aux


def full_child_state_ruleset():
    """Parent sets a global flag during transition; the reply's slot guard
    depends on it, proving the probe consumes the real child aux state."""
    a = _rayer("A", (1, 0))
    b = _rayer("B", (1, 0))
    eu, er, el = _blocker_types()
    flag = RuleAuxState("flag", "bool", "global", "persistent", 0)
    parent = RuleSemanticAction(
        name="parent_sets_flag",
        type_ids=("A",),
        geometry=RuleGeometrySpec(kind="legacy_atoms", atom_kind="ray"),
        target_relation="empty",
        composition="replace_legacy",
        replace_selector=_replace_quiet("A"),
        aux_state=(flag,),
        effects=(
            RuleActionEffect(
                "move",
                from_ref=_ref("source"),
                to_ref=_ref("target"),
            ),
            RuleActionEffect("set_bool", slot_name="flag", value=1),
        ),
        invariants=_own_anchor(),
        postconditions=_no_reply_postcondition(),
    )
    reply = _quiet_action(
        "reply_requires_flag",
        "B",
        (1, 0),
        postconditions=(),
        slot_guards=(RuleSlotGuard("flag", comparison="eq", value=1),),
    )
    return _semantic_ruleset(
        (_king_type(), a, b, eu, er, el),
        (parent, reply),
        n=5,
    )


def full_child_state_position(support):
    return _position(
        support,
        [
            (0, 0, Piece(0, "K", "K")),
            (2, 0, Piece(0, "A", "A")),
            (1, 3, Piece(1, "B", "B")),
            (4, 4, Piece(1, "K", "K")),
            (3, 2, Piece(0, "EU", "EU")),
            (3, 3, Piece(0, "EU", "EU")),
            (3, 4, Piece(0, "EU", "EU")),
            (2, 4, Piece(0, "ER", "ER")),
            (4, 2, Piece(0, "EU", "EU")),
            (4, 3, Piece(0, "ER", "ER")),
        ],
        side=0,
    )


# ============================================================ SPEC-11 many


def multiple_replies_ruleset():
    """Parent action with ``no_legal_reply`` where the reply side has several
    S3 replies: the candidate must be allowed and the existence scan may stop
    at the first reply (early-exit is a MUST, frozen in ADR-016)."""
    a = _rayer("A", (1, 0))
    b = _rayer("B", (1, 0))
    parent = _quiet_action(
        "parent_no_reply",
        "A",
        (1, 0),
        postconditions=_no_reply_postcondition(),
    )
    # The B quiet pattern is left as legacy (no S4); B simply has replies.
    return _semantic_ruleset((_king_type(), a, b), (parent,), n=5)


def multiple_replies_position(support):
    return _position(
        support,
        [
            (0, 0, Piece(0, "K", "K")),
            (0, 1, Piece(0, "A", "A")),
            (4, 4, Piece(1, "K", "K")),
            (1, 3, Piece(1, "B", "B")),
        ],
        side=0,
    )


# ============================================================ SPEC-05 board


def restricted_finish_ruleset():
    """Generic board capture with ``opponent_checked + no_legal_reply(S3)``:
    a no-reply checking capture is forbidden.  Proves the S4 primitive is not
    drop-specific (generic restricted finish)."""
    from generic_chess.core.movement import RayAtom

    r = _rayer("R", (0, 1))
    eu, er, el = _blocker_types()
    action = RuleSemanticAction(
        name="capture_no_legal_reply_forbidden",
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
        effects=(
            RuleActionEffect(
                "remove",
                square_ref=_ref("target"),
                piece_owner="opponent",
                piece_type_ref=RuleTypeRef(kind="any"),
                disposition="capture_to_hand",
            ),
            RuleActionEffect(
                "move",
                from_ref=_ref("source"),
                to_ref=_ref("target"),
            ),
        ),
        invariants=_own_anchor(),
        postconditions=_forbidden_reply_postconditions(),
    )
    return _semantic_ruleset((_king_type(), r, eu, er, el), (action,), n=8)


def restricted_finish_position(support, cage=True):
    entries = [
        (0, 0, Piece(0, "K", "K")),
        (7, 5, Piece(0, "R", "R")),
        (7, 6, Piece(1, "EU", "EU")),  # capture victim, then checks K1
        (7, 7, Piece(1, "K", "K")),
    ]
    if cage:
        entries += [
            (6, 6, Piece(0, "ER", "ER")),  # protects R after landing at (7,6)
            (5, 6, Piece(0, "ER", "ER")),  # protects (6,6)
            (6, 7, Piece(0, "EU", "EU")),
            (5, 7, Piece(0, "ER", "ER")),  # protects (6,7)
        ]
    return _position(support, entries, side=0)


# ============================================================ SPEC-01/02 drop


def forbidden_no_reply_drop_ruleset():
    """Generic drop pattern with ``opponent_checked + no_legal_reply(S3)``:
    a no-reply checking drop is forbidden (uchifuzume-shaped restriction,
    expressed with generic primitives only)."""
    from generic_chess.core.movement import RayAtom

    pawn = _rayer("P", (0, 1))
    eu, er, el = _blocker_types()
    action = RuleSemanticAction(
        name="drop_no_legal_reply_forbidden",
        type_ids=("P",),
        geometry=RuleGeometrySpec(kind="drop"),
        target_relation="empty",
        composition="replace_legacy",
        replace_selector=RuleReplaceSelector(
            type_ids=("P",),
            action_family="drop",
            target_relation="empty",
        ),
        effects=(
            RuleActionEffect(
                "remove_from_hand",
                piece_type_ref=RuleTypeRef(kind="action_base"),
            ),
            RuleActionEffect(
                "place",
                to_ref=_ref("target"),
                piece_type_ref=RuleTypeRef(kind="action_base"),
            ),
        ),
        invariants=_own_anchor(),
        postconditions=_forbidden_reply_postconditions(),
    )
    return _semantic_ruleset(
        (_king_type(), pawn, eu, er, el),
        (action,),
        n=8,
        drop_all_true=("P",),
    )


def forbidden_no_reply_drop_position(support, cage=True):
    """A-side has a P in hand; dropping it gives check to the caged enemy
    king.  With ``cage=True`` the enemy has no reply; with ``cage=False`` it
    has evasion replies."""
    from generic_chess.core.position import Hands

    entries = [
        (0, 0, Piece(0, "K", "K")),
        (7, 7, Piece(1, "K", "K")),
    ]
    if cage:
        entries += [
            (6, 6, Piece(0, "EU", "EU")),
            (6, 7, Piece(0, "EU", "EU")),
            (5, 6, Piece(0, "ER", "ER")),
            (5, 7, Piece(0, "ER", "ER")),
        ]
    return _position(
        support,
        entries,
        side=0,
        hands=(Hands((("P", 1),)), Hands.empty()),
    )
