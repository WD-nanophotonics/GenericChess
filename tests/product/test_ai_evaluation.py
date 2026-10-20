"""Static analysis, values, mobility curves, symmetry, base/current semantics."""

import pytest

from generic_chess.ai.evaluation.analyzer import movement_signature
from generic_chess.ai.evaluation.config import EvaluationConfig, MATE_SCORE, MATE_THRESHOLD
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.mobility import (
    analytic_mobility_at_density,
    mobility_density_curve,
)
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.alphabeta.search import terminal_score
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.terminal import TerminalResult, TerminalStatus

from ai_fixtures import build_4x4_rooks, build_promotion, king, rook
from conftest import T, king_type, make_position, make_ruleset, make_state


def _config():
    return EvaluationConfig()


@pytest.mark.parametrize('rows,mobility,escape,expected', [
    (['...k', 'r...', 'R...', 'K...'], 1, 1, 0),
    (['...k', 'r...', 'R...', 'K...'], 1, 0, 1),
    (['...k', 'r...', 'R...', 'K...'], 0, 1, -1),
    (['...k', 'r...', 'R...', 'K...'], 0, 0, 0),
    (['...k', '....', 'R.r.', 'K...'], 1, 1, -2),
])
def test_dynamic_features_share_current_position_attack_maps(
        monkeypatch, rows, mobility, escape, expected):
    import generic_chess.ai.evaluation.evaluator as module
    from dataclasses import replace

    compiled = build_4x4_rooks()
    config = EvaluationConfig(dynamic_mobility_weight=mobility,
                              anchor_escape_weight=escape,
                              promotion_potential_weight=0)
    evaluator = Evaluator(compiled, build_ruleset_profile(compiled, config), config)
    state = make_state(compiled, rows)
    original = module.pseudo_attacks
    calls = []

    def counted(position, owner, rules):
        calls.append((position, owner))
        return original(position, owner, rules)

    monkeypatch.setattr(module, 'pseudo_attacks', counted)
    assert evaluator.evaluate(state) == expected
    assert [owner for _, owner in calls] == ([0, 1] if mobility or escape else [])
    # A new call uses its own maps, including after the side-to-move changes.
    calls.clear()
    flipped = replace(state, position=replace(state.position, side_to_move=1))
    assert evaluator.evaluate(flipped) == -expected
    assert [owner for _, owner in calls] == ([0, 1] if mobility or escape else [])


def test_anchor_not_in_material():
    compiled = build_4x4_rooks()
    profile = build_ruleset_profile(compiled, _config())
    assert profile.board_value_by_type["K"] == 0
    assert profile.piece_profiles["K"].is_anchor
    assert profile.piece_profiles["K"].normalized_hand_value == 0


def test_unreachable_declaration_does_not_rescale_reachable_static_values():
    from generic_chess.core.movegen import legal_actions
    from generic_chess.rules.compiler import compile_ruleset

    rows = ["...k", "....", "R...", "K..."]
    reachable_rules = make_ruleset(
        4, [king_type(), T("R", RayAtom((1, 0)))], rows,
    )
    decorated_rules = make_ruleset(
        4, [king_type(), T("R", RayAtom((1, 0))), T("X", LeapAtom((1, 1)))], rows,
    )
    reachable = compile_ruleset(reachable_rules)
    decorated = compile_ruleset(decorated_rules)
    config = _config()
    base_profile = build_ruleset_profile(reachable, config)
    decorated_profile = build_ruleset_profile(decorated, config)

    assert base_profile.board_value_by_type["R"] == 1000
    assert decorated_profile.board_value_by_type["R"] == 1000
    assert decorated_profile.median_non_anchor_value == base_profile.median_non_anchor_value
    assert "X" in decorated_profile.board_value_by_type  # diagnostic remains available

    base_state = make_state(reachable, rows)
    decorated_state = make_state(decorated, rows)
    assert legal_actions(base_state, reachable) == legal_actions(decorated_state, decorated)
    assert Evaluator(reachable, base_profile, config).evaluate(base_state) == Evaluator(
        decorated, decorated_profile, config
    ).evaluate(decorated_state)


