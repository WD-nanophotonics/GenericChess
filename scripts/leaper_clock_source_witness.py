"""Actual finite-clock endpoint certificates and artificial search-entry controls.

Uses original records/clocks. The <=2-ply terminal-only certificate is not a
general WDL solver; a live leaf invalidates it. Q entry windows are explicitly
artificial, never reconstructed from old PV/score. No controller is implemented.
"""
import argparse
import time
from pathlib import Path
from generic_chess.ai.alphabeta import search as S
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.session.session import GameSession
from scripts.leaper_postexchange_source import load,sha,stamp,stopped
from scripts.leaper_pvs_quality_pilot import make_session,digest
from scripts.leaper_check_extension_quality import record_interval
from scripts.verify_leaper_pvs_quality_pilot import action
from scripts.research_record import record_value,write_record
from tools.local_agent.common import read_json


def terminal_value(term,actor,ply):
    assert term.is_terminal
    return 0 if term.winner is None else (1 if term.winner==actor else -1)*(S.MATE_SCORE-ply)


def certificate(c,s,remaining,budget_end):
    """Literal one/two-ply terminal tree, no recursive evaluator/search."""
    actor=s.state.position.side_to_move;branches=[];transitions=0
    for a in s.legal_actions():
        if stopped() or time.perf_counter()>=budget_end:raise TimeoutError('certificate_cap')
        child=GameSession.replay(c,s.to_record());child.submit(a);transitions+=1
        b=dict(action=record_value(a),child_record=record_value(child.to_record()),terminal=record_value(child.state.terminal_status),replies=[])
        if child.state.terminal_status.is_terminal:
            b['score']=terminal_value(child.state.terminal_status,actor,1)
        else:
            assert remaining==2,'live leaf at exact original H'
            values=[]
            for reply in child.legal_actions():
                if stopped() or time.perf_counter()>=budget_end:raise TimeoutError('certificate_cap')
                z=GameSession.replay(c,child.to_record());z.submit(reply);transitions+=1
                value=terminal_value(z.state.terminal_status,actor,2)
                values.append(value);b['replies'].append(dict(action=record_value(reply),terminal=record_value(z.state.terminal_status),score=value))
            assert values
            b['score']=min(values)
        branches.append(b)
    assert branches
    return dict(score=max(b['score'] for b in branches),branches=branches,Core_transitions=transitions,all_leaves_actual_Core_terminal=True)


def run(plan_path,out):
    plan=read_json(plan_path)
    for p,h in plan['files'].items():assert sha(p)==h
    assert sha(__file__)==plan['source_sha256']
    out.mkdir(exist_ok=False);write_record(out/'frozen.json',plan)
    prepared=next(p for p in plan['files'] if p.endswith('inputs.json'))
    games_path=next(p for p in plan['files'] if p.endswith('games.json'))
    roots={r['id']:r for r in load(prepared)['rows']};games={g['game_id']:g for g in load(games_path)}
    begin,tick=stamp(),time.perf_counter();sealed=[]
    for w in plan['rows']:
        c,s=make_session(roots[w['case_id']]);g=games[w['game_id']]
        for q in g['queries'][:w['query_index']]:s.submit(action(q['decision']['action'],s))
        assert s.state.ply_count==w['absolute_ply'] and c.max_ply-s.state.ply_count==w['remaining']
        sealed.append(dict(**w,record=record_value(s.to_record()),record_sha256=digest(s.to_record())))
    write_record(out/'inputs-before-queries.json',sealed)
    results=[]
    for w in sealed:
        if stopped() or time.perf_counter()-tick>plan['batch_seconds']-35:break
        c,_=make_session(roots[w['case_id']])
        from scripts.leaper_postexchange_source import replay
        s=replay(c,w['record']);x=dict(**w,queries=[])
        try:
            cert=certificate(c,s,w['remaining'],min(tick+plan['batch_seconds'],time.perf_counter()+30))
            x['certificate']=cert
            # Player construction provides the unchanged actual default profile
            # and existing Native providers. choose_action is never invoked.
            p=AlphaBetaPlayer(c,use_disk_cache=False,use_native_semantic_legality=True,use_native_semantic_check=True,use_native_semantic_availability=True)
            x['evaluation_profile']=record_value(p.evaluation_profile)
            for mode in ('Q4','FIRST_Q0','D1','D1_FIRST_Q0'):
                call_begin=stamp();t=time.perf_counter()
                rt=SearchPathRuntime.from_state(s.state,c,history_witnesses=s._search_witnesses,legal_binding_provider=p.native_legality_provider,availability_provider=p.native_legality_provider.has_legal_action,check_provider=p.native_legality_provider.in_check)
                ctx=S._Context(c,p._evaluator,TranspositionTable(),SearchStatistics(),S._Budget(SearchLimits(max_nodes=100000,max_time_seconds=2,quiescence_max_depth=4,quiescence_hard_max_depth=8),None),SearchTuning(),False,True,4,8,None,runtime=rt,first_main_iteration_complete=mode not in ('FIRST_Q0','D1_FIRST_Q0'))
                q=dict(mode=mode,entry_alpha=-S.INF,entry_beta=S.INF,qdepth=0,entry_ply=0,actual_original_entry_context=False,context='ARTIFICIAL_COLD_WIDE_WINDOW_MECHANISM_CONTROL',first_main_iteration_complete=ctx.first_main_iteration_complete)
                try:
                    if mode.startswith('D1'):
                        r=S.negamax(rt.state,1,-S.INF,S.INF,0,ctx);value=r.score;q['best_action']=record_value(r.best_action)
                        branch=next(b for b in cert['branches'] if b['action']==q['best_action'])
                        q['chosen_exact_terminal_value']=branch['score'];q['root_action_exact_optimal']=branch['score']==cert['score']
                    else:value=S.quiescence(rt.state,-S.INF,S.INF,0,0,ctx)
                    q.update(status='RETURNED',score=value,numerical_agreement=value==cert['score'])
                except S.SearchAborted as e:q.update(status='ABORTED_UNKNOWN',reason=str(e))
                rt.assert_balanced();assert digest(s.to_record())==w['record_sha256']
                q.update(stats=record_value(ctx.stats),seconds=time.perf_counter()-t,started_at=call_begin,ended_at=stamp(),runtime_balanced=True)
                x['queries'].append(q);write_record(out/'results.json',results+[x])
            x['status']='COMPLETE'
        except (AssertionError,TimeoutError) as e:x.update(status='UNKNOWN',error_type=type(e).__name__,error=str(e))
        results.append(x);write_record(out/'results.json',results)
    summary=dict(planned=len(sealed),returned=len(results),complete=sum(x['status']=='COMPLETE' for x in results),NOT_RUN=len(sealed)-len(results),queries=sum(len(x['queries']) for x in results),
                 numeric_mismatch={m:sum(q.get('numerical_agreement') is False for x in results for q in x['queries'] if q['mode']==m) for m in ('Q4','FIRST_Q0','D1','D1_FIRST_Q0')},
                 D1_suboptimal=sum(q.get('root_action_exact_optimal') is False for x in results for q in x['queries']),
                 Core_transitions=sum(x.get('certificate',{}).get('Core_transitions',0) for x in results),
                 new_choose_action_calls=0,new_games=0,controller_implemented=False,
                 claim='Finite actual-clock source mechanism only;all Q windows artificial;no old-root causality,cross-rule strength or cost-qualified benefit')
    write_record(out/'summary.json',summary);record_interval(begin,stamp(),'analysis',str(out/'summary.json'),out);print(summary)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.plan,a.output)
