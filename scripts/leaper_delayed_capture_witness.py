"""Named delayed-capture and short-clock witnesses; no graph or Player search.

Every node is a strict GameSession replay of a full fresh RuleSet/GameRecord.
Named continuations come from an exposed Chat suggestion, not a blind sample.
"""
from __future__ import annotations
import argparse
from dataclasses import replace
from pathlib import Path
from datetime import datetime, timezone
import gzip, json, time
from collections import Counter
from scripts import leaper_design as L
from scripts.leaper_rule_coordinates import physical_action
from scripts.leaper_parity_scope import orthogonally_independent
from generic_chess.core.semantic_executor import semantic_engine_for
from tools.local_agent.common import write_json


def now():
    return datetime.now(timezone.utc).isoformat()


def named_rule(source, *, white_turn=False, H=6, scoring='draw'):
    """Represent black-first by owner exchange, never a synthetic GameState.

    Core initial turn is seat0. Geometric white keeps type A; black keeps B.
    Complete rule policies come from the source, with the declared root/clock.
    """
    white = 0 if white_turn else 1
    black = 1 - white
    board = [None] * 9
    black_king = 5 if white_turn else 7
    for square, owner, tid in ((0, white, 'K'), (2, white, 'A'),
                               (black_king, black, 'K'), (6, black, 'B')):
        board[square] = L.Piece(owner, tid, tid)
    return replace(source, initial_position=tuple(tuple(board[3*y:3*y+3])
                   for y in range(3)), initial_setup_options=(), max_ply=H,
                   stalemate_result=scoring)


def theorem_scope(rule, mask):
    """Fail closed on policies that invalidate the remnant draw argument."""
    pieces=[p for row in rule.initial_position for p in row if p is not None]
    attacking=[p for p in pieces if p.current_type_id=='A']
    if len(attacking)!=1:return False
    white=attacking[0].owner
    expected_inventory=Counter({(0,'K','K'):1,(1,'K','K'):1,(white,'A','A'):1,(1-white,'B','B'):1})
    if Counter((p.owner,p.current_type_id,p.base_type_id)for p in pieces)!=expected_inventory:return False
    expected = L.RuleSet(
        board_size=3,
        piece_types=tuple(L.PieceType(t, t, tuple(L.LeapAtom(v) for v in L.offsets(m)),
                                      is_anchor=(t == 'K'))
                          for t, m in (('K', 3), ('A', mask), ('B', 27))),
        initial_position=rule.initial_position,
        drop_allowed={t: ((False,) * 9,) * 2 for t in ('A', 'B')},
        capture_disposition='remove_from_game', max_ply=rule.max_ply,
        repetition_limit=2, stalemate_result=rule.stalemate_result)
    return (mask in (6, 22) and rule.max_ply in (1, 2, 6)
            and rule.stalemate_result in ('draw', 'loss')
            and L.ruleset_to_dict(rule) == L.ruleset_to_dict(expected))


def action_map(session):
    return {physical_action(L.record_value(a), 3): a
            for a in session.legal_actions()}


def replay(compiled, record):
    return L.GameSession.replay(compiled,
             L.deserialize_game_record(json.dumps(record)))


def snapshot(session):
    engine = semantic_engine_for(session.compiled)
    return dict(record=L.record_value(session.to_record()),
                state=L.record_value(session.state),
                state_sha256=L.state_sha(session.state),
                result=L.record_value(session.result),
                legal_actions=[L.record_value(a) for a in session.legal_actions()],
                check=[engine.in_check(session.state.position, p) for p in (0, 1)])


def follow(compiled, record, key):
    session = replay(compiled, record)
    actions = action_map(session)
    if tuple(key) not in actions:
        raise ValueError(f'named action {key} not legal: {list(actions)}')
    session.submit(actions[tuple(key)])
    return session


def child_frontier(compiled, root, key):
    child = follow(compiled, root, key)
    replies = []
    for k in action_map(child):
        reply = follow(compiled, L.record_value(child.to_record()), k)
        replies.append(dict(action_key=list(k), node=snapshot(reply)))
    return dict(action_key=list(key), child=snapshot(child), replies=replies)