def test_profile_reachability_includes_enabled_promotion_targets():
    from generic_chess.ai.evaluation.profile import _initially_reachable_type_ids
    from generic_chess.rules.compiler import compile_ruleset

    rules = make_ruleset(
        4,
        [
            king_type(),
            T("P", LeapAtom((0, 1)), is_promotable=True, targets=("G",)),
            T("G", RayAtom((1, 0))),
            T("X", LeapAtom((1, 0))),
        ],
        ["...k", "....", "P...", "K..."],
        auto_promotion=True,
    )
    compiled = compile_ruleset(rules)
    reachable = _initially_reachable_type_ids(compiled)
    assert {"K", "P", "G"} <= reachable
    assert "X" not in reachable


def test_profile_reachability_does_not_chain_through_promoted_targets():
    from generic_chess.ai.evaluation.profile import _initially_reachable_type_ids
    from generic_chess.rules.compiler import compile_ruleset

    rules = make_ruleset(
        4,
        [
            king_type(),
            T("P", LeapAtom((0, 1)), is_promotable=True, targets=("Q",)),
            T("Q", LeapAtom((0, 1)), is_promotable=True, targets=("R",)),
            T("R", RayAtom((1, 0))),
        ],
        ["...k", "....", "P...", "K..."],
        auto_promotion=True,
    )
    compiled = compile_ruleset(rules)
    reachable = _initially_reachable_type_ids(compiled)

    # Q can appear only as P's promoted current type in this inventory.
    # Promoted pieces cannot promote again, and capture/drop preserves base P.
    assert {"K", "P", "Q"} <= reachable
    assert "R" not in reachable

    without_r = make_ruleset(
        4,
        [
            king_type(),
            T("P", LeapAtom((0, 1)), is_promotable=True, targets=("Q",)),
            T("Q", LeapAtom((0, 1))),
        ],
        ["...k", "....", "P...", "K..."],
        auto_promotion=True,
    )
    reduced = compile_ruleset(without_r)
    full_profile = build_ruleset_profile(compiled, _config())
    reduced_profile = build_ruleset_profile(reduced, _config())
    assert full_profile.median_non_anchor_value == reduced_profile.median_non_anchor_value
    assert full_profile.board_value_by_type["P"] == reduced_profile.board_value_by_type["P"]
    assert full_profile.board_value_by_type["Q"] == reduced_profile.board_value_by_type["Q"]


def test_profile_reachability_can_promote_an_independently_reachable_target_type():
    from generic_chess.ai.evaluation.profile import _initially_reachable_type_ids
    from generic_chess.rules.compiler import compile_ruleset

    rules = make_ruleset(
        4,
        [
            king_type(),
            T("P", LeapAtom((0, 1)), is_promotable=True, targets=("Q",)),
            T("Q", LeapAtom((0, 1)), is_promotable=True, targets=("R",)),
            T("R", RayAtom((1, 0))),
        ],
        ["...k", "....", "P...", "KQ.."],
        auto_promotion=True,
    )
    compiled = compile_ruleset(rules)
    reachable = _initially_reachable_type_ids(compiled)

    # Q is independently present as an unpromoted base type, so Q→R is usable.
    assert {"K", "P", "Q", "R"} <= reachable


