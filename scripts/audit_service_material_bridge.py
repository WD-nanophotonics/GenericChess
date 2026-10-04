"""Exact service/goal separation and static projection premise certificate."""
from dataclasses import dataclass
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / 'docs/research/SERVICE_MATERIAL_BRIDGE_PROTOCOL.md'
PROTOCOL_SHA = '0677157bb4e9f9a797e6697c48aa27520bcaa20a7b425a4f3a06c6dd0b66ff8b'


@dataclass(frozen=True)
class Node:
    owner: int
    tokens: tuple
    edges: tuple = ()  # action, captured token ID or None, successor key
    winner: int | None = None


def graph():
    nodes = {}
    for context, winner in (('plus', 0), ('minus', 1)):
        prefix = lambda phase: (context, phase)
        for phase in range(5):
            edges = () if phase == 4 else (('capture' if phase == 0 else 'pass',
                                           'j' if phase == 0 else None, prefix(phase + 1)),)
            nodes[prefix(phase)] = Node(phase % 2, (('i', 0), ('j', 1)) if phase == 0 else (('i', 0),),
                                       edges, winner if phase == 4 else None)
    return nodes


def exact_values(nodes):
    memo = {}; active = set()
    def visit(key):
        if key in memo:
            return memo[key]
        if key in active:
            raise ValueError('cyclic graph outside complete finite toy')
        active.add(key); node = nodes[key]
        if node.winner is not None:
            if node.edges:
                raise ValueError('terminal node has successors')
            result = F(1 if node.winner == 0 else -1)
        else:
            if not node.edges:
                raise ValueError('ongoing empty action set')
            values = [visit(target) for _, _, target in node.edges]
            result = (max if node.owner == 0 else min)(values)
        active.remove(key); memo[key] = result
        return result
    for key in nodes:
        visit(key)
    return memo


def secured_capture(nodes, root):
    result = False
    for _, victim, target in nodes[root].edges:
        if victim is None or dict(nodes[root].tokens).get(victim) != 1:
            continue
        child = nodes[target]
        if dict(child.tokens).get('i') != 0 or dict(child.tokens).get(victim) == 1:
            raise ValueError('declared capture trajectory invalid')
        if child.winner is not None:
            good = child.winner == 0
        else:
            if not child.edges:
                raise ValueError('ongoing empty reply set')
            good = all(dict(nodes[key].tokens).get('i') == 0 and dict(nodes[key].tokens).get(victim) != 1
                       and (nodes[key].winner is None or nodes[key].winner == 0) for _, _, key in child.edges)
        result |= good
    return int(result)


def weighted_mean(values, weights):
    if sum(weights) != 1 or any(w < 0 for w in weights):
        raise ValueError('probability weights required')
    return sum((v * w for v, w in zip(values, weights)), F())


def covariance(features, weights):
    means = [weighted_mean([x[t] for x in features], weights) for t in range(len(features[0]))]
    return [[weighted_mean([(x[a] - means[a]) * (x[b] - means[b]) for x in features], weights)
             for b in range(len(means))] for a in range(len(means))]


def rank(matrix):
    rows = [[F(x) for x in row] for row in matrix]; pivot = 0
    for column in range(len(rows[0])):
        chosen = next((r for r in range(pivot, len(rows)) if rows[r][column]), None)
        if chosen is None:
            continue
        rows[pivot], rows[chosen] = rows[chosen], rows[pivot]
        scale = rows[pivot][column]; rows[pivot] = [x / scale for x in rows[pivot]]
        for r in range(len(rows)):
            if r != pivot:
                factor = rows[r][column]
                rows[r] = [x - factor * y for x, y in zip(rows[r], rows[pivot])]
        pivot += 1
        if pivot == len(rows):
            break
    return pivot


def squared_risk(labels, predictions, weights):
    return weighted_mean([(y - p)**2 for y, p in zip(labels, predictions)], weights)


def audit(seconds=5):
    started = monotonic()
    if hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError('frozen bridge protocol changed')
    nodes = graph(); values = exact_values(nodes)
    roots = [('plus', 0), ('minus', 0)]
    labels = [values[key] for key in roots]
    service = [secured_capture(nodes, key) for key in roots]
    features = [(F(1), F(-1))] * 2
    weights = [F(1, 2)] * 2
    if labels != [F(1), F(-1)] or service != [1, 1] or len(nodes) > 16:
        raise ValueError('counterexample contract mismatch')
    mean = weighted_mean(labels, weights)
    minimum = squared_risk(labels, [mean] * 2, weights)
    candidates = {str(c): str(squared_risk(labels, [c] * 2, weights)) for c in (F(-1), F(-1, 2), F(0), F(1, 2), F(1))}
    if any(F(r) != 1 + F(c)**2 for c, r in candidates.items()):
        raise ValueError('risk identity mismatch')
    control_x = [(F(1), F(0)), (F(-1), F(0)), (F(0), F(1)), (F(0), F(-1))]
    control_weights = [F(1, 4)] * 4
    control_w = (F(1, 2), F(1, 4))
    control_y = [sum((x * w for x, w in zip(row, control_w)), F()) for row in control_x]
    zero_risk = squared_risk(control_y, control_y, control_weights)
    if minimum != 1 or rank(covariance(features, weights)) != 0 or rank(covariance(control_x, control_weights)) != 2 or zero_risk:
        raise ValueError('projection/identifiability certificate mismatch')
    if monotonic() - started > seconds:
        raise TimeoutError('bridge proof time cap')
    return {'protocol_sha256': PROTOCOL_SHA, 'program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'complete': True, 'toy_states': len(nodes), 'goal_labels': list(map(str, labels)),
            'local_service_labels': service, 'equal_feature_vector': ['1', '-1'],
            'optimal_constant': str(mean), 'unavoidable_goal_risk': str(minimum),
            'constant_prediction_risks': candidates, 'same_inventory_covariance_rank': 0,
            'full_rank_control_covariance_rank': 2, 'control_slopes': list(map(str, control_w)),
            'control_risk': str(zero_risk), 'elapsed_seconds': monotonic() - started}


if __name__ == '__main__':
    result = audit()
    Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(result, indent=2))
