"""Finite existential source witness search; no value solver or new game.

One completely enumerated non-losing noisy action is a sufficient negative
certificate. For a positive certificate every noisy action needs a concrete
terminal-loss reply and at least one genuinely quiet action needs ALL replies.
This asymmetry avoids paying for irrelevant quiet branches on negative roots.
"""
import argparse
import time
from pathlib import Path
from generic_chess.ai.alphabeta.quiescence import classify_noisy
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.session.session import GameSession
from scripts.leaper_check_extension_quality import record_interval
from scripts.leaper_postexchange_source import load, replay, sha, stamp, stopped
from scripts.leaper_pvs_quality_pilot import make_session, digest
from scripts.research_record import record_value, write_record
from scripts.verify_leaper_pvs_quality_pilot import action
from tools.local_agent.common import read_json


def run(plan_path, out):
    plan = read_json(plan_path)
    assert sha(__file__) == plan['source_sha256']
    for p, h in plan['files'].items():
        assert sha(p) == h
    out.mkdir(exist_ok=False)
    write_record(out/'frozen.json', plan)
    roots = {r['id']: r for r in load(plan['prepared'])['rows']}
    games = load(plan['games'])
    tick, begin = time.perf_counter(), stamp()
    returns, visited, calls, selected = [], [], 0, []
    # Seal the finite actual-history input/order before terminal-reply outcomes.
    for g in games:
        c, s = make_session(roots[g['case_id']])
        initial_count = sum(p is not None for p in s.state.position.board)
        rows = []
        for qi, q in enumerate(g['queries']):
            rows.append(dict(game_id=g['game_id'], family=g['family'], case_id=g['case_id'],
                             relative_ply=qi, record=record_value(s.to_record()),
                             after_material_removal=sum(p is not None for p in s.state.position.board)<initial_count))
            s.submit(action(q['decision']['action'], s))
        selected.extend(reversed(rows))
    write_record(out/'inputs-before-replies.json', selected)
    compiled = {}
    halt = None
    for idx, w in enumerate(selected):
        if stopped() or time.perf_counter()-tick >= plan['batch_seconds']:
            halt = 'scoped_stop_or_batch_cap'
            break
        if not w['after_material_removal']:
            visited.append(dict(index=idx,status='NOT_POST_REMOVAL'))
            continue
        if w['case_id'] not in compiled:
            compiled[w['case_id']] = make_session(roots[w['case_id']])[0]
        c = compiled[w['case_id']]
        s = replay(c,w['record'])
        checked = semantic_engine_for(c).in_check(s.state.position,s.state.position.side_to_move)
        if checked or s.state.terminal_status.is_terminal:
            visited.append(dict(index=idx,status='IN_CHECK_OR_TERMINAL'))
            continue
        row_tick = time.perf_counter()
        actor = s.state.position.side_to_move
        legal = s.legal_actions()
        groups = {True:[], False:[]}
        why = None
        for a in legal:
            if time.perf_counter()-tick >= plan['batch_seconds'] or time.perf_counter()-row_tick >= plan['row_seconds']:
                why='classification_cap'
                break
            child = GameSession.replay(c,s.to_record());child.submit(a)
            noisy = bool(classify_noisy(s.state,[(a,child.state)],c))
            groups[noisy].append((a,child))
        if why:
            returns.append(dict(index=idx,**w,status='UNKNOWN',why=why,branches=[]))
            break
        if not groups[True] or not groups[False]:
            visited.append(dict(index=idx,status='NOT_MIXED',noisy=len(groups[True]),quiet=len(groups[False])))
            continue
        branches, local_calls = [], 0
        status = 'UNKNOWN'
        for noisy in (True,False):
            for a,child in groups[noisy]:
                b=dict(action=record_value(a),noisy=noisy,terminal=record_value(child.state.terminal_status),
                       child_record=record_value(child.to_record()),enumerated=0,status='UNKNOWN')
                term=child.state.terminal_status
                if term.is_terminal:
                    b['status']='LOSS' if term.winner==1-actor else 'NONLOSS'
                else:
                    replies=child.legal_actions();b['reply_count']=len(replies)
                    for reply in replies:
                        if stopped() or local_calls>=plan['max_replies_per_root'] or time.perf_counter()-tick>=plan['batch_seconds'] or time.perf_counter()-row_tick>=plan['row_seconds']:
                            why='reply_or_time_or_stop_cap';break
                        z=GameSession.replay(c,child.to_record());z.submit(reply)
                        calls+=1;local_calls+=1;b['enumerated']+=1
                        if z.state.terminal_status.is_terminal and z.state.terminal_status.winner==1-actor:
                            b.update(status='LOSS',winning_reply=record_value(reply),reply_record=record_value(z.to_record()),reply_terminal=record_value(z.state.terminal_status));break
                    if b['status']=='UNKNOWN' and b['enumerated']==len(replies):b['status']='NONLOSS'
                branches.append(b)
                if why:break
                if noisy and b['status']=='NONLOSS':status='NO_CANDIDATE_NOISY_LOCAL_SURVIVOR';break
                if not noisy and b['status']=='NONLOSS':status='QUIET_COVERAGE_WITNESS';break
            if why or status!='UNKNOWN':break
        if not why and status=='UNKNOWN':status='NO_CANDIDATE_ALL_ACTIONS_LOCALLY_LOSING'
        x=dict(index=idx,**w,status=status,stop=why,legal_count=len(legal),noisy_count=len(groups[True]),quiet_count=len(groups[False]),branches=branches,reply_transitions=local_calls,seconds=time.perf_counter()-row_tick)
        returns.append(x)
        write_record(out/'returns.json',returns)
        write_record(out/'progress.json',dict(visited=idx+1,total=len(selected),eligible=len(returns),reply_transitions=calls,status=status))
        if status=='QUIET_COVERAGE_WITNESS':halt='FIRST_COMPLETE_EXISTENTIAL_WITNESS';break
        if why:halt=why;break
    write_record(out/'skipped.json',visited)
    summary=dict(input_positions=len(selected),classified=len(visited)+len(returns),eligible=len(returns),
                 candidates=sum(x['status']=='QUIET_COVERAGE_WITNESS' for x in returns),
                 UNKNOWN=sum(x['status']=='UNKNOWN' for x in returns),NOT_RUN=len(selected)-len(visited)-len(returns),
                 reply_transitions=calls,halt=halt,elapsed_seconds=time.perf_counter()-tick,
                 claim='Exposed history existential source certificate;not frequency/WDL or actual search mistake',new_Player_calls=0,new_games=0,new_solver_or_controller=0)
    write_record(out/'summary.json',summary)
    record_interval(begin,stamp(),'analysis',str(out/'summary.json'),out)
    print(summary)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.plan,a.output)
