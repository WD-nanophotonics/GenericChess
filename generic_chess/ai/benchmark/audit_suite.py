"""Multi-RuleSet audit suite: deterministic specs, geometry classification."""

from __future__ import annotations

import math
from dataclasses import replace
from typing import Any, Callable, Mapping

from ...core.actions import action_from_dict
from ...core.coordinates import Square, index_to_square
from ...core.movement import LeapAtom, RayAtom, atom_targets
from ...core.pieces import Piece, PieceType
from ...generation.config import GeneratorConfig
from ...generation.generator import generate_game
from ...rules.compiler import compile_ruleset
from ...rules.compiled import CompiledRuleSet
from ...rules.schema import RuleSet
from ...session.session import GameSession
from .audit_schema import RuleSetFixtureSpec, SuiteManifest

GENERATOR_VERSION = "generic-chess-generation-1"
SUITE_SCHEMA_VERSION = 1
FULL_MANIFEST_PATH = "tests/fixtures/native_readiness_suite_v1.json"

KING_ATOMS = tuple(
    LeapAtom((df, dr)) for df in (-1, 0, 1) for dr in (-1, 0, 1) if (df, dr) != (0, 0)
)
ORTHO_RAYS = (RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0)))
DIAG_RAYS = (RayAtom((1, 1)), RayAtom((1, -1)), RayAtom((-1, 1)), RayAtom((-1, -1)))


def _pt(
    type_id: str,
    atoms,
    *,
    is_anchor: bool = False,
    is_promotable: bool = False,
    targets=(),
) -> PieceType:
    return PieceType(
        type_id=type_id,
        name=type_id,
        movement_atoms=tuple(atoms),
        is_anchor=is_anchor,
        is_promotable=is_promotable,
        promotion_target_ids=tuple(targets),
    )


def _lines_to_board(n: int, lines: list[str]) -> tuple[tuple[Piece | None, ...], ...]:
    rows = []
    for line in reversed(lines):
        assert len(line) == n
        row = []
        for ch in line:
            if ch == ".":
                row.append(None)
            else:
                owner = 0 if ch.isupper() else 1
                row.append(Piece(owner, ch.upper(), ch.upper(), False))
        rows.append(tuple(row))
    return tuple(rows)


def _promotion_pairs(n: int, owner: int) -> tuple[tuple[Square, Square], frozenset[Square]]:
    """Pawn-like single-step forward promotion data for one owner."""
    last = n - 1 if owner == 0 else 0
    penultimate = n - 2 if owner == 0 else 1
    step = 1 if owner == 0 else -1
    pairs = tuple(
        (Square(f, penultimate), Square(f, last)) for f in range(n)
    )
    forced = frozenset(Square(f, last) for f in range(n))
    return pairs, forced


