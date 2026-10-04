"""Frozen sparse Shogi path/identity controls; not prices or goal labels."""
from collections import Counter
from dataclasses import asdict, replace
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import sys
from time import monotonic
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from generic_chess.core.actions import action_source_square, action_target_square
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from generic_chess.core.semantic_executor import semantic_engine_for, _semantic_public_action
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_exchange_custody import synthetic_state
from scripts.owned_service_reward import binding_reward, public_child_reward
from scripts.owned_tag_trace import trace_tag
from scripts.public_goal_intervals import PublicGame
from scripts.resource_mode_context import resource_ledger
PROTOCOL = 'docs/research/SHOGI_TARGET_ROLE_CONTROL_PROTOCOL.md'
SHA = '5061b3453ceb3182e33f427db7df0a71030c7ada83e7ff9ca8f128ec6da3763f'
CASES = [('board', 'P', 'P', 0), ('board', 'L', 'L', 0), ('board', 'N', 'N', 0), ('board', 'P', 'TP', 0),
         ('hand', 'P', 'P', 1), ('hand', 'P', 'P', 2), ('hand', 'L', 'L', 1), ('hand', 'L', 'L', 2),
         ('hand', 'N', 'N', 1), ('hand', 'N', 'N', 2)]


class Limit(Exception):
    pass


