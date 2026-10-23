"""Exact cooperative reachability on existing COMPLETE plain-Leaper caches.

Shorten any cooperative decisive walk to a simple path: this only reduces
repetition counts and clock use. Exclude incoming edges to already thrice-
visited nonterminal Positions; decisive terminal precedence is checked by Core.
Thus shortest graph distance with those exclusions decides existence within
the remaining clock, in this restricted position-independent transition game.
Every positive path is replayed from its actual full history. This is neither
minimax WDL nor a policy-attractor probability. No graph is expanded/refilled.
"""
from __future__ import annotations

import argparse
from collections import Counter, deque, defaultdict
import gzip
import hashlib
import json
import pickle
from pathlib import Path
import time

from generic_chess.core.actions import action_to_dict
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.transition import legal_successors
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from generic_chess.rules.schema import ruleset_from_dict
from scripts.leaper_retrograde import fresh_state
from scripts.leaper_microgames import role_stop_requested
from scripts.leaper_explorer_truth import load, save, digest
from scripts.leaper_design import state_sha


def cooperative_distances(edges, decisive, blocked=()):
    """Shortest cooperative decisive paths; return distance and next vertex.

    ``blocked`` means cannot ENTER unless already decisive. A blocked source
    can still leave, so it receives a distance but is not propagated as a
    possible internal destination. Complete-graph validation is separate.
    """
    n = len(edges)
    decisive, blocked = set(decisive), set(blocked)
    if any(type(i) is not int or not 0 <= i < n for i in decisive | blocked):
        raise ValueError('invalid vertex')
    parents = [[] for _ in edges]
    for i, children in enumerate(edges):
        if children is None:
            raise ValueError('incomplete graph')
        for j in children:
            if type(j) is not int or not 0 <= j < n:
                raise ValueError('unexpanded child')
            parents[j].append(i)
    if any(edges[i] for i in decisive):
        raise ValueError('decisive terminals must be sinks')
    distances, nxt = {i: 0 for i in decisive}, {}
    todo = deque(sorted(decisive))
    while todo:
        j = todo.popleft()
        for i in parents[j]:
            if i not in distances:
                distances[i] = distances[j] + 1
                nxt[i] = j
                if i not in blocked or i in decisive:
                    todo.append(i)
    return distances, nxt


def admit(rule, c):
    """Reject transitions/history policies for which cycle shortening is unsafe."""
    assert rule.board_size == 4 and rule.capture_disposition == 'remove_from_game'
    assert c.repetition_limit == 4 and c.repetition_policy == 'draw' and c.max_ply == 128
    assert not rule.promotion_allowed and not rule.promotion_forced
    assert not any(any(mask) for masks in rule.drop_allowed.values() for mask in masks)
    assert all(not p.is_promotable and all(a.__class__.__name__ == 'LeapAtom' for a in p.movement_atoms) for p in rule.piece_types)
    for field in ('no_progress_draw', 'automatic_adjudications', 'consecutive_action_adjudications', 'repeated_cycle_target_conditions'):
        assert not getattr(c.support, field, None)


def cache_manifest():
    low = Path('artifacts/canonical-history-observer-20261022-attempt2')
    result = {}
    for row in load(low/'summary.json')['worlds']:
        if row['status'] == 'COMPLETE':
            result[row['fingerprint'], 'low'] = low/f"world{row['world']}.pkl.gz"
    for actors in (4, 5):
        folder = Path(f'artifacts/canonical-{actors}actor-truth-20261022')
        for row in load(folder/'summary.json')['components']:
            if row['status'] == 'COMPLETE':
                roster = tuple(tuple(pc) for pc in row['roster'])
                result[row['fingerprint'], roster] = folder/f"component{row['component']}.pkl.gz"
    return result


