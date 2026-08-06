"""Phase 2B differential gate: Python fixed-depth minimax oracle vs the
native fixed-depth alpha-beta search."""

import json
from pathlib import Path

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.native_compat import NativeCompatibleEvaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.native.compiler import compile_native_evaluation, compile_native_rules
from generic_chess.native.reference import (
    canonical_pack,
    reference_fixed_depth_minimax,
)
from generic_chess.native.search import native_fixed_depth_search
from generic_chess.native.search import native_fixed_depth_search_state

from native_test_helpers import requires_native


def _setup(compiled, session):
    config = EvaluationConfig()
    profile = build_ruleset_profile(compiled, config)
    evaluator = NativeCompatibleEvaluator(compiled, profile, config)
    rules = compile_native_rules(compiled)
    eval_tables = compile_native_evaluation(rules, profile, config)
    return evaluator, rules, eval_tables


def _compare(compiled, session, rules, eval_tables, evaluator, depth, label):
    ref_score, ref_actions, ref_canonical, ref_pv, ref_nodes = (
        reference_fixed_depth_minimax(session.state, compiled, evaluator, depth)
    )
    native = native_fixed_depth_search(
        compiled, rules, eval_tables, session, depth
    )
    assert native.score == ref_score, (
        f"{label} depth {depth}: score {native.score} != {ref_score}"
    )
    assert native.action == ref_canonical, (
        f"{label} depth {depth}: best action {native.action} != {ref_canonical}"
    )
    if ref_canonical is not None:
        packed = canonical_pack(compiled, session.state, native.action)
        set_packed = {
            canonical_pack(compiled, session.state, a) for a in ref_actions
        }
        assert packed == min(set_packed), (
            f"{label} depth {depth}: action not canonical minimum"
        )
    if native.action is not None:
        assert native.principal_variation
        assert native.principal_variation[0] == native.action
    return ref_score, native


@requires_native
def test_corpus_search_differential():
    from generic_chess.ai.benchmark.audit_suite import (
        build_session,
        standard_ruleset_specs,
    )
    from generic_chess.session.session import GameSession

    corpus = json.loads(
        (
            Path(__file__).resolve().parent.parent
            / "tests"
            / "fixtures"
            / "native_correctness_corpus_v1.json"
        ).read_text(encoding="utf-8")
    )["fixtures"]
    specs = {s.fixture_id: s for s in standard_ruleset_specs()}
    for fixture in corpus:
        compiled, session = build_session(
            specs[fixture["ruleset_fixture_id"]],
            tuple(fixture["action_prefix"]),
        )
        evaluator, rules, eval_tables = _setup(compiled, session)
        for depth in (0, 1, 2, 3):
            _compare(
                compiled,
                session,
                rules,
                eval_tables,
                evaluator,
                depth,
                fixture["fixture_id"],
            )


@requires_native
def test_targeted_fixtures_search_differential():
    from generic_chess.ai.benchmark.targeted_fixtures import (
        build_targeted_fixtures,
    )
    from generic_chess.core.actions import action_from_dict
    from generic_chess.session.session import GameSession

    for fixture in build_targeted_fixtures():
        session = GameSession(fixture.compiled)
        for action_dict in fixture.action_prefix:
            session.submit(action_from_dict(action_dict))
        evaluator, rules, eval_tables = _setup(fixture.compiled, session)
        for depth in (1, 2):
            _compare(
                fixture.compiled,
                session,
                rules,
                eval_tables,
                evaluator,
                depth,
                fixture.fixture_id,
            )


@requires_native
def test_fuzz_search_differential():
    from generic_chess.ai.benchmark.audit_suite import (
        build_session,
        smoke_ruleset_specs,
    )
    from generic_chess.ai.benchmark.position_mining import mine_suite

    specs = smoke_ruleset_specs()
    positions = mine_suite(
        specs, playout_seed=9, max_games=2, max_plies=16, max_positions=3
    )
    for pos in positions:
        spec = next(s for s in specs if s.fixture_id == pos.ruleset_fixture_id)
        compiled, session = build_session(spec, pos.action_prefix)
        evaluator, rules, eval_tables = _setup(compiled, session)
        for depth in (1, 2):
            _compare(
                compiled,
                session,
                rules,
                eval_tables,
                evaluator,
                depth,
                pos.fixture_id,
            )


