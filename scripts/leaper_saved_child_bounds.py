"""Bellman bounds using exact saved full-history children, never a Position join.

Enumerate one successor layer of existing unresolved roots once. Ongoing child
identities not already in the frozen inventory stay UNKNOWN; they are never
expanded. Descending actual ply gives an acyclic proof order. Inputs, failed
attempts and prior caps remain immutable. This is AUX truth, not E0 prediction.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import time

from generic_chess.core.actions import action_from_dict, action_to_dict
from generic_chess.core.transition import legal_successors, apply_action
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.leaper_design import state_sha
from scripts.leaper_explorer_truth import digest, load, save, materialize
from scripts.leaper_explorer_supplement import apply_supplement
from scripts.leaper_local_truth import apply_layer
from scripts.leaper_microgames import role_stop_requested

PROPS = ('wdl_fork', 'cooperative_decisive', 'universal_draw')


def current_truth(parent, followup):
    p, f = Path(parent), Path(followup)
    t = materialize(load(p/'truth.json.gz'), load(p/'cooperative.json'),
                    load(p/'observed-suffixes.json.gz'))
    return apply_layer(apply_supplement(t, load(f/'supplement.json.gz')),
                       load(f/'local-layer.json.gz'))


def interval(bounds):
    if (not isinstance(bounds, list) or len(bounds) != 2
            or any(type(v) is not int or v not in (-1, 0, 1) for v in bounds)
            or bounds[0] > bounds[1]):
        raise ValueError('integer WDL interval required')
    return bounds


def meet(first, second):
    a, b = interval(first), interval(second)
    result = [max(a[0], b[0]), min(a[1], b[1])]
    if result[0] > result[1]:
        raise ValueError('contradictory WDL bounds')
    return result


def restrict(old, new):
    if old is not None and type(old) is not bool:
        raise ValueError('boolean/UNKNOWN required')
    if new is not None and type(new) is not bool:
        raise ValueError('boolean/UNKNOWN required')
    if old is not None and new is not None and old != new:
        raise ValueError('contradictory property')
    return old if new is None else new


def summarize_children(children):
    if not children:
        raise ValueError('ongoing root must have legal children')
    bounds = [interval(c['wdl_bounds']) for c in children]
    fork = (False if len(children) == 1 or
            all(b == bounds[0] and b[0] == b[1] for b in bounds) else
            True if max(b[0] for b in bounds) > min(b[1] for b in bounds) else None)
    coops = [c['cooperative_decisive'] for c in children]
    coop = True if any(x is True for x in coops) else False if all(x is False for x in coops) else None
    return dict(wdl_bounds=[max(b[0] for b in bounds), max(b[1] for b in bounds)],
                wdl_fork=fork, cooperative_decisive=coop,
                universal_draw=None if coop is None else not coop)


def edge(state, action, child):
    t = child.terminal_status
    return dict(action=action_to_dict(action), child_id=state_sha(child),
                child_ply=child.ply_count, parent_mover=state.position.side_to_move,
                child_mover=child.position.side_to_move,
                terminal=t.status.value, terminal_winner=t.winner)


def propagate(truth, packet):
    """Pure inference after Core edge verification; all changes source-bound."""
    if packet.get('format') != 'leaper-saved-child-bounds-v1' or packet['input_digest'] != digest(truth):
        raise ValueError('saved-child source mismatch')
    out = deepcopy(truth)
    roots = {r['id']: r for r in out['roots']}
    if len(roots) != len(out['roots']):
        raise ValueError('duplicate source history')
    rows = packet['rows']
    ids = [q['id'] for q in rows]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate successor root')
    changes = []
    for q in sorted(rows, key=lambda q: (-roots[q['id']]['ply'], q['id'])):
        r = roots[q['id']]
        if q['fingerprint'] != r['fingerprint'] or q['ply'] != r['ply']:
            raise ValueError('root rule/ply mismatch')
        actions = [digest(e['action']) for e in q['children']]
        if len(actions) != len(set(actions)):
            raise ValueError('duplicate legal action')
        old_actions = {digest(a['action']): interval(a['wdl_bounds']) for a in r['action_bounds']}
        if set(old_actions) - set(actions):
            raise ValueError('omitted old action')
        children = []
        for e in q['children']:
            if e['child_ply'] != r['ply'] + 1 or e['parent_mover'] not in (0, 1) or e['child_mover'] not in (0, 1):
                raise ValueError('nonranked edge or invalid mover')
            child = roots.get(e['child_id'])
            if e['terminal'] == 'ongoing':
                if e['terminal_winner'] is not None:
                    raise ValueError('ongoing winner')
                bs = [-1, 1]
                coop = None
                if child is not None:
                    if child['fingerprint'] != r['fingerprint'] or child['ply'] != e['child_ply']:
                        raise ValueError('child rule/history mismatch')
                    bs = interval(child['wdl_bounds'])
                    if e['parent_mover'] != e['child_mover']:
                        bs = [-bs[1], -bs[0]]
                    coop = child['cooperative_decisive']
            elif e['terminal'] == 'no_contest':
                bs, coop = [-1, 1], None
            else:
                winner = e['terminal_winner']
                if winner is not None and type(winner) is not int:
                    raise ValueError('invalid winner')
                if winner not in (None, 0, 1):
                    raise ValueError('invalid winner')
                value = 0 if winner is None else 1 if winner == e['parent_mover'] else -1
                bs, coop = [value, value], winner is not None
            bs = meet(bs, old_actions.get(digest(e['action']), [-1, 1]))
            children.append(dict(action=e['action'], wdl_bounds=bs, cooperative_decisive=coop))
        derived = summarize_children(children)
        before = {k: deepcopy(r[k]) for k in ('wdl_bounds', 'action_bounds', *PROPS)}
        r['wdl_bounds'] = meet(r['wdl_bounds'], derived['wdl_bounds'])
        r['action_bounds'] = [{k: c[k] for k in ('action', 'wdl_bounds')} for c in children]
        for prop in PROPS:
            r[prop] = restrict(r[prop], derived[prop])
        if r['wdl_bounds'] in ([-1, -1], [1, 1]):
            r['cooperative_decisive'] = restrict(r['cooperative_decisive'], True)
            r['universal_draw'] = restrict(r['universal_draw'], False)
        after = {k: r[k] for k in before}
        if before != after:
            changes.append(dict(id=r['id'], fingerprint=r['fingerprint'], ply=r['ply'],
                                before=before, after=deepcopy(after)))
            r['saved_child_basis'] = 'ranked_exact_full_history_child_join'
    out['saved_child_packet_digest'] = digest(packet)
    return out, changes


def collect(truth, *, seconds=180):
    """One pass; the cap includes rule compilation and source replay."""
    start = time.perf_counter()
    target = {r['id'] for r in truth['roots']
              if r['wdl_bounds'][0] != r['wdl_bounds'][1] or r['wdl_fork'] is None}
    roots = {r['id']: r for r in truth['roots']}
    compiled = {fp: compile_rule(ruleset_from_dict(rule)) for fp, rule in truth['rules'].items()}
    rows, seen, stats = [], set(), Counter()
    status = 'COMPLETE'
    try:
        for rid, record in truth['records'].items():
            c = compiled[record['ruleset_fingerprint']]
            s = GameSession.replay(c, deserialize_game_record(json.dumps(record | dict(actions=[]))))
            for action in record['actions']:
                if role_stop_requested():
                    raise TimeoutError('USER_STOP')
                if time.perf_counter() - start >= seconds:
                    raise TimeoutError('TIME_CAP_UNKNOWN')
                hid = state_sha(s.state)
                if hid in target and hid not in seen:
                    children = []
                    for ac, ch in legal_successors(s.state, c):
                        if time.perf_counter() - start >= seconds:
                            raise TimeoutError('TIME_CAP_UNKNOWN')
                        children.append(edge(s.state, ac, ch))
                    r = roots[hid]
                    rows.append(dict(id=hid, fingerprint=r['fingerprint'], ply=r['ply'], children=children))
                    seen.add(hid)
                    stats['complete_roots'] += 1
                    stats['core_edges'] += len(children)
                    stats['saved_child_edges'] += sum(e['child_id'] in roots for e in children)
                s.submit(action_from_dict(action))
                stats['replayed_actions'] += 1
            stats['complete_records'] += 1
    except TimeoutError as exc:
        status = str(exc)
    return dict(format='leaper-saved-child-bounds-v1', input_digest=digest(truth),
                rows=rows, status=status, counts=dict(stats), unqueried=sorted(target-seen),
                seconds=time.perf_counter()-start, caps=dict(seconds=seconds, depth=1),
                scope='Complete legal successor rows only; exact saved full-history identities, descending ply. Missing ongoing children UNKNOWN. No new child expansion, graph, rule, game, forecast or training.')


def verify(truth, packet, *, seconds=180):
    """Independently enumerate/apply every claimed row, then redo inference."""
    from scripts.leaper_cooperative_certificate import root_session
    start = time.perf_counter()
    if digest(truth) != packet['input_digest']:
        raise ValueError('verification source mismatch')
    roots = {r['id']: r for r in truth['roots']}
    compiled, stats = {}, Counter()
    for q in packet['rows']:
        if role_stop_requested():
            raise RuntimeError('USER_STOP')
        if time.perf_counter()-start >= seconds:
            raise RuntimeError('VERIFICATION_CAP_UNKNOWN')
        r = roots[q['id']]
        fp = r['fingerprint']
        if fp not in compiled:
            compiled[fp] = compile_rule(ruleset_from_dict(truth['rules'][fp]))
        _, s = root_session(truth, q['id'], compiled[fp])
        actual = [edge(s.state, ac, apply_action(s.state, ac, compiled[fp])) for ac in s.legal_actions()]
        if digest(actual) != digest(q['children']):
            raise ValueError('Core successor identity/coverage mismatch')
        stats['roots'] += 1
        stats['core_edges'] += len(actual)
    updated, changes = propagate(truth, packet)
    return dict(verified=True, counts=dict(stats), changed_roots=len(changes),
                output_digest=digest(updated), packet_digest=digest(packet),
                seconds=time.perf_counter()-start,
                scope='All packet edges rechecked through public legal_actions/apply_action and full source-record replay, then ranked inference independently repeated. Input imported truth retains its earlier qualifications.')


def summary(truth, updated, changes, packet):
    fields = ('wdl_bounds', *PROPS)
    return dict(format='leaper-saved-child-summary-v1', input_digest=digest(truth),
                output_digest=digest(updated), packet_digest=digest(packet),
                counts=packet['counts'], status=packet['status'],
                changed_roots=len(changes),
                changed_fields={k: sum(q['before'][k] != q['after'][k] for q in changes) for k in fields},
                exact_wdl=sum(r['wdl_bounds'][0] == r['wdl_bounds'][1] for r in updated['roots']),
                wdl_intervals=dict(Counter(str(r['wdl_bounds']) for r in updated['roots'])),
                properties={p: dict(Counter(str(r[p]) for r in updated['roots'])) for p in PROPS},
                initial=[{k:r[k] for k in ('id', *fields)} for r in updated['roots'] if r['ply'] == 0],
                producer_seconds=packet['seconds'])


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument('command', choices=('collect', 'verify'))
    cli.add_argument('--parent', default='docs/research/data/leaper_explorer_truth_20261023')
    cli.add_argument('--followup', default='docs/research/data/leaper_explorer_followup_20261023')
    cli.add_argument('--output', required=True)
    cli.add_argument('--packet')
    args = cli.parse_args()
    started = time.perf_counter()
    truth = current_truth(args.parent, args.followup)
    loaded = time.perf_counter()
    if args.command == 'collect':
        p = Path(args.output)
        p.mkdir(parents=True, exist_ok=False)
        packet = collect(truth)
        updated, changes = propagate(truth, packet)
        save(p/'edges.json.gz', packet)
        save(p/'changes.json.gz', changes)
        report = summary(truth, updated, changes, packet)
        report['load_seconds'] = loaded-started
        report['end_to_end_seconds'] = time.perf_counter()-started
        save(p/'summary.json', report)
    else:
        report = verify(truth, load(args.packet))
        report['load_seconds'] = loaded-started
        report['end_to_end_seconds'] = time.perf_counter()-started
        save(args.output, report)
    print(json.dumps(report))


if __name__ == '__main__':
    main()