def run(truth, *, seconds=900, audit_full_graph=True):
    started = time.perf_counter()
    deadline = started + seconds
    rows_by_id = {r['id']: r for r in truth['roots']}
    chosen = sorted({hid for cats in truth['selected'].values() for hid in cats.values() if hid})
    manifest = cache_manifest()
    compiled = {}
    groups = defaultdict(list)
    result = dict(format='leaper-cooperative-truth-v1', selected=chosen,
                  source_truth_digest=digest(truth), caps=dict(seconds=seconds, graphs=30),
                  audit_full_graph=audit_full_graph,
                  rows=[], graph_checks=[], status='CLOSED', scope=__doc__)
    last_stop_check=0.
    def guard():
        nonlocal last_stop_check
        now=time.perf_counter()
        if now >= deadline: raise TimeoutError('CAP_UNKNOWN')
        if now-last_stop_check>=.2:
            last_stop_check=now
            if role_stop_requested(): raise TimeoutError('USER_STOP')
    for hid in chosen:
        row = rows_by_id[hid]
        fp = row['fingerprint']
        if fp not in compiled:
            rule = ruleset_from_dict(truth['rules'][fp]); c = compile_rule(rule); admit(rule, c)
            compiled[fp] = c
        s = GameSession.replay(compiled[fp], deserialize_game_record(json.dumps(truth['records'][row['record_id']] | dict(actions=truth['records'][row['record_id']]['actions'][:row['ply']]))))
        assert state_sha(s.state) == hid
        roster = tuple(sorted((pc.owner, pc.current_type_id) for pc in s.state.position.board if pc and pc.current_type_id != 'K'))
        key = (fp, 'low' if row['actors'] <= 3 else roster)
        groups[manifest[key]].append((row, s))
    try:
        for graph_index, (path, cases) in enumerate(sorted(groups.items())):
            guard()
            if graph_index >= 30: raise TimeoutError('GRAPH_CAP_UNKNOWN')
            raw = path.read_bytes()
            # Trusted own-role cache from recorded closed producer, never an
            # arbitrary external pickle; public positive paths need no pickle.
            g = pickle.loads(gzip.decompress(raw))
            c = compiled[cases[0][0]['fingerprint']]
            assert g['ruleset'] == c.ruleset_fingerprint
            positions, indices, edges, terminals = (g[k] for k in ('positions', 'indices', 'edges', 'terminals'))
            assert len(positions) == len(indices) == len(edges) and all(e is not None for e in edges)
            decisive = {i for i, winner in terminals.items() if winner is not None}
            # New complete Core graph check is motivated by the stronger
            # negative reachability claim; not a rerun of any experiment cap.
            check_start = time.perf_counter(); checked_edges = 0
            for i, pos in enumerate(positions) if audit_full_graph else ():
                guard()
                state = fresh_state(pos, c)
                if state.terminal_status.is_terminal:
                    assert i in terminals and terminals[i] == state.terminal_status.winner and not edges[i]
                else:
                    assert i not in terminals
                    actual = [indices[ch.position] for _, ch in legal_successors(state, c)]
                    assert tuple(actual) == tuple(edges[i])
                    checked_edges += len(actual)
            result['graph_checks'].append(dict(path=str(path).replace('\\', '/'), sha256=hashlib.sha256(raw).hexdigest(),
                                               fingerprint=c.ruleset_fingerprint, positions=len(positions), edges=checked_edges,
                                               seconds=time.perf_counter()-check_start, complete=audit_full_graph,cache_complete=True))
            key_index = {repetition_identity_key(pos, c): i for i, pos in enumerate(positions)}
            for row, session in cases:
                guard()
                state = session.state
                blocked = {key_index[key] for key, count in state.repetition_counts if count == 3 and key in key_index}
                ds, nxt = cooperative_distances(edges, decisive, blocked)
                root = indices[state.position]
                distance = ds.get(root)
                can_mate = distance is not None and distance <= row['rule_remaining']
                witness = []
                if can_mate:
                    current = root
                    while current not in decisive:
                        guard()
                        child_index = nxt[current]
                        candidates = [(ac, ch) for ac, ch in legal_successors(session.state, c) if ch.position == positions[child_index]]
                        assert candidates
                        ac, child = candidates[0]
                        witness.append(action_to_dict(ac)); session.submit(ac)
                        assert session.state == child
                        current = child_index
                    assert session.result.winner is not None and len(witness) == distance
                result['rows'].append(dict(id=row['id'], fingerprint=row['fingerprint'], graph=str(path).replace('\\', '/'),
                                           remaining=row['rule_remaining'], blocked_vertices=len(blocked), shortest_cooperative_distance=distance,
                                           cooperative_decisive=can_mate, universal_draw=not can_mate,
                                           root_wdl_bounds=row['wdl_bounds'], graph_structural_deadzone=row['graph_structural_deadzone'],
                                           witness=witness, terminal=None if not can_mate else dict(status=session.result.status.value, winner=session.result.winner)))
    except TimeoutError as exc:
        result['status'] = str(exc)
    result['unresolved'] = sorted(set(chosen)-{r['id'] for r in result['rows']})
    result['seconds'] = time.perf_counter()-started
    return result


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--truth', required=True); parser.add_argument('--output', required=True); parser.add_argument('--seconds', type=int, default=900)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 900: raise ValueError('bounded 1..900 seconds required')
    result = run(load(args.truth), seconds=args.seconds)
    save(args.output, result)
    print(json.dumps(dict(status=result['status'], selected=len(result['selected']), completed=len(result['rows']), unresolved=len(result['unresolved']), seconds=result['seconds'])))


if __name__ == '__main__': main()