def audit(report):
    start = monotonic()
    if hashlib.sha256((ROOT/PROTOCOL).read_bytes()).hexdigest() != SHA:
        raise ValueError('frozen protocol drift')
    def check():
        if monotonic()-start >= 15:
            raise Limit('15-second global cap')
    def tick():
        check()
        if report['enumerated'] >= 5000:
            raise Limit('5000 global enumeration cap')
        report['enumerated'] += 1
    compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    game = PublicGame(compiled); engine = semantic_engine_for(compiled)
    initial_stock = Counter(p.base_type_id for p in compiled.initial_position.board if p)

    def table(state, tag):
        if game.terminal(state).is_terminal:
            raise ValueError('required ongoing witness is terminal')
        public = {}
        for a in game.actions(state, check):
            tick(); key = str(a)
            if key in public or len(public) >= 128:
                raise ValueError('unique complete<=128 action set required')
            public[key] = a
        bindings = {}; rewards = {}
        for runtime, binding in engine.iter_legal_action_bindings(state.position, checkpoint=check):
            tick(); key = str(_semantic_public_action(engine, runtime))
            if key in bindings or len(bindings) >= 128:
                raise ValueError('unique complete<=128 bindings required')
            bindings[key] = (runtime, binding)
            rewards[key] = binding_reward(engine, state.position, runtime, binding, tag)
        if not public or public.keys() != bindings.keys():
            raise ValueError('public/binding complete identity mismatch or unsupported Session claim')
        return public, bindings, rewards

    def select(table, predicate):
        matches = [k for k, a in table[0].items() if predicate(a)]
        if len(matches) != 1:
            raise ValueError('unique predetermined legal witness missing')
        return matches[0]

    def square(action, target=False):
        s = (action_target_square if target else action_source_square)(action)
        return None if s is None else s.rank*9+s.file

    def step(state, tag, choices, key):
        check()
        if report['public_transitions'] >= 40:
            raise Limit('40 global transition cap')
        child = game.successor(state, choices[0][key]); report['public_transitions'] += 1
        reward = public_child_reward(state.position, child.position, choices[0][key], tag, compiled.support.type_metadata)
        if reward != choices[2][key]:
            raise AssertionError('independent reward mismatch')
        runtime, binding = choices[1][key]
        next_tag = trace_tag(engine, state.position, child.position, runtime, binding, tag)
        if len(child.history) != len(state.history)+1 or child.ply_count != state.ply_count+1:
            raise ValueError('actual history not advanced')
        game.terminal(child); check()
        return child, next_tag, reward

    try:
        for row in report['rows']:
            check(); location, base, current, n = row['case']; owner = row['owner']
            transform = lambda s: (8-s//9)*9+s%9 if owner else s
            board = [None]*81
            for s, player, b, t in [(0, 0, 'K', 'K'), (71, 1, 'K', 'K'), (49, 1, 'P', 'P'), (59, 1, 'P', 'P')]:
                board[transform(s)] = Piece(1-player if owner else player, b, t, b != t)
            hands = [Hands(), Hands()]
            if location == 'board':
                board[transform(40)] = Piece(owner, base, current, base != current)
            else:
                hands[owner] = Hands(((base, n),))
            position = replace(initial_state(compiled).position, board=tuple(board), hands=tuple(hands), side_to_move=owner)
            state = synthetic_state(compiled, position)
            try:
                resource_ledger(compiled, position, 'shogi')
            except ValueError as error:
                if 'global base inventory' not in str(error):
                    raise
            else:
                raise ValueError('sparse state must not be claimed full inventory')
            actual = Counter(p.base_type_id for p in position.board if p)
            for hand in position.hands:
                actual.update(dict(hand.items()))
            row['missing_base_inventory'] = dict(initial_stock-actual)
            row['missing_tokens'] = sum((initial_stock-actual).values())
            if row['missing_tokens'] != (34 if n == 2 else 35):
                raise ValueError('declared resource deficit mismatch')
            tag = {'owner': owner, 'base': base, 'board': {transform(40): F(1)} if location == 'board' else {},
                   'held': F(int(location == 'hand')), 'lost': F(0)}
            row['root_state'] = asdict(state)
            choices = table(state, tag); row['complete_first_choices'] = len(choices[0])
            target = transform(59 if current == 'N' and location == 'board' else 49)
            if location == 'hand':
                chosen = select(choices, lambda a: square(a) is None and square(a, True) == transform(40)
                                and getattr(a, 'base_type_id', None) == base)
            else:
                chosen = select(choices, lambda a: square(a) == transform(40) and square(a, True) == target
                                and getattr(a, 'promotion_target_id', None) is None)
            row['first_choice'] = chosen
            state, tag, r1 = step(state, tag, choices, chosen)
            row.update(first_reward=r1, after_first_tag=tag.copy())
            if location == 'hand' and tag['board'] != {transform(40): F(1, n)}:
                raise AssertionError('drop tag must use q/n')
            choices = table(state, tag); row['complete_reply_choices'] = len(choices[0])
            chosen = select(choices, lambda a: square(a) == transform(71) and square(a, True) == transform(80)
                            and getattr(a, 'promotion_target_id', None) is None)
            row['opponent_choice'] = chosen
            state, tag, _ = step(state, tag, choices, chosen)
            choices = table(state, tag)
            row.update(after_reply_tag=tag, final_state=asdict(state), complete_next_choices=len(choices[0]),
                       next_reward_sum=sum(choices[2].values(), F(0)),
                       next_reward_choices={k: r for k, r in choices[2].items() if r},
                       next_expected_reward=sum(choices[2].values(), F(0))/len(choices[0]), complete=True)
        report['all_controls_complete'] = True
    except Limit as error:
        report['stop_reason'] = str(error)
    finally:
        report['seconds'] = monotonic()-start


if __name__ == '__main__':
    target = ROOT/'docs/research/data/shogi_target_role_controls_20261004.json'
    if not target.parent.is_dir() or target.exists():
        raise ValueError('actual destination; no completed control rerun')
    report = {'rows': [{'case': case, 'owner': owner, 'complete': False} for case in CASES for owner in (0, 1)],
              'enumerated': 0, 'public_transitions': 0, 'all_controls_complete': False}
    paths = [PROTOCOL, 'scripts/audit_shogi_target_role_controls.py', 'scripts/owned_service_reward.py',
             'scripts/owned_tag_trace.py', 'scripts/finite_owned_service.py', 'scripts/audit_exchange_custody.py',
             'scripts/resource_mode_context.py', 'scripts/public_goal_intervals.py',
             'generic_chess/rules/standard_shogi.py', 'generic_chess/core/semantic_executor.py']
    report['source_sha256'] = {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
    try:
        audit(report)
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
    target.write_text(json.dumps(report, indent=2, default=str)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('rows', 'source_sha256')}))
    print(json.dumps([{k: v for k, v in r.items() if k in ('case', 'owner', 'complete', 'complete_first_choices',
                      'complete_next_choices', 'first_reward', 'next_reward_sum', 'next_expected_reward')} for r in report['rows']], default=str))
