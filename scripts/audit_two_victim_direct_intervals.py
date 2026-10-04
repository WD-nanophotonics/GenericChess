"""One frozen global-budget direct H2 pilot; no formula-use labels."""
from dataclasses import asdict, replace
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from generic_chess.core.pieces import Piece
from generic_chess.core.semantic_executor import semantic_engine_for, _semantic_public_action
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_exchange_custody import synthetic_state
from scripts.owned_service_reward import binding_reward, public_child_reward
from scripts.owned_tag_trace import trace_tag
from scripts.public_goal_intervals import PublicGame

PROTOCOL = 'docs/research/TWO_VICTIM_DIRECT_INTERVAL_PILOT.md'
PROTOCOL_SHA = 'e1922eeb5dbcfa0c51f33e8af348bf75ad0a9d68774bc9db487988b9e06714d7'
PREFLIGHT = 'docs/research/data/two_victim_preflight_20261004.json'
TYPES = ('P', 'N', 'B', 'R', 'Q')


class Limit(Exception):
    pass


def aggregate(rows):
    """Fixed mass even for unvisited roots; intervals never drop a suffix."""
    result = {}
    for kind in TYPES:
        subset = [r for r in rows if r['type'] == kind]
        if len(subset) != 24:
            raise ValueError('exact frozen24 roots/type required')
        low = high = F(0)
        for row in subset:
            if row.get('first_complete'):
                lo, hi = row['future_interval']
                low += (row['first_mean']+lo)/24
                high += (row['first_mean']+hi)/24
            else:
                high += F(2, 24)
        result[kind] = {'raw_interval': (low, high), 'common_scaled_interval': (low/2, high/2),
                        'first_complete_roots': sum(r.get('first_complete', False) for r in subset)}
    return result