def measure(source):
    tick = time.perf_counter()
    start = now()
    families = {f['masks'][0]: L.ruleset_from_dict(f['rule'])
                for f in source['families']}
    measured = dict(started_at=start, source_provider=source['provider_commit'],
                    source_common_mu_id=source['common_mu_id'],
                    sample_scope='One exposed role-changed candidate; NOT any of the 128 original white-first roots.',
                    candidate=[], clocks=[], scoring=[],
                    new_Player_queries=0, new_graph_or_solver_calls=0,
                    source_capsule_executions=0)
    king = ('K', 7, 5, None)
    for mask in (6, 22):
        rule = named_rule(families[mask])
        c = L.compile_rule(rule)
        s = L.GameSession(c)
        r = L.record_value(s.to_record())
        branch = child_frontier(c, r, king)
        # Named two white moves; keep ALL black replies, not only the mate.
        after_king = branch['child']['record']
        white_branches = [child_frontier(c, after_king, k)
                          for k in action_map(replay(c, after_king))]
        measured['candidate'].append(dict(mask=mask, white_owner=1,
             rule=L.ruleset_to_dict(rule, include_metadata=True), root=snapshot(s),
             shared_king=branch, white_branches=white_branches,
             A_offset_orthogonally_independent=orthogonally_independent(L.offsets(mask))))
        for H in (1, 2):
            rule = named_rule(families[mask], white_turn=True, H=H)
            c = L.compile_rule(rule)
            s = L.GameSession(c)
            r = L.record_value(s.to_record())
            measured['clocks'].append(dict(mask=mask, H=H, white_owner=0,
                 rule=L.ruleset_to_dict(rule, include_metadata=True), root=snapshot(s),
                 white_branches=[child_frontier(c, r, k) for k in action_map(s)]))
    # Same named role-root and same king/capture path; ONLY scoring changes.
    for scoring in ('draw', 'loss'):
        rule = named_rule(families[22], scoring=scoring)
        c = L.compile_rule(rule)
        s = L.GameSession(c)
        after = follow(c, L.record_value(s.to_record()), king)
        capture = child_frontier(c, L.record_value(after.to_record()), ('A', 2, 6, None))
        # ONE additional white frontier per legal black reply, no recursive solver.
        white_next = []
        for reply in capture['replies']:
            rec = reply['node']['record']
            z = replay(c, rec)
            white_next.append(dict(black_reply=reply['action_key'],
                 white_branches=[child_frontier(c, rec, k) for k in action_map(z)]))
        measured['scoring'].append(dict(scoring=scoring,
             rule=L.ruleset_to_dict(rule, include_metadata=True), root=snapshot(s),
             capture=capture, white_next=white_next,
             root_WDL='UNKNOWN; no-mate does not imply draw under loss-stalemate'))
    measured['ended_at'] = now()
    measured['seconds'] = time.perf_counter() - tick
    return measured


def qualify(m):
    """Evaluate declared literal premises only AFTER raw returns are persisted."""
    candidate = {r['mask']: r for r in m['candidate']}
    old, new = candidate[6], candidate[22]
    for row in m['candidate'] + m['clocks']:
        assert theorem_scope(L.ruleset_from_dict(row['rule']), row['mask']), 'outside proved rule scope'
    for row in m['scoring']:
        assert theorem_scope(L.ruleset_from_dict(row['rule']), 22), 'outside scoring scope'
    assert old['root']['result']['status'] == new['root']['result']['status'] == 'ongoing'
    a, b = [r['shared_king']['child'] for r in (old, new)]
    assert a['result']['status'] == b['result']['status'] == 'ongoing'
    assert a['state']['position']['board'] == b['state']['position']['board']
    assert a['state']['position']['side_to_move'] == b['state']['position']['side_to_move'] == 1
    assert a['state']['ply_count'] == b['state']['ply_count'] == 1
    assert old['rule']['max_ply'] - a['state']['ply_count'] == 5
    old_actions = {tuple(x['action_key']) for x in old['white_branches']}
    new_actions = {tuple(x['action_key']) for x in new['white_branches']}
    expected_old = {('A', 2, 4, None), ('A', 2, 8, None)}
    capture_key = ('A', 2, 6, None)
    assert old_actions == expected_old
    assert new_actions == expected_old | {capture_key}
    mate_keys = {('A', 2, 4, None): ('B', 6, 4, None),
                 ('A', 2, 8, None): ('B', 6, 1, None)}
    mates = []
    for row in (old, new):
        for w in row['white_branches']:
            k = tuple(w['action_key'])
            if k in mate_keys:
                response = next(r for r in w['replies'] if tuple(r['action_key']) == mate_keys[k])
                assert response['node']['result']['status'] == 'checkmate'
                assert response['node']['result']['winner'] == 0
                mates.append(dict(mask=row['mask'], white_action=list(k),
                                  black_mate=list(mate_keys[k]), ply=3))
    capture = next(x for x in new['white_branches'] if tuple(x['action_key']) == capture_key)
    assert capture['child']['result']['status'] == 'ongoing'
    assert not any(p and p['current_type_id'] == 'B'
                   for p in capture['child']['state']['position']['board'])
    assert all(not dict(h['counts']) for h in capture['child']['state']['position']['hands'])
    assert new['A_offset_orthogonally_independent']
    # Scoped geometric no-mate theorem + bare king + finite clock under draw.
    # No move graph is regenerated, and no AUX labels are invented.
    clocks = []
    for row in m['clocks']:
        mask, H = row['mask'], row['H']
        if H == 1:
            assert all(w['child']['result']['status'] == 'max_ply'
                       and w['child']['result']['winner'] is None
                       for w in row['white_branches'])
            value = 0
        else:
            for w in row['white_branches']:
                k = tuple(w['action_key'])
                if k in mate_keys:
                    response = next(r for r in w['replies'] if tuple(r['action_key']) == mate_keys[k])
                    assert response['node']['result']['status'] == 'checkmate'
                    assert response['node']['result']['winner'] == 1
                    assert response['node']['state']['ply_count'] == 2
                else:
                    assert mask == 22 and k == capture_key
                    assert w['replies']
                    assert all(r['node']['result']['status'] == 'max_ply'
                               and r['node']['result']['winner'] is None for r in w['replies'])
            value = -1 if mask == 6 else 0
        clocks.append(dict(mask=mask, H=H, white_WDL=value,
                            evidence='All white options, named mate responses; all capture-branch H2 replies.'))
    scoring = qualify_scoring(m['scoring'])
    return dict(status='PASS', scoring=scoring, candidate_shared_action_WDL_white=[-1, 0],
                 candidate_shared_action_WDL_black=[1, 0],
                 both_shared_children_ongoing=True, old_white_options=len(old_actions),
                 added_capture_exits=1, mate_response_witnesses=mates,
                 clocks=clocks,
                 remnant_draw_basis='Complete remove-only, no promotion/drop/pass, draw-stalemate, finiteH/repeat2; A22 offset independence forbids checkmate and bare king cannot mate.',
                 proof_scope='Exposed named action, not new black-root WDL or 128-root population prediction. Remaining scoring values UNKNOWN.',
                 new_Player_queries=0, new_graph_or_solver_calls=0)



