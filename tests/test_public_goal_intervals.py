"""Independent complete-game oracle and public-state soundness controls."""
from dataclasses import dataclass, replace
from itertools import product
from hashlib import sha256
import json
from pathlib import Path

import pytest

from generic_chess.core.movegen import legal_actions
from generic_chess.core.terminal import TerminalResult, TerminalStatus as T
from generic_chess.core.transition import apply_action, initial_state
from scripts.f156_known_game_shallow_search_equivalence import _western_pair, _western_state
from scripts.audit_chess_root_terminal_labels import FEN
from scripts.public_goal_intervals import PublicGame, observe


@dataclass(frozen=True)
class Node:
    owner: int
    children: tuple = ()
    result: TerminalResult = TerminalResult(T.ONGOING)


class TinyGame:
    def terminal(self, node):
        return node.result

    def owner(self, node):
        return node.owner

    def actions(self, node, checkpoint):
        for index in range(len(node.children)):
            checkpoint()
            yield index

    def successor(self, node, index):
        return node.children[index]


def leaf(value):
    return Node(0, result=TerminalResult(T.STALEMATE if value == 0 else T.CHECKMATE,
                                       None if value == 0 else 0 if value == 1 else 1))


def oracle(node):
    if node.result.is_terminal:
        return 0 if node.result.winner is None else 1 if node.result.winner == 0 else -1
    values = [oracle(child) for child in node.children]
    return (max if node.owner == 0 else min)(values)


def test_every_small_tree_budget_contains_independent_exact_value():
    for owner, replies, outcomes in product((0, 1), (0, 1), product((-1, 0, 1), repeat=3)):
        inner = Node(replies, (leaf(outcomes[1]), leaf(outcomes[2])))
        for children in ((leaf(outcomes[0]), inner), (inner, leaf(outcomes[0]))):
            root = Node(owner, children)
            exact = oracle(root)
            for depth, transitions, visits in product(range(4), range(6), (0, 1, 3, 6)):
                result = observe(root, TinyGame(), depth=depth, max_transitions=transitions,
                                 max_visits=visits, clock=lambda: 0)
                lo, hi = result['interval']
                assert lo <= exact <= hi
                assert result['transitions'] <= transitions and result['visits'] <= visits
            full = observe(root, TinyGame(), depth=3, max_transitions=10, clock=lambda: 0)
            assert full['interval'] == (exact, exact)


def test_missing_actions_are_unknown_not_draw_or_empty_min():
    maximum = Node(0, (leaf(0), leaf(-1)))
    minimum = Node(1, (leaf(0), leaf(1)))
    assert observe(maximum, TinyGame(), depth=1, max_transitions=1)['interval'] == (0, 1)
    assert observe(minimum, TinyGame(), depth=1, max_transitions=1)['interval'] == (-1, 0)
    with pytest.raises(ValueError, match='empty legal'):
        observe(Node(0), TinyGame(), depth=1)


def test_cooperative_time_interruptions_preserve_soundness():
    root = Node(0, (leaf(0), Node(1, (leaf(-1), leaf(1)))))
    exact = oracle(root)
    for allowed_calls in range(18):
        count = 0
        def clock():
            nonlocal count
            count += 1
            return 0 if count <= allowed_calls else 6
        result = observe(root, TinyGame(), depth=3, seconds=5, clock=clock)
        assert result['interval'][0] <= exact <= result['interval'][1]


def test_censoring_and_no_contest_are_not_zero_labels():
    capped = Node(0, result=TerminalResult(T.MAX_PLY))
    assert observe(capped, TinyGame(), depth=0)['interval'] == (0, 0)
    assert observe(capped, TinyGame(), depth=0, censored_statuses=(T.MAX_PLY,))['interval'] == (-1, 1)
    assert observe(Node(0, result=TerminalResult(T.NO_CONTEST)), TinyGame(), depth=0)['interval'] == (-1, 1)
    with pytest.raises(ValueError, match='censor'):
        observe(capped, TinyGame(), depth=0, censored_statuses=(T.ONGOING,))
    for kwargs in ({'depth': -1}, {'depth': 0, 'max_visits': 0.5}, {'depth': 0, 'seconds': float('inf')}):
        with pytest.raises(ValueError):
            observe(capped, TinyGame(), **kwargs)


def test_public_terminal_cache_and_history_preserved():
    rules, _ = _western_pair()
    game = PublicGame(rules)
    root = _western_state(rules, FEN)
    with pytest.raises(ValueError, match='stale'):
        observe(replace(root, terminal_status=TerminalResult(T.STALEMATE)), game, depth=1)
    child = game.successor(root, legal_actions(root, rules)[0])
    direct = apply_action(root, legal_actions(root, rules)[0], rules)
    assert child == direct
    assert child.ply_count == 1 and len(child.history) == 2
    assert root.ply_count == 0 and len(root.history) == 1
    assert observe(initial_state(rules), game, depth=1)['interval'] == (-1, 1)


def test_public_checkmate_and_draw_control():
    rules, _ = _western_pair()
    game = PublicGame(rules)
    root = _western_state(rules, FEN)
    assert observe(root, game, depth=1)['interval'] == (1, 1)
    draw = next(child for action in legal_actions(root, rules)
                if (child := apply_action(root, action, rules)).terminal_status.status is T.STALEMATE)
    assert observe(draw, game, depth=0)['interval'] == (0, 0)


@pytest.mark.parametrize('owner', (0, 1))
def test_shogi_winning_declaration_and_restart_scope(owner):
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
    from generic_chess.core.declarations import available_declarations
    from generic_chess.session.session import GameSession
    from test_generic_declaration_semantics import _shogi_boundary_state
    rules = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    game = PublicGame(rules)
    for score in (31, 24):
        state = _shogi_boundary_state(rules, score, owner=owner)
        # The existing fixture has an ongoing cache; qualify it by fresh Core.
        from generic_chess.core.terminal import terminal_result
        state = replace(state, terminal_status=terminal_result(state, rules))
        assessment = available_declarations(state, rules)[0]
        assert assessment.outcome == ('WIN' if score == 31 else 'RESTART')
        session = GameSession(rules)
        session._state = state
        result = session.declare(assessment.declaration_id)
        assert result.declaration_outcome == assessment.outcome
        assert session.state is state
        label = observe(state, game, depth=1, max_transitions=1, max_visits=3)
        expected = ((1, 1) if owner == 0 else (-1, -1)) if score == 31 else (-1, 1)
        assert label['interval'] == expected
        assert label['transitions'] == 1 and label['public_materializations'] == 0
        if score == 31:
            stale = replace(assessment, actor=1-owner)
            with pytest.raises(ValueError, match='stale declaration'):
                game.successor(state, stale)


def test_recorded_certificate_sources_and_contract_match():
    root = Path(__file__).resolve().parents[1]
    record = json.loads((root/'docs/research/data/public_goal_intervals_20261004.json').read_text())
    paths = {'protocol_sha256': 'docs/research/PUBLIC_GOAL_INTERVAL_PROTOCOL.md',
             'declaration_addendum_sha256': 'docs/research/PUBLIC_GOAL_INTERVAL_DECLARATION_ADDENDUM.md',
             'observer_sha256': 'scripts/public_goal_intervals.py'}
    for key, path in paths.items():
        assert record[key] == sha256((root/path).read_bytes()).hexdigest()
    rules, _ = _western_pair()
    assert record['ruleset_fingerprint'] == rules.ruleset_fingerprint
    assert record['controls']['initial']['interval'] == [-1, 1]
    assert record['controls']['existing_mate_root']['interval'] == [1, 1]
