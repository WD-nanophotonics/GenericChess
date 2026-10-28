"""Independent literal Core checks of existential source certificates.

Does not call producer classification/branch functions or run an AI. A negative
certificate needs only one complete noisy survivor. A positive certificate needs
all noisy losing witnesses and one completely enumerated quiet survivor.
"""
import argparse,json,time
from pathlib import Path
from datetime import datetime,timezone
from generic_chess.ai.alphabeta.quiescence import classify_noisy
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.session.session import GameSession
from scripts.leaper_pvs_quality_pilot import make_session,digest
from scripts.verify_leaper_pvs_quality_pilot import action
from scripts.leaper_postexchange_source import load,replay,sha,stopped
from scripts.leaper_check_extension_quality import record_interval
from scripts.research_record import record_value,write_record


def verify(source,out):
    begin=datetime.now(timezone.utc).isoformat();tick=time.perf_counter()
    frozen=load(source/'frozen.json');summary=load(source/'summary.json')
    for p,h in frozen['files'].items():assert sha(p)==h
    roots={r['id']:r for r in load(frozen['prepared'])['rows']}
    games={g['game_id']:g for g in load(frozen['games'])}
    inputs=load(source/'inputs-before-replies.json');returns=load(source/'returns.json');skips=load(source/'skipped.json')
    assert len(inputs)==sum(len(g['queries']) for g in games.values())
    expected=[(g['game_id'],i) for g in games.values() for i in reversed(range(len(g['queries'])))]
    assert [(w['game_id'],w['relative_ply']) for w in inputs]==expected
    covered=sorted(x['index'] for x in returns+skips)
    assert covered==list(range(summary['classified'])) and len(set(covered))==len(covered)
    for w in inputs:
        q=games[w['game_id']]['queries'][w['relative_ply']]
        assert digest(w['record'])==q['record_before_sha256']
        assert w['case_id']==games[w['game_id']]['case_id'] and w['family']==games[w['game_id']]['family']
    compiled={};initial_counts={};transitions=0;counts={};progress=[]
    for x in returns:
        if stopped() or time.perf_counter()-tick>1200:raise TimeoutError('independent reader stop/cap1200s;not PASS')
        w=inputs[x['index']]
        for k in w:assert x[k]==w[k]
        if w['case_id'] not in compiled:compiled[w['case_id']]=make_session(roots[w['case_id']])[0]
        c=compiled[w['case_id']];s=replay(c,w['record']);actor=s.state.position.side_to_move
        assert not s.state.terminal_status.is_terminal and not semantic_engine_for(c).in_check(s.state.position,actor)
        legal=s.legal_actions();assert len(legal)==x['legal_count']
        certified=[]
        for b in x['branches']:
            a=action(b['action'],s);assert a in legal
            child=GameSession.replay(c,s.to_record());child.submit(a);transitions+=1
            assert record_value(child.to_record())==b['child_record']
            noisy=bool(classify_noisy(s.state,[(a,child.state)],c));assert noisy==b['noisy']
            term=child.state.terminal_status;assert record_value(term)==b['terminal']
            if b['status']=='LOSS':
                if term.is_terminal:assert term.winner==1-actor
                else:
                    reply=action(b['winning_reply'],child);assert reply in child.legal_actions()
                    z=GameSession.replay(c,child.to_record());z.submit(reply);transitions+=1
                    assert z.state.terminal_status.is_terminal and z.state.terminal_status.winner==1-actor
                    assert record_value(z.to_record())==b['reply_record']
                    assert record_value(z.state.terminal_status)==b['reply_terminal']
            elif b['status']=='NONLOSS':
                if term.is_terminal:assert term.winner!=1-actor
                else:
                    replies=child.legal_actions();assert len(replies)==b['reply_count']==b['enumerated']
                    for reply in replies:
                        z=GameSession.replay(c,child.to_record());z.submit(reply);transitions+=1
                        assert not(z.state.terminal_status.is_terminal and z.state.terminal_status.winner==1-actor)
            else:assert b['status']=='UNKNOWN' and x['status']=='UNKNOWN'
            certified.append((a,noisy,b['status']))
        if x['status']=='NO_CANDIDATE_NOISY_LOCAL_SURVIVOR':assert any(n and st=='NONLOSS' for a,n,st in certified)
        elif x['status']=='QUIET_COVERAGE_WITNESS':
            noisy_actions=set()
            for a in legal:
                child=GameSession.replay(c,s.to_record());child.submit(a);transitions+=1
                if classify_noisy(s.state,[(a,child.state)],c):noisy_actions.add(a)
            assert noisy_actions and noisy_actions=={a for a,n,st in certified if n and st=='LOSS'}
            assert any(not n and st=='NONLOSS' for a,n,st in certified)
        elif x['status']=='NO_CANDIDATE_ALL_ACTIONS_LOCALLY_LOSING':assert set(legal)=={a for a,n,st in certified if st=='LOSS'}
        else:assert x['status']=='UNKNOWN'
        counts[x['status']]=counts.get(x['status'],0)+1
        progress.append(dict(index=x['index'],status='VERIFIED',Core_transitions=transitions))
        write_record(out/'progress.json',dict(verified=len(progress),planned=len(returns),counts=counts,Core_transitions=transitions))
    # Skipped sources were not asserted to be losing or safe. Independently
    # check the semantic reason before including them in whole-source coverage.
    for x in skips:
        if stopped() or time.perf_counter()-tick>1200:raise TimeoutError('independent reader stop/cap1200s;not PASS')
        w=inputs[x['index']]
        if w['case_id'] not in compiled:compiled[w['case_id']]=make_session(roots[w['case_id']])[0]
        c=compiled[w['case_id']];s=replay(c,w['record'])
        if w['case_id'] not in initial_counts:initial_counts[w['case_id']]=sum(p is not None for p in make_session(roots[w['case_id']])[1].state.position.board)
        initial_count=initial_counts[w['case_id']]
        post=sum(p is not None for p in s.state.position.board)<initial_count
        assert post==w['after_material_removal']
        if x['status']=='NOT_POST_REMOVAL':assert not post
        elif x['status']=='IN_CHECK_OR_TERMINAL':assert s.state.terminal_status.is_terminal or semantic_engine_for(c).in_check(s.state.position,s.state.position.side_to_move)
        elif x['status']=='NOT_MIXED':
            flags=[]
            for a in s.legal_actions():
                child=GameSession.replay(c,s.to_record());child.submit(a);transitions+=1
                flags.append(bool(classify_noisy(s.state,[(a,child.state)],c)))
            assert sum(flags)==x['noisy'] and len(flags)-sum(flags)==x['quiet'] and (not any(flags) or all(flags))
        else:raise AssertionError('unknown skip reason')
    result=dict(status='PASS',actual_input_records=len(inputs),certificates=len(returns),skips=len(skips),statuses=counts,Core_transitions=transitions,NOT_RUN=summary['NOT_RUN'],scope='Literal fullhistory source certificates and skipped reasons;no search-value/causal or WDL generalization')
    write_record(out/'verification.json',result);record_interval(begin,datetime.now(timezone.utc).isoformat(),'validation',str(out/'verification.json'),out);print(result)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(exist_ok=False);verify(a.source,a.output)