def nodes(value):
    if isinstance(value, dict):
        if {'record', 'state', 'state_sha256', 'result', 'legal_actions', 'check'} <= value.keys():
            yield value
        else:
            for x in value.values():
                yield from nodes(x)
    elif isinstance(value, list):
        for x in value:
            yield from nodes(x)


def physical(node):
    # Cross-rule fingerprints and derived repetition keys necessarily differ.
    # Compare actual board/side/hands/aux plus legal physical actions, NOT hash.
    p = node['state']['position']
    return dict(board=p['board'], hands=p['hands'], turn=p['side_to_move'],
                aux=p.get('aux_state'), ply=node['state']['ply_count'],
                actions=sorted((physical_action(a, 3) for a in node['legal_actions']), key=str),
                check=node['check'])


def qualify_scoring(rows):
    a, b = rows
    assert [r['scoring'] for r in rows] == ['draw', 'loss']
    ra, rb = [L.ruleset_from_dict(r['rule']) for r in rows]
    assert L.ruleset_to_dict(replace(ra, stalemate_result='loss'), include_metadata=True) == L.ruleset_to_dict(rb, include_metadata=True)
    aa, bb = list(nodes(a)), list(nodes(b))
    assert len(aa) == len(bb)
    changes = []
    statuses = []
    for left, right in zip(aa, bb):
        assert physical(left) == physical(right)
        if left['result'] != right['result']:
            changes.append(dict(draw=left['result'], loss=right['result']))
        statuses.append(left['result']['status'])
    # This is the actual negative local result, not a positive-effect prediction.
    return dict(node_occurrences_compared=len(aa), payoff_changes=changes,
                terminal_status_counts={k: statuses.count(k) for k in sorted(set(statuses))},
                root_WDL='UNKNOWN; limited literal continuations do not solve loss-stalemate',
                limit='No additional branches were selected to hunt a scoring effect.')


def verify_measurements(m):
    """Replay stored records only, no source capsules and no new fitness."""
    count = 0
    seen = {}
    for row in m['candidate'] + m['clocks'] + m['scoring']:
        rule = L.ruleset_from_dict(row['rule'])
        c = L.compile_rule(rule)
        for node in nodes(row):
            count += 1
            key = json.dumps(node['record'], sort_keys=True)
            if key in seen:
                assert node == seen[key], 'literal stored duplicate record has inconsistent state/frontier'
                continue
            seen[key] = node
            session = replay(c, node['record'])
            actual = snapshot(session)
            assert actual == node, 'literal stored state/frontier/record mismatch'
    return dict(status='PASS', node_occurrences=count, unique_full_records=len(seen),
                independently_recomputed='Strict same-Core record and frontier binding; NOT an independent WDL solver',
                qualification=qualify(m), new_Player_queries=0, new_graph_or_solver_calls=0)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', type=Path)
    p.add_argument('--verify-measurements', type=Path)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise ValueError('NEW output directory required')
    a.output.mkdir(parents=True)
    if a.verify_measurements:
        m = json.loads(a.verify_measurements.read_text(encoding='utf-8'))
        q = verify_measurements(m)
        write_json(a.output / 'qualification.json', q)
        print(json.dumps({k: v for k, v in q.items() if k != 'qualification'}))
        return
    if not a.input:
        p.error('--input or --verify-measurements required')
    src = json.loads(gzip.decompress(a.input.read_bytes()))
    m = measure(src)
    write_json(a.output / 'measurements.json', m)
    # Raw results survive a failed expectation. No fit-to-output changes.
    q = qualify(m)
    write_json(a.output / 'qualification.json', q)
    print(json.dumps(q))


if __name__ == '__main__':
    main()