@pytest.mark.parametrize('atoms', [
    (LeapAtom((0, 1)),),
    (LeapAtom((0, 1)),) * 2,
    (RayAtom((0, 1), 1),),
    (LeapAtom((0, 1)), RayAtom((0, 1), 1)),
    (LeapAtom((0, 1)), LeapAtom((0, 2)), RayAtom((1, 0))),
])
def test_short_escape_uses_owner_frame_and_unique_targets(atoms):
    from generic_chess.rules.compiler import compile_ruleset
    from generic_chess.core.coordinates import Square

    compiled = compile_ruleset(make_ruleset(4, [
        T('K', *atoms, is_anchor=True), T('R', RayAtom((1, 0)))],
        ['...k', '....', '....', 'K...']))
    cfg = EvaluationConfig(dynamic_mobility_weight=0, anchor_escape_weight=1,
                           promotion_potential_weight=0)
    evaluator = Evaluator(compiled, build_ruleset_profile(compiled, cfg), cfg)
    state = make_state(compiled, ['...k', '....', '....', 'K...'])
    assert [evaluator._anchor_escape(state.position, owner, set())
            for owner in (0, 1)] == [1, 1]
    assert evaluator.evaluate(state) == 0
    assert evaluator._anchor_escape(state.position, 1, {Square(3, 2)}) == 0
    blocked = make_state(compiled, ['...k', '...R', '....', 'K...'])
    assert evaluator._anchor_escape(blocked.position, 1, set()) == 0


def test_short_escape_does_not_expand_to_long_leaps_or_unbounded_rays():
    from generic_chess.rules.compiler import compile_ruleset

    compiled = compile_ruleset(make_ruleset(4, [
        T('K', LeapAtom((0, 2)), RayAtom((1, 0)), is_anchor=True),
        T('R', RayAtom((1, 0)))], ['...k', '....', '....', 'K...']))
    cfg = EvaluationConfig()
    evaluator = Evaluator(compiled, build_ruleset_profile(compiled, cfg), cfg)
    state = make_state(compiled, ['...k', '....', '....', 'K...'])
    assert evaluator._anchor_escape(state.position, 0, set()) == 0


def test_type_name_invariance():
    config = _config()
    a = build_ruleset_profile(build_4x4_rooks(), config)
    compiled_b = None
    from generic_chess.core.pieces import PieceType, Piece
    from generic_chess.rules.compiler import compile_ruleset
    from generic_chess.rules.schema import RuleSet

    n = 4
    rows = [[None] * n for _ in range(n)]
    rows[0][0] = Piece(0, "K", "K", False)
    rows[3][3] = Piece(1, "K", "K", False)
    rows[1][2] = Piece(0, "Z1", "Z1", False)
    rows[2][1] = Piece(1, "Z2", "Z2", False)
    z1 = PieceType("Z1", "Z1", (RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0))))
    z2 = PieceType("Z2", "Z2", (RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0))))
    mask = (True,) * 16
    ruleset = RuleSet(
        board_size=n,
        piece_types=(king(), z1, z2),
        initial_position=tuple(tuple(r) for r in rows),
        drop_allowed={"Z1": (mask, mask), "Z2": (mask, mask)},
        promotion_allowed={},
        promotion_forced={},
    )
    compiled_b = compile_ruleset(ruleset)
    b = build_ruleset_profile(compiled_b, config)
    assert b.piece_profiles["Z1"].raw_capability_score == b.piece_profiles["Z2"].raw_capability_score
    assert b.piece_profiles["Z1"].normalized_board_value == b.piece_profiles["Z2"].normalized_board_value
    assert movement_signature(z1.movement_atoms) == movement_signature(z2.movement_atoms)


def test_ray_leap_dominance():
    n = 8
    # Same empty-board target set along one file: ray vs a leap at every step.
    ray_atoms = (RayAtom((0, 1)),)
    leap_atoms = tuple(LeapAtom((0, j)) for j in range(1, 8))
    config = _config()
    ray_curve = mobility_density_curve(
        n, ray_atoms, (0.0, 0.5),
        signature="s", version=config.evaluator_version, mc_samples=config.mc_samples,
    )
    leap_curve = mobility_density_curve(
        n, leap_atoms, (0.0, 0.5),
        signature="s", version=config.evaluator_version, mc_samples=config.mc_samples,
    )
    assert ray_curve[0] == pytest.approx(leap_curve[0], abs=1e-3)  # empty board equal
    assert leap_curve[1] >= ray_curve[1]
    assert leap_curve[1] > ray_curve[1]  # strictly better under occupancy


