"""Rebuild the published small child graph and short actual-history tree via Core.

No pickle, saved graph or executed producer source is loaded. Partial parent
graphs are never upgraded. This is shared-Core verification, not another engine.
"""
import argparse
from collections import Counter, deque
import gzip
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path.cwd()))
from scripts.leaper_design import compile_rule, ruleset_from_dict, GameSession, state_sha
from scripts.leaper_retrograde import fresh_state, attractor
from scripts.leaper_microgames import role_stop_requested
from generic_chess.core.actions import action_to_dict
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.transition import legal_successors
from generic_chess.session.serialization import deserialize_game_record


def replay(compiled, record):
    return GameSession.replay(compiled, deserialize_game_record(json.dumps(record))).state


def value(state, actor):
    result = state.terminal_status
    return 0 if result.winner is None else 1 if result.winner == actor else -1


def verify(packet, cap=240):
    start = time.perf_counter()
    data = json.loads(gzip.decompress(packet.read_bytes()))
    def guard():
        if role_stop_requested() or time.perf_counter() - start >= cap:
            raise RuntimeError('verification incomplete: role stop or fixed time cap')

    direct = data['direct_clock']
    case = next(x for x in data['parent']['manifest'] if x['world'] == direct['world'])
    compiled = compile_rule(ruleset_from_dict(case['rule']))
    root = replay(compiled, direct['record'])
    assert state_sha(root) == direct['root']
    assert case['rule']['max_ply'] - root.ply_count == direct['remaining']
    # The original counter counts recursive descendants; root dispatch is separate.
    visits = 0
    reasons = Counter()
    def solve(state):
        nonlocal visits
        visits += 1
        guard()
        if state.terminal_status.is_terminal:
            reasons[str(state.terminal_status.status)] += 1
            return value(state, state.position.side_to_move)
        return max(-solve(child) for _, child in legal_successors(state, compiled))
    branches = [dict(action=action_to_dict(action), WDL=-solve(child))
                for action, child in legal_successors(root, compiled)]
    assert branches == direct['actions']
    assert max(x['WDL'] for x in branches) == direct['root_WDL']
    assert visits == direct['visits'] and dict(reasons) == direct['terminal_reasons'], (visits, dict(reasons), direct['visits'], direct['terminal_reasons'])

    child = data['child']
    result = child['rows'][0]
    case = next(x for x in child['manifest'] if x['world'] == result['world'])
    compiled = compile_rule(ruleset_from_dict(case['rule']))
    root = replay(compiled, case['record'])
    assert state_sha(root) == result['id']
    assert max(n for _, n in root.repetition_counts) <= 2
    positions = [root.position]
    index = {root.position: 0}
    edges, actions, terminals = [], [], {}
    for number, position in enumerate(positions):
        guard()
        assert number < 120000
        state = fresh_state(position, compiled)
        if state.terminal_status.is_terminal:
            terminals[number] = value(state, position.side_to_move)
            edges.append(())
            actions.append(())
            continue
        successors = list(legal_successors(state, compiled))
        children = []
        for _, successor in successors:
            if successor.position not in index:
                index[successor.position] = len(positions)
                positions.append(successor.position)
            children.append(index[successor.position])
        edges.append(tuple(children))
        actions.append(tuple(action_to_dict(a) for a, _ in successors))
    values, ranks = attractor(edges, terminals)
    # Check every local Bellman/rank equation, independently of the producer.
    for number, successors in enumerate(edges):
        if number in terminals:
            assert values[number] == terminals[number]
        else:
            assert values[number] == max(-values[c] for c in successors)
            if values[number] == 1:
                assert ranks[number] == 1 + min(ranks[c] for c in successors if values[c] == -1)
            elif values[number] == -1:
                assert ranks[number] == 1 + max(ranks[c] for c in successors)
    remaining = case['rule']['max_ply'] - root.ply_count
    def bound(number, left):
        if number in terminals or values[number] == 0:
            return values[number]
        return 0 if ranks[number] > left else values[number]
    actual = list(legal_successors(root, compiled))
    labels = []
    for (action, state), number in zip(actual, edges[0]):
        assert action_to_dict(action) == actions[0][len(labels)]
        answer = value(state, root.position.side_to_move) if state.terminal_status.is_terminal else -bound(number, remaining - 1)
        labels.append([answer, answer])
    assert labels == [x['bounds'] for x in result['labels']['actions']]
    parents = [[] for _ in positions]
    for number, successors in enumerate(edges):
        for c in successors:
            parents[c].append(number)
    reachable = {n for n, v in terminals.items() if v}
    pending = deque(reachable)
    while pending:
        for parent in parents[pending.popleft()]:
            if parent not in reachable:
                reachable.add(parent)
                pending.append(parent)
    structural = len(positions) - len(reachable)
    claim = child['parent_bound']
    assert structural == claim['structural_draw_entries'] and (0 not in reachable) == claim['root_structural_draw']
    assert len(positions) == result['positions'] == claim['graph_entries']
    assert sum(map(len, edges)) == result['edges'] == claim['edges']
    parent_case = next(x for x in data['parent']['manifest'] if x['world'] == case['world'])
    parent = replay(compiled, parent_case['record'])
    chosen = [(a, s) for a, s in legal_successors(parent, compiled) if action_to_dict(a) == claim['parent_action']]
    assert len(chosen) == 1 and chosen[0][1] == root
    assert max(x[0] for x in labels) == 0 and claim['parent_root_bounds_after_this_child'] == [0, 1]
    assert all(x['labels'] is None for x in data['parent']['rows'] if x['status'] != 'COMPLETE')
    return dict(status='PASS', seconds=time.perf_counter()-start, actual_history_visits=visits,
                positions=len(positions), edges=sum(map(len, edges)), structural_deadzone=structural,
                child_action_bounds=labels, parent_bounds=[0, 1],
                scope='Shared-Core complete child graph and direct clock tree rebuilt; partial parents remain UNKNOWN. No new fitness or independent engine.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('packet', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.packet)
    args.output.write_text(json.dumps(result, indent=2), encoding='utf8')
    print(json.dumps(result))
