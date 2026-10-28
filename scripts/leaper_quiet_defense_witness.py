"""Fixed saved-history, two-ply Core terminal-reply census for source design.

No controller/solver is implemented and no full WDL is assigned. A move with
no immediate losing reply may lose later. Q-policy exclusion is classified,
not claimed observed in an actual qsearch invocation or causally responsible
for a game's outcome.
"""
import argparse,json,time,hashlib
from pathlib import Path
from datetime import datetime,timezone
from scripts.leaper_pvs_quality_pilot import make_session
from scripts.verify_leaper_pvs_quality_pilot import action
from scripts.research_record import record_value,write_record
from generic_chess.session.session import GameSession
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.ai.alphabeta.quiescence import classify_noisy
from tools.local_agent import session
from tools.local_agent.common import read_json

def stamp():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def run(prepared,games_path,plan_path,out):
    assert not out.exists();plan=read_json(plan_path)
    assert sha(prepared/'inputs.json')==plan['input_sha256'] and sha(games_path)==plan['games_sha256']
    assert sha(__file__)==plan['source_sha256']
    roots={r['id']:r for r in json.loads((prepared/'inputs.json').read_bytes())['rows']};games=json.loads(games_path.read_bytes());out.mkdir()
    write_record(out/'frozen.json',plan);selected=[];seen=set();selection=[];tick=time.perf_counter();halt=None
    for g in games:
        if g['family'] in seen:continue
        c,s=make_session(roots[g['case_id']]);engine=semantic_engine_for(c)
        for qi,q in enumerate(g['queries']):
            if time.perf_counter()-tick>plan['batch_seconds']:halt='selection_budget';break
            a=action(q['decision']['action'],s);checked=engine.in_check(s.state.position,s.state.position.side_to_move)
            child=GameSession.replay(c,s.to_record());child.submit(a)
            noisy=bool(classify_noisy(s.state,[(a,child.state)],c))
            accept=not checked and not noisy and not child.state.terminal_status.is_terminal
            selection.append(dict(case_id=g['case_id'],family=g['family'],game_id=g['game_id'],relative_ply=qi,in_check=checked,noisy=noisy,accept=accept))
            if accept:
                selected.append(dict(case_id=g['case_id'],family=g['family'],game_id=g['game_id'],relative_ply=qi,record=record_value(s.to_record()),actual_quiet_action=record_value(a)));seen.add(g['family']);break
            s.submit(a)
        if halt:break
    write_record(out/'selection-log.json',selection);write_record(out/'selected-before-reply-expansion.json',selected)
    results=[]
    for w in selected:
        begin=stamp();t=time.perf_counter();row=roots[w['case_id']];c,_=make_session(row);s=GameSession.replay(c,__import__('generic_chess.session.serialization',fromlist=['deserialize_game_record']).deserialize_game_record(json.dumps(w['record'])));engine=semantic_engine_for(c)
        assert not s.state.terminal_status.is_terminal and not engine.in_check(s.state.position,s.state.position.side_to_move)
        actor=s.state.position.side_to_move;branches=[];count=0;why=None
        for a in s.legal_actions():
            flags=[read_json(Path('.local_agent')/(n+'.json')) for n in ('rollout','advisor','slack')]
            if any(f.get(k,False) for f in flags for k in ('stopped','research_stopped','stop_requested','user_paused')):why='scoped_stop';break
            if time.perf_counter()-t>=plan['row_seconds'] or time.perf_counter()-tick>=plan['batch_seconds']:why='time_cap';break
            child=GameSession.replay(c,s.to_record());child.submit(a);noisy=bool(classify_noisy(s.state,[(a,child.state)],c));term=child.state.terminal_status
            b=dict(action=record_value(a),noisy=noisy,child_record=record_value(child.to_record()),root_child_terminal=record_value(term),opponent_legal_replies=0,enumerated=0,status='UNKNOWN',winning_reply=None)
            if term.is_terminal:b['status']='ROOT_TERMINAL'
            else:
                replies=child.legal_actions();b['opponent_legal_replies']=len(replies)
                for reply in replies:
                    if count>=plan['max_replies_per_root'] or time.perf_counter()-t>=plan['row_seconds'] or time.perf_counter()-tick>=plan['batch_seconds']:why='reply_or_time_cap';break
                    z=GameSession.replay(c,child.to_record());z.submit(reply);count+=1;b['enumerated']+=1
                    if z.state.terminal_status.is_terminal and z.state.terminal_status.winner==1-actor:
                        b.update(status='HAS_OPPONENT_TERMINAL_WIN_REPLY',winning_reply=record_value(reply),reply_record=record_value(z.to_record()),reply_terminal=record_value(z.state.terminal_status));break
                if b['status']=='UNKNOWN' and b['enumerated']==len(replies):b['status']='NO_OPPONENT_TERMINAL_WIN_REPLY_ALL_ENUMERATED'
            branches.append(b)
            if why:break
        complete=why is None and len(branches)==len(s.legal_actions()) and all(b['status']!='UNKNOWN' for b in branches)
        surviving=[b for b in branches if b['status']=='NO_OPPONENT_TERMINAL_WIN_REPLY_ALL_ENUMERATED' or b['status']=='ROOT_TERMINAL' and b['root_child_terminal']['winner'] in (actor,None)]
        losing=[b for b in branches if b['status']=='HAS_OPPONENT_TERMINAL_WIN_REPLY']
        candidate=complete and bool(surviving) and bool(losing) and any(b['noisy'] for b in branches) and all(not b['noisy'] for b in surviving)
        x=dict(**w,complete=complete,stop=why,legal_root_actions=len(s.legal_actions()),branches=branches,enumerated_replies=count,local_avoidance_actions=len(surviving),locally_losing_actions=len(losing),coverage_omission_candidate=candidate,started_at=begin,ended_at=stamp(),seconds=time.perf_counter()-t)
        results.append(x);write_record(out/'witnesses.json',results);session.record_work(begin,x['ended_at'],'analysis',str(out/'witnesses.json')+':'+str(w['family']))
    summary=dict(selected=len(selected),families=sorted(seen),complete=sum(x['complete'] for x in results),coverage_candidates=sum(x['coverage_omission_candidate'] for x in results),Core_reply_transitions=sum(x['enumerated_replies'] for x in results),halt=halt,source_design='COVERAGE_CANDIDATE_ONLY' if any(x['coverage_omission_candidate'] for x in results) else 'NO_GO_NO_LOCAL_FORCING_WITNESS_IN_FIXED_CENSUS',implementation='NO_GO:requires actual search-return dependency and cost-qualified safe admission;local survival beyond one reply is NOT fullWDL',new_Player_calls=0,new_games=0,new_solver_controller=0,limitations='Posthoc exposed DEVELOPMENT histories,firstquiet selection ignores scores/winners. Two-ply actual-Core terminal-reply properties only;no unique game-cause,full-defense/WDL/strength or all-domain claim.')
    write_record(out/'summary.json',summary);print(json.dumps(summary))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepared',type=Path,required=True);p.add_argument('--games',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.prepared,a.games,a.plan,a.output)