def test_density_curve_dedup_overlapping_atoms():
    config = _config()
    leap = LeapAtom((0, 1))
    dup_atoms = (leap, LeapAtom((0, 1)))
    curve = mobility_density_curve(
        8,
        dup_atoms,
        (0.0, 0.5),
        signature="dup",
        version=config.evaluator_version,
        mc_samples=256,
    )
    single = analytic_mobility_at_density(8, (leap,), 0.5)
    assert curve[0] == pytest.approx(56 / 64, abs=1e-9)  # empty board: 56/64
    assert curve[1] == pytest.approx(single, abs=0.02)
    again = mobility_density_curve(
        8,
        dup_atoms,
        (0.0, 0.5),
        signature="dup",
        version=config.evaluator_version,
        mc_samples=256,
    )
    assert curve == again  # deterministic


def test_promotion_gain_order_invariant():
    from generic_chess.rules.compiler import compile_ruleset

    config = _config()
    pawn = T("P", LeapAtom((0, 1)), is_promotable=True, targets=("G",))
    gold = T("G", RayAtom((1, 0)))
    lines = [
        ".......k",
        "....P...",
        "........",
        "........",
        "........",
        "........",
        "........",
        "K.......",
    ]
    a = compile_ruleset(
        make_ruleset(8, [king_type(), pawn, gold], lines, auto_promotion=True)
    )
    b = compile_ruleset(
        make_ruleset(8, [gold, pawn, king_type()], lines, auto_promotion=True)
    )
    pa = build_ruleset_profile(a, config)
    pb = build_ruleset_profile(b, config)
    assert pa.board_value_by_type == pb.board_value_by_type
    assert pa.hand_value_by_base_type == pb.hand_value_by_base_type
    assert pa.promotion_gain_by_type == pb.promotion_gain_by_type
    assert pa.piece_profiles["P"] == pb.piece_profiles["P"]
    assert pa.piece_profiles["G"] == pb.piece_profiles["G"]
    assert pa.promotion_gain_by_type["P"] > 0  # gain is not dropped when G is later


def test_static_profile_equivariant_under_bijective_type_id_rename():
    from dataclasses import replace

    from generic_chess.rules.compiler import compile_ruleset

    config = _config()
    types = [
        king_type(),
        T("P", LeapAtom((0, 1)), is_promotable=True, targets=("G", "R")),
        T("G", LeapAtom((0, 1)), LeapAtom((1, 0))),
        T("R", RayAtom((1, 0)), RayAtom((0, 1))),
    ]
    original_rules = make_ruleset(
        6,
        types,
        [".....k", "......", "......", "......", "......", "K....P"],
        auto_drop=True,
        auto_promotion=True,
    )
    rename = {"K": "anchor_z", "P": "source_q", "G": "target_x", "R": "ray_n"}
    renamed_types = tuple(
        replace(
            piece_type,
            type_id=rename[piece_type.type_id],
            promotion_target_ids=tuple(
                rename[target] for target in piece_type.promotion_target_ids
            ),
        )
        for piece_type in original_rules.piece_types
    )
    renamed_position = tuple(
        tuple(
            None
            if piece is None
            else replace(
                piece,
                base_type_id=rename[piece.base_type_id],
                current_type_id=rename[piece.current_type_id],
            )
            for piece in row
        )
        for row in original_rules.initial_position
    )
    renamed_rules = replace(
        original_rules,
        piece_types=renamed_types,
        initial_position=renamed_position,
        drop_allowed={rename[key]: value for key, value in original_rules.drop_allowed.items()},
        promotion_allowed={
            rename[key]: value for key, value in original_rules.promotion_allowed.items()
        },
        promotion_forced={
            rename[key]: value for key, value in original_rules.promotion_forced.items()
        },
    )

    original = build_ruleset_profile(compile_ruleset(original_rules), config)
    renamed = build_ruleset_profile(compile_ruleset(renamed_rules), config)

    assert renamed.median_non_anchor_value == original.median_non_anchor_value
    assert renamed.board_value_by_type == {
        rename[type_id]: value for type_id, value in original.board_value_by_type.items()
    }
    assert renamed.hand_value_by_base_type == {
        rename[type_id]: value for type_id, value in original.hand_value_by_base_type.items()
    }
    assert renamed.promotion_gain_by_type == {
        rename[type_id]: value for type_id, value in original.promotion_gain_by_type.items()
    }
    for type_id, profile in original.piece_profiles.items():
        mapped_profile = replace(renamed.piece_profiles[rename[type_id]], type_id=type_id)
        assert mapped_profile == profile