def _hb(
    fixture_id: str,
    n: int,
    types: list[PieceType],
    lines: list[str],
    *,
    drop_types=(),
    drop_restrict_left: bool = False,
    promo: Mapping[str, tuple] | None = None,
) -> CompiledRuleSet:
    initial = _lines_to_board(n, lines)
    drop: dict[str, tuple[tuple[bool, ...], ...]] = {}
    for t in types:
        if t.is_anchor:
            continue
        if t.type_id not in drop_types:
            mask = (False,) * (n * n)
        elif drop_restrict_left:
            mask = tuple((idx % n) < n // 2 for idx in range(n * n))
        else:
            mask = (True,) * (n * n)
        drop[t.type_id] = (mask, mask)
    allowed: dict[str, tuple[frozenset, ...]] = {}
    forced: dict[str, tuple[frozenset, ...]] = {}
    for tid, (pairs0, forced0, pairs1, forced1) in (promo or {}).items():
        allowed[tid] = (frozenset(pairs0), frozenset(pairs1))
        forced[tid] = (frozenset(forced0), frozenset(forced1))
    ruleset = RuleSet(
        schema_version=1,
        board_size=n,
        piece_types=tuple(types),
        initial_position=initial,
        drop_allowed=drop,
        promotion_allowed=allowed,
        promotion_forced=forced,
        repetition_limit=4,
        max_ply=512,
        stalemate_result="draw",
    )
    return compile_ruleset(ruleset)


def _hb_multi_promo() -> CompiledRuleSet:
    n = 6
    pairs0, forced0 = _promotion_pairs(n, 0)
    pairs1, forced1 = _promotion_pairs(n, 1)
    return _hb(
        "hb_multi_promo",
        n,
        [
            _pt("K", KING_ATOMS, is_anchor=True),
            _pt("P", (LeapAtom((0, 1)),), is_promotable=True, targets=("G", "Q")),
            _pt("G", (LeapAtom((0, 1)), LeapAtom((0, -1)), LeapAtom((1, 0)), LeapAtom((-1, 0)))),
            _pt("Q", ORTHO_RAYS + DIAG_RAYS),
        ],
        [".....k", "P.....", "......", "......", ".....p", "K....."],
        drop_types=("P", "G", "Q"),
        promo={
            "P": (pairs0, forced0, pairs1, forced1),
        },
    )


def _hb_forced_promo() -> CompiledRuleSet:
    n = 6
    pairs0, forced0 = _promotion_pairs(n, 0)
    pairs1, forced1 = _promotion_pairs(n, 1)
    return _hb(
        "hb_forced_promo",
        n,
        [
            _pt("K", KING_ATOMS, is_anchor=True),
            _pt("L", (RayAtom((0, 1)),), is_promotable=True, targets=("G",)),
            _pt("G", (LeapAtom((0, 1)), LeapAtom((0, -1)), LeapAtom((1, 0)), LeapAtom((-1, 0)))),
        ],
        [".....k", "L.....", "......", "......", ".....l", "K....."],
        drop_types=("L", "G"),
        promo={
            "L": (pairs0, forced0, pairs1, forced1),
        },
    )


def _hb_no_drop() -> CompiledRuleSet:
    return _hb(
        "hb_no_drop",
        8,
        [
            _pt("K", KING_ATOMS, is_anchor=True),
            _pt("R", ORTHO_RAYS),
            _pt("B", DIAG_RAYS),
        ],
        [".......k", "........", "........", "........", "........", "........", "R.......", "K......."],
        drop_types=(),
    )


def _hb_restricted_drop() -> CompiledRuleSet:
    return _hb(
        "hb_restricted_drop",
        8,
        [
            _pt("K", KING_ATOMS, is_anchor=True),
            _pt("R", ORTHO_RAYS),
            _pt("B", DIAG_RAYS),
        ],
        [".......k", "........", "........", "........", "........", "........", "R.......", "K......."],
        drop_types=("R", "B"),
        drop_restrict_left=True,
    )


def _hb_sym_leap() -> CompiledRuleSet:
    return _hb(
        "hb_sym_leap",
        6,
        [
            _pt("K", KING_ATOMS, is_anchor=True),
            _pt("N", (LeapAtom((1, 2)), LeapAtom((2, 1)), LeapAtom((-1, 2)), LeapAtom((-2, 1)))),
            _pt("S", KING_ATOMS),
        ],
        [".....k", "......", "N....S", "s....n", "......", "K....."],
        drop_types=(),
    )


def _hb_ray_sym() -> CompiledRuleSet:
    return _hb(
        "hb_ray_sym",
        8,
        [
            _pt("K", KING_ATOMS, is_anchor=True),
            _pt("R", ORTHO_RAYS),
            _pt("B", DIAG_RAYS),
        ],
        [".......k", "........", "........", "R......B", "b......r", "........", "........", "K......."],
        drop_types=(),
    )


def _hb_lance_only() -> CompiledRuleSet:
    return _hb(
        "hb_lance_only",
        6,
        [
            _pt("K", KING_ATOMS, is_anchor=True),
            _pt("L", (RayAtom((0, 1)),)),
        ],
        [".....k", "L.....", "......", "......", ".....l", "K....."],
        drop_types=(),
    )


_HAND_BUILT_BUILDERS: dict[str, Callable[[], CompiledRuleSet]] = {
    "hb_multi_promo": _hb_multi_promo,
    "hb_forced_promo": _hb_forced_promo,
    "hb_no_drop": _hb_no_drop,
    "hb_restricted_drop": _hb_restricted_drop,
    "hb_sym_leap": _hb_sym_leap,
    "hb_ray_sym": _hb_ray_sym,
    "hb_lance_only": _hb_lance_only,
}


_GRID_SEEDS: dict[int, tuple[int, int]] = {
    4: (101, 102),
    6: (201, 202),
    8: (301, 302),
    9: (401, 402),
    10: (501, 502),
}


def _grid_specs() -> list[RuleSetFixtureSpec]:
    specs = []
    for size in (4, 6, 8, 9, 10):
        for preset in ("classic_like", "bilateral_random", "free_random"):
            for seed in _GRID_SEEDS[size]:
                specs.append(
                    RuleSetFixtureSpec(
                        fixture_id=f"gen_{preset}_{size}_{seed}",
                        generator_mode="generator",
                        board_size=size,
                        ruleset_seed=seed,
                        generator_options={"setup_preset": preset},
                    )
                )
    return specs


_BIASED_OPTIONS: tuple[tuple[str, int, int, dict[str, Any]], ...] = (
    ("gen_ray_heavy", 8, 5001, {"setup_preset": "classic_like", "leap_probability": 0.15, "ray_probability": 0.85}),
    ("gen_leap_heavy", 8, 5002, {"setup_preset": "bilateral_random", "leap_probability": 0.9, "ray_probability": 0.1, "max_leap_delta": 2}),
    ("gen_long_ray", 10, 5003, {"setup_preset": "free_random", "ray_probability": 0.9, "max_ray_component": 4}),
    ("gen_short_range", 6, 5004, {"setup_preset": "classic_like", "max_leap_delta": 1, "max_ray_component": 1}),
    ("gen_hybrid", 8, 5005, {"setup_preset": "bilateral_random", "allow_hybrid": True}),
    ("gen_asymmetric", 8, 5006, {"setup_preset": "free_random", "movement_symmetry": "none"}),
)


def _biased_specs() -> list[RuleSetFixtureSpec]:
    return [
        RuleSetFixtureSpec(
            fixture_id=fid,
            generator_mode="generator",
            board_size=size,
            ruleset_seed=seed,
            generator_options=dict(opts),
        )
        for fid, size, seed, opts in _BIASED_OPTIONS
    ]


def _handbuilt_specs() -> list[RuleSetFixtureSpec]:
    specs = []
    for fid, builder in sorted(_HAND_BUILT_BUILDERS.items()):
        compiled = builder()
        specs.append(
            RuleSetFixtureSpec(
                fixture_id=fid,
                generator_mode="handbuilt",
                board_size=compiled.board_size,
                ruleset_seed=0,
            )
        )
    return specs


def standard_ruleset_specs() -> tuple[RuleSetFixtureSpec, ...]:
    return tuple(_grid_specs() + _biased_specs() + _handbuilt_specs())


def smoke_ruleset_specs() -> tuple[RuleSetFixtureSpec, ...]:
    return (
        RuleSetFixtureSpec(
            "gen_classic_like_4_101", "generator", 4, 101,
            generator_options={"setup_preset": "classic_like"},
        ),
        RuleSetFixtureSpec(
            "gen_free_random_6_202", "generator", 6, 202,
            generator_options={"setup_preset": "free_random"},
        ),
    )


REPRESENTATIVE_FIXTURE_IDS: tuple[str, ...] = (
    "gen_classic_like_4_101",
    "gen_classic_like_8_301",
    "gen_bilateral_random_6_201",
    "gen_free_random_10_501",
    "gen_ray_heavy",
    "gen_leap_heavy",
    "gen_hybrid",
    "hb_multi_promo",
    "hb_forced_promo",
    "hb_restricted_drop",
)


def build_compiled(spec: RuleSetFixtureSpec) -> CompiledRuleSet:
    if spec.generator_mode == "handbuilt":
        return _HAND_BUILT_BUILDERS[spec.fixture_id]()
    config = GeneratorConfig(
        seed=spec.ruleset_seed,
        board_size=spec.board_size,
        **spec.generator_options,
    )
    return generate_game(config).compiled_ruleset


def build_session(
    spec: RuleSetFixtureSpec, action_prefix: tuple[dict, ...]
) -> tuple[CompiledRuleSet, GameSession]:
    compiled = build_compiled(spec)
    session = GameSession(compiled)
    for data in action_prefix:
        session.submit(action_from_dict(dict(data)))
    return compiled, session


def _direction_key(df: int, dr: int) -> tuple[int, int]:
    g = math.gcd(abs(df), abs(dr))
    return (df // g, dr // g)


def movement_buckets(compiled: CompiledRuleSet) -> tuple[str, ...]:
    n = compiled.board_size
    leap_total = ray_total = 0
    max_steps = 0
    max_span = 0
    directions: set[tuple[int, int]] = set()
    forward_heavy = False
    symmetric = True
    for pt in compiled.piece_types:
        if pt.is_anchor:
            continue
        for atom in pt.movement_atoms:
            if isinstance(atom, LeapAtom):
                leap_total += 1
                span = max(abs(atom.offset[0]), abs(atom.offset[1]))
                directions.add(_direction_key(*atom.offset))
            else:
                ray_total += 1
                span = atom.max_steps or n
                directions.add(_direction_key(*atom.direction))
                max_steps = max(max_steps, atom.max_steps or n)
            max_span = max(max_span, span)
        f = b = s = 0
        for idx in range(n * n):
            square = index_to_square(idx, n)
            for atom in pt.movement_atoms:
                for target in atom_targets(n, 0, square, atom):
                    if target.rank > square.rank:
                        f += 1
                    elif target.rank < square.rank:
                        b += 1
                    else:
                        s += 1
        if f + b > 0 and abs(f - b) / (f + b) > 0.5:
            forward_heavy = True
            symmetric = False
    buckets = []
    if ray_total and ray_total >= leap_total:
        buckets.append("ray_heavy")
    if leap_total > ray_total:
        buckets.append("leap_heavy")
    if ray_total and leap_total:
        buckets.append("mixed")
    if max_steps >= 5:
        buckets.append("long_ray")
    if max_span <= 2:
        buckets.append("short_range")
    if len(directions) >= 8:
        buckets.append("high_direction")
    if len(directions) <= 2:
        buckets.append("low_direction")
    if forward_heavy:
        buckets.append("forward_asymmetric")
    if symmetric:
        buckets.append("symmetric")
    return tuple(buckets)


def promotion_buckets(compiled: CompiledRuleSet) -> tuple[str, ...]:
    promotable = [pt for pt in compiled.piece_types if pt.is_promotable]
    if not promotable:
        return ("no_promotion",)
    buckets = []
    counts = {len(pt.promotion_target_ids) for pt in promotable}
    if all(c == 1 for c in counts):
        buckets.append("single_target")
    if any(c >= 2 for c in counts):
        buckets.append("multi_target")
    if any(compiled.promotion_allowed[t.type_id][0] for t in promotable):
        buckets.append("voluntary")
    if any(compiled.promotion_forced[t.type_id][0] for t in promotable):
        buckets.append("forced")
    return tuple(buckets)


def drop_buckets(compiled: CompiledRuleSet) -> tuple[str, ...]:
    droppable = [
        tid
        for tid, masks in compiled.drop_allowed.items()
        if any(any(mask) for mask in masks)
    ]
    if not droppable:
        return ("no_drop",)
    buckets = []
    all_true = all(all(m) for tid in droppable for m in compiled.drop_allowed[tid])
    buckets.append("drop_all" if all_true else "drop_restricted")
    if len(droppable) >= 3:
        buckets.append("multi_type_drop")
    return tuple(buckets)


def classify_ruleset(compiled: CompiledRuleSet, spec: RuleSetFixtureSpec) -> RuleSetFixtureSpec:
    """Return the spec with geometry-derived classification buckets filled in."""
    return replace(
        spec,
        movement_buckets=movement_buckets(compiled),
        promotion_buckets=promotion_buckets(compiled),
        drop_buckets=drop_buckets(compiled),
    )


def build_manifest(
    suite_name: str,
    specs: tuple[RuleSetFixtureSpec, ...],
    positions: list,
    commit: str,
) -> SuiteManifest:
    return SuiteManifest(
        schema_version=SUITE_SCHEMA_VERSION,
        suite_version=f"{suite_name}-v1",
        generator_version=GENERATOR_VERSION,
        commit=commit,
        rulesets=tuple(specs),
        positions=tuple(positions),
    )