@requires_native
def test_repetition_history_search_differential():
    from test_native_history import _cycle_ruleset, _session_at_ply

    compiled = _cycle_ruleset()
    for ply in (3, 7, 11):
        session = _session_at_ply(compiled, ply)
        evaluator, rules, eval_tables = _setup(compiled, session)
        for depth in (1, 2):
            _compare(
                compiled,
                session,
                rules,
                eval_tables,
                evaluator,
                depth,
                f"cycle-ply-{ply}",
            )


@requires_native
def test_promotion_and_drop_search_differential():
    from generic_chess.core.movement import LeapAtom, RayAtom
    from generic_chess.core.pieces import Piece, PieceType
    from generic_chess.session.session import GameSession

    from native_test_helpers import simple_ruleset

    n = 4
    king = PieceType("K", "K", (), is_anchor=True)
    pawn = PieceType(
        "P", "P", (LeapAtom((0, 1)), LeapAtom((0, -1))),
        is_promotable=True, promotion_target_ids=("Q",),
    )
    queen = PieceType(
        "Q", "Q", tuple(RayAtom((df, dr)) for df in (-1, 0, 1) for dr in (-1, 0, 1) if (df, dr) != (0, 0)),
    )
    rows = [[None] * n for _ in range(n)]
    rows[0][0] = Piece(0, "K", "K", False)
    rows[n - 1][n - 1] = Piece(1, "K", "K", False)
    rows[1][0] = Piece(0, "P", "P", False)
    rows[1][1] = Piece(1, "P", "P", False)
    mask = (True,) * (n * n)
    compiled = simple_ruleset(
        (king, pawn, queen),
        rows,
        drop_types=("P", "Q"),
        drop_mask_all=True,
        promotion_allowed={"P": ((), ())},
        promotion_forced={"P": ((), ())},
    )
    session = GameSession(compiled)
    evaluator, rules, eval_tables = _setup(compiled, session)
    for depth in (1, 2, 3):
        _compare(compiled, session, rules, eval_tables, evaluator, depth, "promo-drop")


@requires_native
def test_owner_swap_score_negation():
    from generic_chess.core.movement import LeapAtom
    from generic_chess.core.pieces import Piece, PieceType
    from generic_chess.core.position import Hands, Position
    from generic_chess.core.keys import position_key
    from generic_chess.core.terminal import _terminal_from_parts
    from generic_chess.native.reference import reference_fixed_depth_minimax
    from generic_chess.session.session import GameSession

    from native_test_helpers import make_state, simple_ruleset

    n = 4
    king = PieceType("K", "K", (), is_anchor=True)
    f = PieceType("F", "F", (LeapAtom((0, 1)), LeapAtom((0, -1))))
    rows = [[None] * n for _ in range(n)]
    rows[0][0] = Piece(0, "K", "K", False)
    rows[3][3] = Piece(1, "K", "K", False)
    rows[1][0] = Piece(0, "F", "F", False)
    rows[2][3] = Piece(1, "F", "F", False)
    compiled = simple_ruleset((king, f), rows, drop_types=("F",))

    def build(flip: bool):
        board = [None] * (n * n)
        for i in range(n * n):
            p = compiled.initial_position.board[i]
            if p is None:
                continue
            owner = 1 - p.owner if flip else p.owner
            board[i] = Piece(owner, p.base_type_id, p.current_type_id, p.promoted)
        side = 1 if flip else 0
        return make_state(
            compiled,
            Position(tuple(board), (Hands.empty(), Hands.empty()), side, compiled.ruleset_fingerprint),
        )

    st_a = build(False)
    st_b = build(True)
    evaluator, rules, eval_tables = _setup(compiled, GameSession(compiled))
    for depth in (1, 2):
        ref_a = reference_fixed_depth_minimax(st_a, compiled, evaluator, depth)[0]
        ref_b = reference_fixed_depth_minimax(st_b, compiled, evaluator, depth)[0]
        assert ref_a == -ref_b
        nat_a = native_fixed_depth_search_state(
            compiled, rules, eval_tables, st_a, depth
        )
        nat_b = native_fixed_depth_search_state(
            compiled, rules, eval_tables, st_b, depth
        )
        assert nat_a.score == -nat_b.score
        assert nat_a.score == ref_a