def test_semantic_profile_equivariant_under_bijective_type_id_rename():
    from collections.abc import Mapping
    from dataclasses import fields, is_dataclass, replace

    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.rules.western_chess import build_western_chess_ruleset

    rename = {
        "K": "king_z", "P": "pawn_q", "N": "knight_x",
        "B": "bishop_m", "R": "rook_v", "Q": "queen_a",
    }
    id_keyed_fields = {
        "drop_allowed", "promotion_allowed", "promotion_forced",
        "initial_setup_positions", "weights",
    }

    def remap(value, field_name=""):
        if is_dataclass(value):
            changes = {}
            for item in fields(value):
                old = getattr(value, item.name)
                new = remap(old, item.name)
                if new is not old and new != old:
                    changes[item.name] = new
            return replace(value, **changes) if changes else value
        if isinstance(value, Mapping):
            if field_name in id_keyed_fields:
                return {
                    rename.get(key, key): remap(item)
                    for key, item in value.items()
                }
            return {key: remap(item) for key, item in value.items()}
        if isinstance(value, tuple):
            if (
                field_name.endswith("_type_ids")
                or field_name in {"type_ids", "promotion_target_ids"}
            ):
                return tuple(rename.get(item, item) for item in value)
            return tuple(remap(item) for item in value)
        if isinstance(value, list):
            return [remap(item) for item in value]
        if isinstance(value, str) and field_name.endswith("_type_id"):
            return rename.get(value, value)
        if isinstance(value, str) and field_name in {
            "type_id", "explicit_promotion_type",
        }:
            return rename.get(value, value)
        return value

    rules = build_western_chess_ruleset()
    renamed_rules = remap(rules)
    assert len(rules.semantic_actions) == 20
    assert {
        type_id for action in renamed_rules.semantic_actions
        for type_id in action.type_ids
    } == set(rename.values())

    config = _config()
    original = build_ruleset_profile(
        compile_ruleset_for_execution(rules), config
    )
    renamed = build_ruleset_profile(
        compile_ruleset_for_execution(renamed_rules), config
    )

    assert renamed.median_non_anchor_value == original.median_non_anchor_value
    assert renamed.board_value_by_type == {
        rename[type_id]: value for type_id, value in original.board_value_by_type.items()
    }
    assert renamed.hand_value_by_base_type == {
        rename[type_id]: value
        for type_id, value in original.hand_value_by_base_type.items()
    }
    assert renamed.promotion_gain_by_type == {
        rename[type_id]: value
        for type_id, value in original.promotion_gain_by_type.items()
    }
    for type_id, profile in original.piece_profiles.items():
        mapped_profile = replace(
            renamed.piece_profiles[rename[type_id]], type_id=type_id
        )
        assert mapped_profile == profile


