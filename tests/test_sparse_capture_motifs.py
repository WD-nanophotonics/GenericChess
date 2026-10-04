from itertools import combinations, product

import pytest

from scripts.sparse_capture_motifs import (
    bitset, capture_masks, extra_token_mask, joint_counts, triple_population,
)
from scripts.intrinsic_action_events import collect_intrinsic_board_events
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset


def explicit_holds(cubes, source, victim, extra, extra_label):
    board = {source: 'own', victim: 'enemy', extra: extra_label}
    return any(all(board.get(s, 'empty') in labels for s, labels in cube) for cube in cubes)


def test_extra_masks_match_explicit_three_token_boards_exhaustively():
    cubes = [(), ((0, ('empty',)),), ((1, ('own', 'enemy')),),
             ((1, ('own',)), (2, ('enemy',))),
             ((0, ('own',)), (3, ('empty',))), ((2, ('enemy',)),)]
    for union_size in (1, 2):
        for union in combinations(cubes, union_size):
            for source, victim, label in product(range(4), range(4), ('own', 'enemy')):
                if source == victim:
                    continue
                actual = extra_token_mask(union, 4, source, victim, label)
                expected = bitset(e for e in range(4) if e not in (source, victim)
                                  and explicit_holds(union, source, victim, e, label))
                assert actual == expected


def test_distinct_triple_inclusion_exclusion_matches_enumeration():
    subsets = [set(c) for n in range(5) for c in combinations(range(4), n)]
    for s, t, u in product(subsets, repeat=3):
        expected = sum(len({a, b, c}) == 3 for a, b, c in product(s, t, u))
        assert triple_population(s, t, u) == expected


def test_shared_blocker_and_joint_counts_use_the_same_population():
    # First ray 0->2 requires square1 empty; the enemy's threat targets square1.
    actor_cubes = (((1, ('empty',)), (2, ('enemy',))),)
    victim_cubes = (((1, ('enemy',)),),)
    actor_masks = {(0, 2): {label: extra_token_mask(actor_cubes, 4, 0, 2, label)
                           for label in ('own', 'enemy')}}
    victim_masks = {(2, 1): {label: extra_token_mask(victim_cubes, 4, 2, 1, label)
                            for label in ('own', 'enemy')}}
    counts = joint_counts({0}, {2}, {1, 3}, actor_masks, victim_masks)
    assert counts == {'population': 2, 'A': 1, 'B': 1, 'joint': 0}
    # Product of SAME-law marginals is1/4 while the exact joint is0.
    with pytest.raises(ValueError, match='empty distinct triple'):
        joint_counts({0}, {0}, {0}, actor_masks, victim_masks)


def test_joint_accounting_matches_independent_explicit_cube_oracle():
    supports = ({0, 1, 2}, {1, 2, 3}, {0, 2, 3})
    actor_events = {(0, 2): (((1, ('empty',)), (2, ('enemy',))),),
                    (1, 3): (((2, ('empty', 'own')), (3, ('enemy',))),)}
    victim_events = {(2, 3): (((3, ('enemy',)),),),
                     (3, 0): (((1, ('empty',)), (2, ('empty',)), (0, ('enemy',))),)}
    def masks(events):
        return {pair: {label: extra_token_mask(cubes, 4, *pair, label)
                       for label in ('own', 'enemy')} for pair, cubes in events.items()}
    result = joint_counts(*supports, masks(actor_events), masks(victim_events))
    population = first = second = joint = 0
    for s, t, u in product(*supports):
        if len({s, t, u}) != 3:
            continue
        a = explicit_holds(actor_events.get((s, t), ()), s, t, u, 'own')
        b = explicit_holds(victim_events.get((t, u), ()), t, u, s, 'enemy')
        population += 1; first += a; second += b; joint += a and b
    assert result == {'population': population, 'A': first, 'B': second, 'joint': joint}


def test_compiled_rook_path_blocks_both_extra_owners():
    compiled = compile_semantic_ruleset(build_western_chess_ruleset())
    supports, edges, masks = capture_masks(collect_intrinsic_board_events(compiled, 'R'), 64)
    assert (0, 16) in edges[0] and 0 in supports[0]
    for label in ('own', 'enemy'):
        assert not masks[0][0, 16][label] & (1 << 8)
        assert masks[0][0, 16][label] & (1 << 9)
    with pytest.raises(ValueError, match='valid distinct'):
        extra_token_mask((), 64, 0, 0, 'own')
