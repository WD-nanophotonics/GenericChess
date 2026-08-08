"""Focused implementation hardening for Phase 1.9B-3 (not specification).

Covers architecture hazards that the frozen SPEC-01..11 suite does not
observe directly: S4-bearing capture patterns participating in S2, the
conjunction-vs-per-item distinction, source-order independence and cheap-first
short circuit, reply early exit, nested S4 disabled, and the exact S3 child
reuse for S4.
"""

from __future__ import annotations

from dataclasses import replace

from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.position import Hands, Position
from generic_chess.core.semantic_executor import SemanticEngine
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.schema import (
    RuleActionEffect,
    RuleGeometrySpec,
    RuleInvariant,
    RulePostcondition,
    RuleReplaceSelector,
    RuleSemanticAction,
    RuleSquareRef,
    RuleTypeRef,
)

from phase19b3_s4_fixtures import (
    _idx,
    _position,
    forbidden_no_reply_drop_ruleset,
    full_child_state_ruleset,
    full_child_state_position,
    multiple_replies_ruleset,
    multiple_replies_position,
    nested_s4_option_b_ruleset,
    nested_s4_option_b_position,
    restricted_finish_ruleset,
)
from rule_semantics_ir_fixtures import _king_type, _semantic_ruleset


def _engine(builder):
    return SemanticEngine(compile_semantic_ruleset(builder()))


def _forbidden_drop_pattern(compiled):
    return next(p for p in compiled.ir.patterns if p.postconditions)


# ------------------------------------------------------- S2 participation


def _s4_leap_capture_ruleset():
    """A leap capture pattern carrying S4 postconditions.  Its S0/S1 capture
    eligibility must still contribute to pseudo-attack."""
    a = PieceType("A", "A", (LeapAtom((1, 0)),))
    action = RuleSemanticAction(
        name="leap_capture_no_reply_forbidden",
        type_ids=("A",),
        geometry=RuleGeometrySpec(kind="legacy_atoms", atom_kind="leap"),
        target_relation="enemy",
        composition="replace_legacy",
        replace_selector=RuleReplaceSelector(
            type_ids=("A",),
            action_family="board",
            target_relation="enemy",
            geometry_kind="leap",
            replace_all_matching=True,
        ),
        effects=(
            RuleActionEffect(
                "remove",
                square_ref=RuleSquareRef("target"),
                piece_owner="opponent",
                piece_type_ref=RuleTypeRef("any"),
                disposition="capture_to_hand",
            ),
            RuleActionEffect(
                "move",
                from_ref=RuleSquareRef("source"),
                to_ref=RuleSquareRef("target"),
            ),
        ),
        invariants=(RuleInvariant("own_anchor_safe"),),
        postconditions=(
            RulePostcondition("opponent_checked"),
            RulePostcondition("no_legal_reply", max_stratum="S3"),
        ),
    )
    return _semantic_ruleset((_king_type(), a), (action,), n=5)


def test_s4_bearing_capture_contributes_to_s2_pseudo_attack(monkeypatch):
    engine = _engine(_s4_leap_capture_ruleset)
    s = engine.support
    pos = _position(
        s,
        [
            (0, 0, Piece(0, "A", "A")),
            (1, 0, Piece(1, "K", "K")),  # enemy anchor, capture target
            (4, 4, Piece(0, "K", "K")),
        ],
        side=0,
    )
    target = _idx(s, 1, 0)
    assert engine.is_square_attacked(pos, target, 0) is True
    assert engine.in_check(pos, 1) is True
    # The anchor capture itself stays illegal (S3 remove rejects anchors).
    assert not [
        a
        for a in engine.legal_actions(pos)
        if a.pattern_id == "sem_00_leap_capture_no_reply_forbidden"
    ]

    # The attack must not evaluate S4 (nor S3 trial): make the S4 filter and
    # the probe hostile and confirm the attack still succeeds.
    def _boom(*_args, **_kwargs):
        raise AssertionError("S4 consulted during pseudo-attack")

    monkeypatch.setattr(engine, "_violates_postconditions", _boom)
    monkeypatch.setattr(engine, "_exists_s3_reply", _boom)
    assert engine.is_square_attacked(pos, target, 0) is True
    assert engine.in_check(pos, 1) is True


def test_s4_bearing_ray_capture_attacks_first_occupied_square():
    engine = _engine(restricted_finish_ruleset)
    s = engine.support
    pos = _position(
        s,
        [
            (0, 0, Piece(0, "K", "K")),
            (7, 5, Piece(0, "R", "R")),
            (7, 6, Piece(1, "EU", "EU")),
            (7, 7, Piece(1, "K", "K")),
        ],
        side=0,
    )
    assert engine.is_square_attacked(pos, _idx(s, 7, 6), 0) is True


# ------------------------------------------- conjunction / source order


def _drop_rulesets_both_orders():
    base = forbidden_no_reply_drop_ruleset()
    normal = base
    reversed_ = replace(
        base,
        semantic_actions=(
            replace(
                base.semantic_actions[0],
                postconditions=(
                    RulePostcondition("no_legal_reply", max_stratum="S3"),
                    RulePostcondition("opponent_checked"),
                ),
            ),
        ),
    )
    return (
        SemanticEngine(compile_semantic_ruleset(normal)),
        SemanticEngine(compile_semantic_ruleset(reversed_)),
    )


def _no_check_position(engine):
    """Enemy anchor on the back rank: no P drop can check it, so
    ``opponent_checked`` is false for every candidate and the reply probe
    must never run (cheap-first short circuit)."""
    s = engine.support
    return _position(
        s,
        [
            (0, 0, Piece(1, "K", "K")),
            (7, 7, Piece(0, "K", "K")),
        ],
        side=0,
        hands=(Hands((("P", 1),)), Hands.empty()),
    )


