"""One legal-history contrast, same full rule/Position/clock, no graph solver."""
from __future__ import annotations
import argparse, gzip, json, time
from dataclasses import replace
from pathlib import Path
from generic_chess.rules.schema import RuleInitialSetupOption
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import (
    named_rule, follow, snapshot, action_map, child_frontier, nodes, replay, now)
from tools.local_agent.common import write_json


def measure(source):
    tick = time.perf_counter()
    base = L.ruleset_from_dict(next(f['rule'] for f in source['families'] if f['masks'][0] == 6))
    default = named_rule(base, white_turn=True, H=6)
    cells = [list(row) for row in default.initial_position]
    cells[0][2] = None
    cells[1][1] = L.Piece(0, 'A', 'A')
    alternate = tuple(tuple(row) for row in cells)
    rule = replace(default, initial_setup_options=(RuleInitialSetupOption('first_visit_path', alternate),))
    c = L.compile_rule(rule)
    paths = [
        (None, [('A', 2, 8, None), ('K', 5, 7, None), ('A', 8, 2, None), ('K', 7, 5, None)]),
        ('first_visit_path', [('A', 4, 8, None), ('K', 5, 7, None), ('A', 8, 2, None), ('K', 7, 5, None)])]
    result = dict(started_at=now(), rule=L.ruleset_to_dict(rule, include_metadata=True),
                  paths=[], new_Player_queries=0, new_graph_or_solver_calls=0)
    for setup, keys in paths:
        s = L.GameSession(c, setup)
        trace = [snapshot(s)]
        for k in keys:
            s = follow(c, L.record_value(s.to_record()), k)
            trace.append(snapshot(s))
        r = L.record_value(s.to_record())
        branches = [child_frontier(c, r, k) for k in action_map(s)]
        result['paths'].append(dict(setup_key=setup, actions=[list(k) for k in keys],
                                   trace=trace, target=snapshot(s), white_branches=branches))
    result['ended_at'] = now()
    result['seconds'] = time.perf_counter() - tick
    return result


def qualify_loss_prediction(m):
    repeated, fresh = m['paths']
    a, b = [p['target'] for p in m['paths']]
    assert a['state']['position'] == b['state']['position']
    assert a['state']['ply_count'] == b['state']['ply_count'] == 4
    assert m['rule']['max_ply'] == 6 and m['rule']['repetition_limit'] == 2
    assert a['result']['status'] == 'repetition' and a['result']['winner'] is None
    assert b['result']['status'] == 'ongoing'
    assert len(a['record']['actions']) == len(b['record']['actions']) == 4
    assert a['record'].get('initial_setup_key') != b['record'].get('initial_setup_key')
    for path in m['paths']:
        assert all(n['result']['status'] == 'ongoing' for n in path['trace'][:-1])
    assert repeated['trace'][0]['state']['position'] == a['state']['position']
    assert fresh['trace'][0]['state']['position'] != b['state']['position']
    assert len(fresh['white_branches']) == 2
    assert not repeated['white_branches']
    responses = {('A', 2, 4, None): ('B', 6, 4, None),
                 ('A', 2, 8, None): ('B', 6, 1, None)}
    assert {tuple(x['action_key']) for x in fresh['white_branches']} == responses.keys()
    witnesses = []
    for w in fresh['white_branches']:
        mate = next(r for r in w['replies']
                    if tuple(r['action_key']) == responses[tuple(w['action_key'])])
        assert mate['node']['result']['status'] == 'checkmate'
        assert mate['node']['result']['winner'] == 1
        assert mate['node']['state']['ply_count'] == 6
        witnesses.append(dict(white_action=w['action_key'], black_mate=mate['action_key']))
    return dict(status='PASS', same_full_rule_Position_and_clock=True,
                target_ply=4, remaining=2, white_WDL=[0, -1],
                terminal_status=['repetition', 'ongoing'], mate_witnesses=witnesses,
                decision='Position plus remaining clock is insufficient; legal occurrence history changes value.',
                limits='One named-setup pair, exact local proof. No arbitrary forged history or population claim.')



def assess(m):
    # Preserve the original loss prediction above; it FAILS on these actual rows.
    repeated, fresh = m['paths']
    a, b = [x['target'] for x in m['paths']]
    assert a['state']['position'] == b['state']['position']
    assert a['state']['ply_count'] == b['state']['ply_count'] == 4
    assert a['result']['status'] == 'repetition' and a['result']['winner'] is None
    assert b['result']['status'] == 'ongoing'
    assert all(n['result']['status'] == 'ongoing'
               for path in m['paths'] for n in path['trace'][:-1])
    assert {tuple(x['action_key']) for x in fresh['white_branches']} == {
        ('A', 2, 4, None), ('A', 2, 8, None)}
    proof = []
    for w in fresh['white_branches']:
        if tuple(w['action_key']) == ('A', 2, 8, None):
            assert w['child']['result']['status'] == 'repetition'
            assert w['child']['result']['winner'] is None
            assert w['child']['state']['ply_count'] == 5
            assert w['child']['state']['position'] == fresh['trace'][1]['state']['position']
            assert not w['replies']
            value = 0
        else:
            mate = next(r for r in w['replies'] if tuple(r['action_key']) == ('B', 6, 4, None))
            assert mate['node']['result']['status'] == 'checkmate'
            assert mate['node']['result']['winner'] == 1
            assert mate['node']['state']['ply_count'] == 6
            value = -1
        proof.append(dict(action=w['action_key'], white_action_WDL=value))
    return dict(binding_status='PASS', prediction_status='REFUTED',
                predicted_white_WDL=[0, -1], proven_white_WDL=[0, 0],
                same_full_rule_Position_and_clock=True, target_ply=4, remaining=2,
                different_target_terminal_status=['repetition', 'ongoing'],
                alternate_white_options=proof,
                cause='The alternate prefix already visited the c3 child atply1. White c1-c3 atply5 is a repetition DRAW before the alleged black mate. Fresh-root two-ply loss proof cannot be transplanted to this history.',
                supported_claim='Same Position/clock need not determine terminal status or legal continuations.',
                unsupported_claim='This candidate does NOT demonstrate different WDL for same Position/clock.',
                stop='First named history value candidate failed; no replacement history search or fabricated counts.')


def verify(m):
    c = L.compile_rule(L.ruleset_from_dict(m['rule']))
    seen = {}
    occurrences = 0
    for node in nodes(m):
        occurrences += 1
        key = json.dumps(node['record'], sort_keys=True)
        if key in seen:
            assert node == seen[key], 'literal stored duplicate record has inconsistent state/frontier'
            continue
        seen[key] = node
        assert snapshot(replay(c, node['record'])) == node
    return dict(status='PASS', node_occurrences=occurrences,
                unique_full_records=len(seen), qualification=assess(m),
                same_Core_binding_only=True, new_graph_or_solver_calls=0)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', type=Path)
    p.add_argument('--verify-measurements', type=Path)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise ValueError('NEW immutable output required')
    a.output.mkdir(parents=True)
    if a.verify_measurements:
        m = json.loads(a.verify_measurements.read_text(encoding='utf-8'))
        q = verify(m)
    else:
        if not a.input:
            p.error('--input or --verify-measurements required')
        m = measure(json.loads(gzip.decompress(a.input.read_bytes())))
        write_json(a.output / 'measurements.json', m)
        q = assess(m)
    write_json(a.output / 'qualification.json', q)
    print(json.dumps(q))


if __name__ == '__main__':
    main()
