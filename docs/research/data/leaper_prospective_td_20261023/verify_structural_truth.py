"""Rebuild the two frozen structural components and check supplied history labels."""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path.cwd()))
from scripts.leaper_design import compile_rule, ruleset_from_dict, GameSession, state_sha, floor_type_map, FLOOR_COUPLING
from scripts.leaper_retrograde import fresh_state, attractor
from scripts.leaper_microgames import role_stop_requested
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.transition import legal_successors
from generic_chess.core.actions import action_to_dict
from generic_chess.ai.alphabeta.search import terminal_score
from generic_chess.learning.incremental import compile_channels, _material_features, Model


def verify_mechanisms(packet):
    """Independently recompute supplied finite trees, not a new search policy."""
    component = packet['components'][1]
    c = compile_rule(ruleset_from_dict(component['plan']['root']['rule']))
    histories = {r['id']: r for r in component['histories']['rows']}
    counts = Counter()
    for key in ('mechanism', 'allfork_mechanism'):
        data = packet[key]
        weights = list(data['weights'].values())
        for row in data['rows']:
            st = replay(c, histories[row['id']]['record'])
            def values(state, left, ply):
                counts['literal_visits'] += 1
                if role_stop_requested():
                    raise RuntimeError('ROLE_STOP')
                if state.terminal_status.is_terminal:
                    return [float(terminal_score(state.terminal_status, state.position.side_to_move, ply))] * len(weights)
                if left == 0:
                    # Bind material features via the maintained learner environment.
                    phi = _material_features(state.position, c, compile_channels(c, unit_type='A'))
                    sign = 1 if state.position.side_to_move == 0 else -1
                    return [sign * Model(tuple(w) + (0, 0, 0)).raw(phi) for w in weights]
                return list(map(max, zip(*[[-v for v in values(child, left-1, ply+1)] for _, child in legal_successors(state, c)])))
            branches = [dict(action=action_to_dict(a), scores=[-v for v in values(ch, row['depth']-1, 1)]) for a, ch in legal_successors(st, c)]
            assert branches == row['branches']
            for i, name in enumerate(data['weights']):
                best = max(b['scores'][i] for b in branches)
                supported = [j for j, b in enumerate(branches) if b['scores'][i] == best]
                assert supported == row['supports'][name]
                assert [histories[row['id']]['actions'][j]['bounds'][0] for j in supported] == row['exact_WDL_of_supported_actions'][name]
            counts['literal_trees'] += 1
    return dict(counts)


def replay(c, record):
    return GameSession.replay(c, deserialize_game_record(json.dumps(record))).state


def verify(path):
    packet = json.loads(gzip.decompress(path.read_bytes()))
    counts = Counter()
    begun = time.perf_counter()
    for component in packet['components']:
        started = time.perf_counter()
        case = component['plan']['root']
        rule = ruleset_from_dict(case['rule'])
        floor_type_map({'floor_coupling': FLOOR_COUPLING},
                       {'rule': case['rule'], 'floor_type_map': {t.type_id: t.type_id for t in rule.piece_types}})
        c = compile_rule(rule)
        root = replay(c, case['record'])
        assert state_sha(root) == case['id']
        positions = [root.position]
        index = {root.position: 0}
        edges, actions, terminals = [], [], {}
        for number, pos in enumerate(positions):
            if role_stop_requested() or time.perf_counter() - started >= 240:
                raise RuntimeError('verification stopped or capped; no verification success')
            assert number < 120000
            st = fresh_state(pos, c)
            if st.terminal_status.is_terminal:
                result = st.terminal_status
                terminals[number] = 0 if result.winner is None else 1 if result.winner == pos.side_to_move else -1
                edges.append(())
                actions.append(())
                continue
            successors = list(legal_successors(st, c))
            children = []
            for _, child in successors:
                if child.position not in index:
                    index[child.position] = len(positions)
                    positions.append(child.position)
                children.append(index[child.position])
            edges.append(tuple(children))
            actions.append(tuple(action_to_dict(a) for a, _ in successors))
        values, ranks = attractor(edges, terminals)
        for i, children in enumerate(edges):
            if i in terminals:
                assert values[i] == terminals[i]
            else:
                assert values[i] == max(-values[ch] for ch in children)
                if values[i] == 1:
                    assert ranks[i] == 1 + min(ranks[ch] for ch in children if values[ch] == -1)
                elif values[i] == -1:
                    assert ranks[i] == 1 + max(ranks[ch] for ch in children)
        result = component['result']
        assert result['status'] == 'COMPLETE'
        assert len(positions) == result['positions'] and sum(map(len, edges)) == result['edges']
        for stored in component['histories']['rows']:
            state = replay(c, stored['record'])
            assert state_sha(state) == stored['id'] and state.position in index
            prior = max(n for _, n in state.repetition_counts)
            left = rule.max_ply - state.ply_count
            assert (prior, left) == (stored['max_prior'], stored['remaining'])
            def bound(i, remaining):
                v = values[i]
                if i in terminals or v == 0 or ranks[i] > remaining:
                    return [v, v] if i in terminals or v == 0 else [0, 0]
                return [v, v] if prior <= 2 else [0, 1] if v == 1 else [-1, 0]
            branches = []
            for action, child in legal_successors(state, c):
                if child.terminal_status.is_terminal:
                    t = child.terminal_status
                    v = 0 if t.winner is None else 1 if t.winner == state.position.side_to_move else -1
                    bb = [v, v]
                else:
                    lo, hi = bound(index[child.position], left - 1)
                    bb = [-hi, -lo]
                branches.append(dict(action=action_to_dict(action), bounds=bb))
            assert branches == stored['actions']
            best = [max(b['bounds'][j] for b in branches) for j in (0, 1)]
            assert best == stored['bounds']
            for ref in stored['references']:
                served = next(b['bounds'] for b in branches if b['action'] == ref['served_action'])
                assert served == ref['served_bounds']
                assert (served[1] < best[0]) == ref['inferior']
                counts['covered_references'] += 1
                counts['certified_inferior_references'] += ref['inferior']
            counts['distinct_histories'] += 1
        counts['components'] += 1
        counts['positions'] += len(positions)
        counts['edges'] += sum(map(len, edges))
    assert counts['components'] == 2 and counts['covered_references'] == 360
    assert counts['certified_inferior_references'] == 2
    mechanism_counts = verify_mechanisms(packet)
    return dict(status='PASS', seconds=time.perf_counter()-begun, counts=counts, mechanisms=mechanism_counts,
                scope='Both components rebuilt through shared Core; all supplied natural-history labels and action regrets checked. Source forward returns are OLD. No independent engine, new fitness or training.')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('packet', type=Path)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    result = verify(args.packet)
    args.output.write_text(json.dumps(result, indent=2), encoding='utf8')
    print(json.dumps(result))
