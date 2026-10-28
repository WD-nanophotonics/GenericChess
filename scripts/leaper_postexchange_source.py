"""Frozen source-only Core witness search in existing actual game histories.

No Player, value search, policy implementation or new game. 'Postexchange'
means after at least one observed on-board material removal, not necessarily
a reciprocal exchange. Negative two-ply evidence never establishes WDL.
"""
import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from generic_chess.ai.alphabeta.quiescence import classify_noisy
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from scripts.leaper_check_extension_quality import record_interval
from scripts.leaper_pvs_quality_pilot import make_session, digest
from scripts.research_record import record_value, write_record
from scripts.verify_leaper_pvs_quality_pilot import action
from tools.local_agent.common import read_json


def stamp():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_bytes())


def stopped():
    return any(read_json(Path('.local_agent') / (n + '.json')).get(k, False)
               for n in ('rollout', 'advisor', 'slack')
               for k in ('stopped', 'research_stopped', 'stop_requested', 'user_paused'))


def replay(c, record):
    return GameSession.replay(c, deserialize_game_record(json.dumps(record)))


def setup(plan_path, out):
    plan = read_json(plan_path)
    for path, expected in plan['files'].items():
        assert sha(path) == expected, path
    assert sha(__file__) == plan['source_sha256']
    out.mkdir(exist_ok=False)
    write_record(out / 'frozen.json', plan)
    roots = {r['id']: r for r in read_json(Path(plan['prepared']))['rows']}
    return plan, roots


def select(plan_path, out):
    begin, tick = stamp(), time.perf_counter()
    plan, roots = setup(plan_path, out)
    games = load(plan['games'])
    descriptors = load(plan['old_descriptors'])
    known = {(x['game_id'], x['relative_ply']): x for x in descriptors if x['complete']}
    seen, selected, log = set(), [], []
    halt = None
    for g in games:
        if g['family'] in seen:
            continue
        c, s = make_session(roots[g['case_id']])
        engine = semantic_engine_for(c)
        initial_count = sum(p is not None for p in s.state.position.board)
        for qi, query in enumerate(g['queries']):
            if stopped() or time.perf_counter() - tick >= plan['selection_seconds']:
                halt = 'scoped_stop_or_selection_cap'
                break
            count = sum(p is not None for p in s.state.position.board)
            post = count < initial_count
            checked = engine.in_check(s.state.position, s.state.position.side_to_move)
            entry = dict(game_id=g['game_id'], case_id=g['case_id'], family=g['family'],
                         relative_ply=qi, board_count=count, initial_count=initial_count,
                         after_material_removal=post, in_check=checked, accept=False)
            if post and not checked and not s.state.terminal_status.is_terminal:
                record = record_value(s.to_record())
                old = known.get((g['game_id'], qi))
                if old is not None:
                    assert old['case_id'] == g['case_id'] and old['record'] == record
                    noisy, quiet = old['noisy'], old['quiet']
                    entry['descriptor_source'] = 'REUSED_EXACT_COMPLETE_OLD_DESCRIPTOR'
                else:
                    noisy, quiet = [], []
                    for a in s.legal_actions():
                        if time.perf_counter() - tick >= plan['selection_seconds']:
                            halt = 'selection_cap_in_descriptor'
                            break
                        child = GameSession.replay(c, s.to_record())
                        child.submit(a)
                        (noisy if classify_noisy(s.state, [(a, child.state)], c) else quiet).append(record_value(a))
                    entry['descriptor_source'] = 'NEW_COMPLETE_DESCRIPTOR' if not halt else 'UNKNOWN'
                entry.update(noisy_count=len(noisy), quiet_count=len(quiet))
                if not halt and noisy and quiet:
                    entry['accept'] = True
                    selected.append(dict(family=g['family'], case_id=g['case_id'],
                                         game_id=g['game_id'], relative_ply=qi,
                                         fingerprint=roots[g['case_id']]['fingerprint'],
                                         record=record, record_sha256=digest(record),
                                         noisy=noisy, quiet=quiet))
                    seen.add(g['family'])
            log.append(entry)
            if entry['accept'] or halt:
                break
            s.submit(action(query['decision']['action'], s))
        if halt:
            break
    # All selected histories are sealed BEFORE any new terminal-reply census.
    write_record(out / 'selection-log.json', log)
    write_record(out / 'selected-before-replies.json', selected)
    write_record(out / 'selection-summary.json', dict(selected=len(selected), families=sorted(seen),
                 missing_families=sorted(set(range(8))-seen), halt=halt,
                 reused_descriptors=sum(x.get('descriptor_source','').startswith('REUSED') for x in log),
                 new_descriptors=sum(x.get('descriptor_source','').startswith('NEW') for x in log),
                 Player=0, solver=0, games=0, reply_census='NOT_STARTED'))
    end = stamp()
    record_interval(begin, end, 'analysis', str(out / 'selection-summary.json'), out)
    print(json.dumps(read_json(out / 'selection-summary.json')))