def test_mirrored_position_evaluation_negates():
    compiled = build_4x4_rooks()
    profile = build_ruleset_profile(compiled, _config())
    evaluator = Evaluator(compiled, profile, _config())
    state_a = make_state(compiled, [
        "....",
        "....",
        "....",
        "K..R",
    ])
    # Rotate 180 + swap colors.
    def rotate_swap(pos, n):
        from generic_chess.core.coordinates import Square
        from generic_chess.core.pieces import Piece
        board = [None] * (n * n)
        for idx, piece in enumerate(pos.board):
            if piece is None:
                continue
            sq = Square(idx % n, idx // n)
            r = Square(n - 1 - sq.file, n - 1 - sq.rank)
            board[r.rank * n + r.file] = Piece(1 - piece.owner, piece.base_type_id, piece.current_type_id, piece.promoted)
        return tuple(board)

    n = compiled.board_size
    board_b = rotate_swap(state_a.position, n)
    from generic_chess.core.position import Position, Hands

    pos_b = Position(board=board_b, hands=(Hands.empty(), Hands.empty()), side_to_move=0, ruleset_fingerprint=compiled.ruleset_fingerprint)
    from generic_chess.core.position import GameState
    from generic_chess.core.terminal import TerminalResult, TerminalStatus

    state_b = GameState(pos_b, 0, (("k", 1),), TerminalResult(TerminalStatus.ONGOING))
    assert evaluator.evaluate(state_a) == -evaluator.evaluate(state_b)


def test_promoted_uses_current_type_and_hand_uses_base():
    compiled = build_promotion()
    config = _config()
    profile = build_ruleset_profile(compiled, config)
    evaluator = Evaluator(compiled, profile, config)
    assert profile.board_value_by_type["G"] > profile.board_value_by_type["P"]

    lines = [
        ".......k",
        "....P...",
        "........",
        "........",
        "........",
        "........",
        "........",
        "K.......",
    ]
    base_state = make_state(compiled, lines)  # native P on the board
    promo_lines = [
        ".......k",
        "....G...",
        "........",
        "........",
        "........",
        "........",
        "........",
        "K.......",
    ]
    promo_state = make_state(compiled, promo_lines, promoted={(4, 6): "P"})  # promoted: base P, current G
    assert evaluator.evaluate(promo_state) > evaluator.evaluate(base_state)

    # Hand material uses base type value.
    plain = [
        ".......k",
        "........",
        "........",
        "........",
        "........",
        "........",
        "........",
        "K.......",
    ]
    no_hand = make_state(compiled, plain)
    with_hand = make_state(compiled, plain, hands=([("P", 1)], []))
    delta = evaluator.evaluate(with_hand) - evaluator.evaluate(no_hand)
    assert delta == profile.hand_value_by_base_type["P"]


def test_semantic_western_pawn_promotion_zone_uses_compiled_masks():
    from types import SimpleNamespace

    from generic_chess.core.coordinates import Square, square_to_index
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.rules.western_chess import build_western_chess_ruleset

    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    config = EvaluationConfig()
    profile = build_ruleset_profile(compiled, config)
    evaluator = Evaluator(compiled, profile, config)

    # The legacy P atom table is empty although semantic P has direct moves.
    # Semantic execution carries the generated promotion masks, which define
    # destinations independently of the projected empty-board geometry.
    for owner in (0, 1):
        expected = frozenset(
            square_to_index(to, 8)
            for _, to in compiled.promotion_allowed["P"][owner]
        )
        assert evaluator._zones[("P", owner)] == expected
    pawn = SimpleNamespace(promoted=False, base_type_id="P", owner=0)
    unit = max(1, profile.promotion_gain_by_type["P"] // 1000)
    assert evaluator._promotion_bonus(pawn, square_to_index(Square(3, 7), 8)) == 3 * unit
    assert evaluator._promotion_bonus(pawn, square_to_index(Square(3, 6), 8)) == 3 * unit // 2
    assert evaluator._promotion_bonus(pawn, square_to_index(Square(3, 5), 8)) == 0


def test_legacy_promotion_zone_matches_compiled_forward_table():
    from types import SimpleNamespace

    from generic_chess.core.coordinates import Square, square_to_index

    compiled = build_promotion()
    config = EvaluationConfig()
    profile = build_ruleset_profile(compiled, config)
    evaluator = Evaluator(compiled, profile, config)
    for pt in compiled.piece_types:
        if not pt.is_promotable:
            continue
        for owner in (0, 1):
            expected_forward = tuple(
                tuple(square_to_index(target, compiled.board_size) for target in targets)
                for targets in compiled.empty_forward_mobility[pt.type_id][owner]
            )
            assert evaluator._promotion_forward[(pt.type_id, owner)] == expected_forward
            expected_zone = frozenset(
                target_idx
                for _, to in compiled.promotion_allowed[pt.type_id][owner]
                for target_idx in (square_to_index(to, compiled.board_size),)
                if any(
                    compiled.empty_mobility[target][owner][target_idx]
                    for target in pt.promotion_target_ids
                )
            )
            assert evaluator._zones[(pt.type_id, owner)] == expected_zone

    # Forward targets and zone members now share integer-index representation;
    # the previous Square-vs-int membership check silently suppressed this band.
    pawn = SimpleNamespace(promoted=False, base_type_id="P", owner=0)
    unit = max(1, profile.promotion_gain_by_type["P"] // 1000)
    assert evaluator._promotion_bonus(
        pawn, square_to_index(Square(3, 6), 8)
    ) == config.promotion_potential_weight * unit // 2


def test_promotion_potential_tracks_compiled_allowed_destinations():
    from types import SimpleNamespace

    from generic_chess.core.coordinates import Square, square_to_index
    from generic_chess.core.movegen import legal_actions
    from generic_chess.rules.compiler import compile_ruleset

    pawn = T("P", LeapAtom((0, 1)), is_promotable=True, targets=("G",))
    gold = T("G", RayAtom((1, 0)))
    ruleset = make_ruleset(
        8,
        [king_type(), pawn, gold],
        lines=[
            ".......k", "........", "........", "........",
            "........", "........", "........", "K.......",
        ],
        promotion={"P": ([(Square(4, 1), Square(4, 2))], [])},
    )
    compiled = compile_ruleset(ruleset)
    config = EvaluationConfig()
    profile = build_ruleset_profile(compiled, config)
    evaluator = Evaluator(compiled, profile, config)

    # Only this custom destination is promotion-enabled. The evaluator should
    # not substitute every geometric no-forward square for the rule's mask.
    target = square_to_index(Square(4, 2), 8)
    geometric_edge = square_to_index(Square(4, 7), 8)
    assert evaluator._zones[("P", 0)] == frozenset({target})
    assert evaluator._promotion_bonus(
        SimpleNamespace(promoted=False, base_type_id="P", owner=0), target
    ) > 0
    unit = max(1, profile.promotion_gain_by_type["P"] // 1000)
    assert evaluator._promotion_bonus(
        SimpleNamespace(promoted=False, base_type_id="P", owner=0),
        square_to_index(Square(4, 1), 8),
    ) == config.promotion_potential_weight * unit // 2
    assert evaluator._promotion_bonus(
        SimpleNamespace(promoted=False, base_type_id="P", owner=0), geometric_edge
    ) == 0

    state = make_state(compiled, [
        ".......k", "........", "........", "........",
        "........", "........", "....P...", "K.......",
    ])
    moves = [a for a in legal_actions(state, compiled)
             if a.from_square == Square(4, 1) and a.to_square == Square(4, 2)]
    assert any(a.promotion_target_id == "G" for a in moves)


@pytest.mark.parametrize(
    'semantic_execution', [False, True], ids=['legacy', 'inherited-semantic']
)
def test_promotion_potential_ignores_structurally_dead_targets(semantic_execution):
    from types import SimpleNamespace

    from generic_chess.core.coordinates import Square, square_to_index
    from generic_chess.core.movegen import legal_actions
    from generic_chess.rules.compiler import (
        compile_legacy_ruleset_for_semantic_execution, compile_ruleset,
    )

    pawn = T('P', LeapAtom((1, 1)), is_promotable=True, targets=('G',))
    # At the only promotion destination, G has no empty-board move. Core
    # therefore suppresses that structurally dead promotion variant.
    gold = T('G', RayAtom((1, 0)), RayAtom((0, 1)))
    rows = [
        '........', '......P.', '........', '........',
        '........', '........', '........', 'K......k',
    ]
    ruleset = make_ruleset(
        8, [king_type(), pawn, gold], lines=rows,
        promotion={'P': ([(Square(6, 6), Square(7, 7))], [])},
    )
    compiled = (
        compile_legacy_ruleset_for_semantic_execution(ruleset)
        if semantic_execution else compile_ruleset(ruleset)
    )
    config = EvaluationConfig()
    profile = build_ruleset_profile(compiled, config)
    evaluator = Evaluator(compiled, profile, config)
    target = square_to_index(Square(7, 7), 8)

    assert profile.promotion_gain_by_type['P'] > 0
    assert not compiled.empty_mobility['G'][0][target]
    assert target not in evaluator._zones[('P', 0)]
    assert evaluator._promotion_bonus(
        SimpleNamespace(promoted=False, base_type_id='P', owner=0), target
    ) == 0

    state = make_state(compiled, rows)
    moves = [a for a in legal_actions(state, compiled)
             if a.from_square == Square(6, 6) and a.to_square == Square(7, 7)]
    assert len(moves) == 1
    assert moves[0].promotion_target_id is None


def test_mate_score_beats_static():
    compiled = build_4x4_rooks()
    profile = build_ruleset_profile(compiled, _config())
    evaluator = Evaluator(compiled, profile, _config())
    state = make_state(compiled, [
        "....",
        "....",
        "....",
        "K..R",
    ])
    static = evaluator.evaluate(state)
    assert abs(static) < MATE_THRESHOLD
    mate = terminal_score(TerminalResult(TerminalStatus.CHECKMATE, 0), 0, 0)
    assert mate > static
    assert mate == MATE_SCORE
    later = terminal_score(TerminalResult(TerminalStatus.CHECKMATE, 0), 0, 3)
    assert later == MATE_SCORE - 3  # faster win scores higher

@pytest.mark.parametrize('sfen', [
    '8k/9/4+p4/4P4/9/9/9/9/K8 b 2P1g 1',
    '8k/9/3+P5/9/5B3/9/9/9/K8 w 2rP 7',
])
def test_standard_shogi_evaluation_is_owner_rotation_symmetric_with_hands_and_promotion(sfen):
    from dataclasses import replace

    from generic_chess.ai.evaluation.evaluator import Evaluator
    from generic_chess.ai.evaluation.profile import build_ruleset_profile
    from generic_chess.core.pieces import Piece
    from generic_chess.learning.shogi_rules import sfen_to_gc_state
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset

    compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    config = EvaluationConfig()
    evaluator = Evaluator(compiled, build_ruleset_profile(compiled, config), config)
    state = sfen_to_gc_state(compiled, sfen)
    assert any(piece is not None and piece.promoted for piece in state.position.board)
    assert any(hand.total() for hand in state.position.hands)
    base_score = evaluator.evaluate(state)
    assert base_score != 0

    def rotate_swap_position(position, *, flip_turn):
        n = compiled.board_size
        board = [None] * (n * n)
        for index, piece in enumerate(position.board):
            if piece is None:
                continue
            rank, file = divmod(index, n)
            target = (n - 1 - rank) * n + (n - 1 - file)
            board[target] = Piece(
                1 - piece.owner, piece.base_type_id, piece.current_type_id,
                piece.promoted,
            )
        return replace(
            position,
            board=tuple(board),
            hands=(position.hands[1], position.hands[0]),
            side_to_move=(1 - position.side_to_move if flip_turn else position.side_to_move),
        )

    owner_swapped = replace(
        state, position=rotate_swap_position(state.position, flip_turn=False)
    )
    same_actor_to_move = replace(
        state, position=rotate_swap_position(state.position, flip_turn=True)
    )
    assert evaluator.evaluate(owner_swapped) == -base_score
    assert evaluator.evaluate(same_actor_to_move) == base_score