def audit(report):
    started = monotonic()
    if hashlib.sha256((ROOT/PROTOCOL).read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError('frozen protocol drift')
    original = json.loads((ROOT/PREFLIGHT).read_text())
    for path, expected in original['source_sha256'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest() != expected:
            raise ValueError('preflight input drift')
    if not original['complete'] or original['eligible_layout_pairs'] != 12:
        raise ValueError('complete common eligibility required')
    def check():
        if monotonic()-started >= 15:
            raise Limit('15-second global time cap')
    def tick():
        check()
        if report['enumerated'] >= 5000:
            raise Limit('5000 global public/binding enumeration cap')
        report['enumerated'] += 1
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    game = PublicGame(compiled); engine = semantic_engine_for(compiled)

    def choices(state, tag):
        if game.terminal(state).is_terminal:
            raise ValueError('cannot enumerate terminal service')
        public = {}
        for action in game.actions(state, check):
            tick(); key = str(action)
            if key in public:
                raise ValueError('lossless public key collision')
            if len(public) >= 128:
                raise Limit('128 choices/state cap')
            public[key] = action
        bindings = {}; rewards = {}
        for runtime, binding in engine.iter_legal_action_bindings(state.position, checkpoint=check):
            tick(); key = str(_semantic_public_action(engine, runtime))
            if key in bindings:
                raise ValueError('lossless binding key collision')
            if len(bindings) >= 128:
                raise Limit('128 binding choices/state cap')
            bindings[key] = (runtime, binding)
            rewards[key] = binding_reward(engine, state.position, runtime, binding, tag)
        if public.keys() != bindings.keys() or not public:
            raise ValueError('complete public/binding correspondence required')
        return public, bindings, rewards

    def transition(state, tag, table, key):
        check()
        if report['public_transitions'] >= 128:
            raise Limit('128 global public transition cap')
        report['transition_attempts'] += 1
        child = game.successor(state, table[0][key]); report['public_transitions'] += 1
        check()
        control = public_child_reward(state.position, child.position, table[0][key], tag, compiled.support.type_metadata)
        if control != table[2][key]:
            raise AssertionError('binding reward/public child mismatch')
        runtime, binding = table[1][key]
        new_tag = trace_tag(engine, state.position, child.position, runtime, binding, tag)
        if len(child.history) != len(state.history)+1 or child.ply_count != state.ply_count+1:
            raise ValueError('actual history/ply must advance')
        return child, new_tag

    layouts = [tuple(x['displacement']) for x in original['layouts']]
    report['roots'] = [{'type': t, 'displacement': v, 'owner': owner,
                        'first_complete': False, 'future_interval': (F(0), F(1)), 'branches': []}
                       for t in TYPES for v in layouts for owner in (0, 1)]
    roots = []
    try:
        for row in report['roots']:
            check(); df, dr = row['displacement']; flip = row['owner']; kind = row['type']
            board = [None]*64
            for s, owner, t in ((0, 0, 'K'), (55, 1, 'K'), (27, 0, kind),
                               ((3+dr)*8+3+df, 1, 'P'), ((3-dr)*8+3-df, 1, 'P')):
                if flip:
                    s = (7-s//8)*8+s%8; owner = 1-owner
                if board[s] is not None:
                    raise ValueError('frozen layout collision')
                board[s] = Piece(owner, t, t, False)
            position = replace(initial_state(compiled).position, board=tuple(board), side_to_move=flip,
                aux_state=(((0, -1), 0), ((1, -1), 0), ((2, -1), None), ((3, -1), 0), ((4, -1), 0)))
            state = synthetic_state(compiled, position)
            if game.terminal(state).is_terminal:
                raise ValueError('preflight eligibility changed')
            square = (7-27//8)*8+27%8 if flip else 27
            tag = {'owner': flip, 'base': kind, 'board': {square: F(1)}, 'held': F(0), 'lost': F(0)}
            table = choices(state, tag)
            row.update(first_complete=True, first_mean=sum(table[2].values(), F(0))/len(table[0]),
                       first_reward_sum=sum(table[2].values(), F(0)), complete_A=len(table[0]),
                       first_rewards=table[2], state_sha256=hashlib.sha256(json.dumps(asdict(state), sort_keys=True, default=str).encode()).hexdigest())
            roots.append((row, state, tag, table))
        report['all_first_rewards_complete'] = True
        for row, state, tag, table in roots:
            A = len(table[0])
            # Default future is exactly the sum of A original branch[0,1]/A.
            own_bounds = {key: (F(0), F(1)) for key in table[0]}
            for key in sorted(table[0]):
                check(); child, next_tag = transition(state, tag, table, key)
                branch = {'own_choice': key, 'first_reward': table[2][key], 'opponent_rows': [], 'interval': (F(0), F(1))}
                row['branches'].append(branch)
                if game.terminal(child).is_terminal or next_tag['lost'] == 1:
                    own_bounds[key] = (F(0), F(0)); branch['interval'] = own_bounds[key]
                else:
                    replies = choices(child, next_tag); B = len(replies[0]); branch['complete_B'] = B
                    reply_bounds = {reply: (F(0), F(1)) for reply in replies[0]}
                    for reply in sorted(replies[0]):
                        grandchild, final_tag = transition(child, next_tag, replies, reply)
                        entry = {'opponent_choice': reply, 'interval': (F(0), F(1)), 'tag_lost': final_tag['lost'],
                                 'state_sha256': hashlib.sha256(json.dumps(asdict(grandchild), sort_keys=True, default=str).encode()).hexdigest()}
                        branch['opponent_rows'].append(entry)
                        if game.terminal(grandchild).is_terminal or final_tag['lost'] == 1:
                            expected = F(0); entry['endpoint_zero'] = True
                        else:
                            second = choices(grandchild, final_tag)
                            expected = sum(second[2].values(), F(0))/len(second[0])
                            entry.update(complete_next_A=len(second[0]), next_rewards=second[2])
                        reply_bounds[reply] = (expected, expected); entry['interval'] = reply_bounds[reply]
                        own_bounds[key] = tuple(sum(p[i] for p in reply_bounds.values())/B for i in (0, 1))
                        branch['interval'] = own_bounds[key]
                        row['future_interval'] = tuple(sum(p[i] for p in own_bounds.values())/A for i in (0, 1))
                row['future_interval'] = tuple(sum(p[i] for p in own_bounds.values())/A for i in (0, 1))
        report['complete_exact_H2'] = True
    except Limit as error:
        report['stop_reason'] = str(error)
    finally:
        report['component_intervals'] = aggregate(report['roots'])
        report['seconds'] = monotonic()-started
        report['budgeted_observation_preserved'] = True


if __name__ == '__main__':
    target = ROOT/'docs/research/data/two_victim_direct_intervals_20261004.json'
    if not target.parent.is_dir() or target.exists():
        raise ValueError('actual destination preflight; preserve previous observation')
    report = {'public_transitions': 0, 'transition_attempts': 0, 'enumerated': 0,
              'all_first_rewards_complete': False, 'complete_exact_H2': False, 'budgeted_observation_preserved': False}
    try:
        audit(report)
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
    paths = [PROTOCOL, PREFLIGHT, 'scripts/audit_two_victim_direct_intervals.py', 'scripts/owned_service_reward.py',
             'scripts/owned_tag_trace.py', 'scripts/finite_owned_service.py', 'scripts/audit_exchange_custody.py',
             'scripts/public_goal_intervals.py', 'generic_chess/core/semantic_executor.py',
             'generic_chess/core/transition.py', 'generic_chess/rules/western_chess.py']
    report['source_sha256'] = {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
    target.write_text(json.dumps(report, indent=2, default=str)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('roots', 'source_sha256')}, default=str))