def test_conjunction_and_source_order_independent(monkeypatch):
    engine_a, engine_b = _drop_rulesets_both_orders()
    pattern_id = "sem_00_drop_no_legal_reply_forbidden"

    # Same position, reversed postcondition order: identical legal sets.
    pos_a = _no_check_position(engine_a)
    pos_b = _no_check_position(engine_b)
    drops_a = sorted(
        a.target for a in engine_a.legal_actions(pos_a) if a.pattern_id == pattern_id
    )
    drops_b = sorted(
        a.target for a in engine_b.legal_actions(pos_b) if a.pattern_id == pattern_id
    )
    assert drops_a and drops_a == drops_b

    # Cheap-first: opponent_checked false => the C4 probe never runs.
    calls = []

    def _count_probe(child):
        calls.append(child)
        return False

    monkeypatch.setattr(engine_a, "_exists_s3_reply", _count_probe)
    engine_a.legal_actions(pos_a)
    assert calls == [], "reply probe ran although opponent_checked was false"


def test_conjunction_rejects_only_violating_candidate():
    engine = _engine(forbidden_no_reply_drop_ruleset)
    s = engine.support
    pos = _position(
        s,
        [
            (0, 0, Piece(0, "K", "K")),
            (7, 7, Piece(1, "K", "K")),
            (6, 6, Piece(0, "EU", "EU")),
            (6, 7, Piece(0, "EU", "EU")),
            (5, 6, Piece(0, "ER", "ER")),
            (5, 7, Piece(0, "ER", "ER")),
        ],
        side=0,
        hands=(Hands((("P", 1),)), Hands.empty()),
    )
    pattern_id = "sem_00_drop_no_legal_reply_forbidden"
    drops = {
        a.target for a in engine.legal_actions(pos) if a.pattern_id == pattern_id
    }
    forbidden = _idx(s, 7, 5)
    control = _idx(s, 0, 1)
    assert forbidden not in drops  # C=True, E=False -> rejected
    assert control in drops  # C=False -> legal


# ------------------------------------------------------- early exit


def test_reply_probe_early_exits(monkeypatch):
    engine = _engine(multiple_replies_ruleset)
    s = engine.support
    pos = multiple_replies_position(s)
    parents = [
        a
        for a in engine.legal_actions(pos)
        if a.pattern_id == "sem_00_parent_no_reply"
    ]
    assert parents
    child = engine.apply(pos, parents[0])

    total_candidates = sum(
        1 for p in engine._patterns for _ in engine._iter_candidates(p, child)
    )
    trials = []
    orig_trial = engine._trial_child_if_s3_legal

    def _counting_trial(pattern, position, action, binding):
        trials.append(action)
        return orig_trial(pattern, position, action, binding)

    monkeypatch.setattr(engine, "_trial_child_if_s3_legal", _counting_trial)
    assert engine._exists_s3_reply(child) is True
    assert len(trials) < total_candidates, "probe did not stop at the first reply"


# ------------------------------------------------------- nested S4 disabled


def test_nested_s4_disabled_in_reply_probe(monkeypatch):
    engine = _engine(nested_s4_option_b_ruleset)
    s = engine.support
    pos = nested_s4_option_b_position(s)
    parents = [
        a for a in engine.legal_actions(pos) if a.pattern_id == "sem_00_parent_no_reply"
    ]
    assert parents  # Option B: the only reply is itself S4-forbidden but counts
    child = engine.apply(pos, parents[0])

    def _boom(*_args, **_kwargs):
        raise AssertionError("nested reply S4 evaluated inside probe")

    monkeypatch.setattr(engine, "_violates_postconditions", _boom)
    assert engine._exists_s3_reply(child) is True


# ------------------------------------------------------- exact S3 child


def test_exact_s3_child_reused_for_s4_single_transition(monkeypatch):
    from phase19b3_s4_fixtures import (
        opponent_checked_perspective_ruleset,
        opponent_checked_reply_checked_position,
    )

    engine = _engine(opponent_checked_perspective_ruleset)
    s = engine.support
    pos = opponent_checked_reply_checked_position(s)
    total_candidates = sum(
        1 for p in engine._patterns for _ in engine._iter_candidates(p, pos)
    )
    transitions = []
    orig_transition = engine._transition

    def _counting_transition(position, action, binding):
        transitions.append(action)
        return orig_transition(position, action, binding)

    monkeypatch.setattr(engine, "_transition", _counting_transition)
    engine.legal_actions(pos)
    # This pattern has no no_legal_reply: every S0-S1 candidate gets exactly
    # one S3 trial transition (no double parent transition before S4).
    assert len(transitions) == total_candidates


def test_s4_consumes_exact_aux_child(monkeypatch):
    engine = _engine(full_child_state_ruleset)
    s = engine.support
    pos = full_child_state_position(s)
    slot = next(x for x in engine.ir.aux_slots if x.value_kind == "bool")
    seen = []
    orig_violation = engine._violates_postconditions

    def _capture_violation(pattern, child_pos):
        seen.append(child_pos)
        return orig_violation(pattern, child_pos)

    monkeypatch.setattr(engine, "_violates_postconditions", _capture_violation)
    actions = engine.legal_actions(pos)
    assert [
        a for a in actions if a.pattern_id == "sem_00_parent_sets_flag"
    ]
    # S4 received the exact transition child carrying the aux flag.
    assert seen
    for child_pos in seen:
        if dict(child_pos.aux_state).get((slot.slot_id, -1)) == 1:
            break
    else:
        raise AssertionError("S4 never received the flag-bearing transition child")