def census(plan_path, selected_path, out):
    begin, tick = stamp(), time.perf_counter()
    plan, roots = setup(plan_path, out)
    selected = load(selected_path)
    old = load(plan['old_witnesses'])
    results = []
    for w in selected:
        prior = next((x for x in old if x['complete'] and x['case_id'] == w['case_id']
                      and x['record'] == w['record']), None)
        if prior is not None:
            results.append(dict(**w, status='REUSED_EXACT_COMPLETE_CENSUS', old=prior))
            write_record(out / 'witnesses.json', results)
            continue
        c, _ = make_session(roots[w['case_id']])
        s = replay(c, w['record'])
        assert digest(s.to_record()) == w['record_sha256']
        assert not s.state.terminal_status.is_terminal
        assert not semantic_engine_for(c).in_check(s.state.position, s.state.position.side_to_move)
        actor, row_tick, branches, calls, why = s.state.position.side_to_move, time.perf_counter(), [], 0, None
        legal = s.legal_actions()
        for a in legal:
            if stopped() or time.perf_counter()-tick >= plan['batch_seconds'] or time.perf_counter()-row_tick >= plan['row_seconds']:
                why = 'scoped_stop_or_time_cap'
                break
            child = GameSession.replay(c, s.to_record())
            child.submit(a)
            noisy = bool(classify_noisy(s.state, [(a, child.state)], c))
            term = child.state.terminal_status
            b = dict(action=record_value(a), noisy=noisy, child_record=record_value(child.to_record()),
                     terminal=record_value(term), status='UNKNOWN', enumerated=0, reply_count=None)
            if term.is_terminal:
                b['status'] = 'ROOT_TERMINAL_LOSS' if term.winner == 1-actor else 'ROOT_TERMINAL_NONLOSS'
            else:
                replies = child.legal_actions()
                b['reply_count'] = len(replies)
                for reply in replies:
                    if calls >= plan['max_replies_per_root'] or time.perf_counter()-tick >= plan['batch_seconds'] or time.perf_counter()-row_tick >= plan['row_seconds']:
                        why = 'reply_or_time_cap'
                        break
                    z = GameSession.replay(c, child.to_record())
                    z.submit(reply)
                    calls += 1
                    b['enumerated'] += 1
                    if z.state.terminal_status.is_terminal and z.state.terminal_status.winner == 1-actor:
                        b.update(status='HAS_TERMINAL_WIN_REPLY', winning_reply=record_value(reply),
                                 reply_record=record_value(z.to_record()), reply_terminal=record_value(z.state.terminal_status))
                        break
                if b['status'] == 'UNKNOWN' and b['enumerated'] == len(replies):
                    b['status'] = 'NO_TERMINAL_WIN_REPLY_ALL_ENUMERATED'
            branches.append(b)
            if why:
                break
        complete = why is None and len(branches) == len(legal) and all(b['status'] != 'UNKNOWN' for b in branches)
        survivors = [b for b in branches if b['status'] in ('NO_TERMINAL_WIN_REPLY_ALL_ENUMERATED', 'ROOT_TERMINAL_NONLOSS')]
        losing = [b for b in branches if b['status'] in ('HAS_TERMINAL_WIN_REPLY', 'ROOT_TERMINAL_LOSS')]
        candidate = complete and bool(survivors) and bool(losing) and any(b['noisy'] for b in branches) and all(not b['noisy'] for b in survivors)
        results.append(dict(**w, status='COMPLETE' if complete else 'UNKNOWN', stop=why,
                            legal_count=len(legal), branches=branches, reply_transitions=calls,
                            locally_losing=len(losing), local_survivors=len(survivors),
                            coverage_candidate=candidate, seconds=time.perf_counter()-row_tick))
        write_record(out / 'witnesses.json', results)
        if stopped() or time.perf_counter()-tick >= plan['batch_seconds']:
            break
    summary = dict(planned=len(selected), returned=len(results),
                   complete=sum(x['status']=='COMPLETE' for x in results),
                   reused=sum(x['status'].startswith('REUSED') for x in results),
                   candidates=sum(x.get('coverage_candidate', x.get('old',{}).get('coverage_omission_candidate',False)) for x in results),
                   UNKNOWN=sum(x['status']=='UNKNOWN' for x in results), NOT_RUN=len(selected)-len(results),
                   reply_transitions=sum(x.get('reply_transitions',0) for x in results),
                   claim='Two-ply actual-Core coverage only;not WDL,actual qvisit/error,causality or strength',
                   new_Player_calls=0, new_games=0, solver_or_controller=0)
    write_record(out / 'summary.json', summary)
    record_interval(begin, stamp(), 'analysis', str(out / 'summary.json'), out)
    print(json.dumps(summary))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('mode', choices=('select','census'))
    p.add_argument('--plan', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--selected', type=Path)
    a = p.parse_args()
    select(a.plan,a.output) if a.mode=='select' else census(a.plan,a.selected,a.output)
