"""Prospective bounded descriptor census for the next source-design question.
No reply expansion, WDL labels, Player, solver/controller or new game.
"""
import argparse,json,time,hashlib
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
from scripts.leaper_pvs_quality_pilot import make_session
from scripts.verify_leaper_pvs_quality_pilot import action
from scripts.research_record import record_value,write_record
from generic_chess.session.session import GameSession
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.ai.alphabeta.quiescence import classify_noisy
from tools.local_agent import session
from tools.local_agent.common import read_json
from scripts.leaper_check_extension_quality import record_interval

def stamp():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def run(prepared,games,plan_path,out):
    assert not out.exists();plan=read_json(plan_path);assert sha(__file__)==plan['source_sha256'] and sha(games)==plan['games_sha256'] and sha(prepared/'inputs.json')==plan['input_sha256'];out.mkdir()
    write_record(out/'frozen.json',plan);roots={r['id']:r for r in json.loads((prepared/'inputs.json').read_bytes())['rows']};counts=Counter();rows=[];tick=time.perf_counter();halt=None
    for g in json.loads(games.read_bytes()):
        if counts[g['family']]>=24:continue
        c,s=make_session(roots[g['case_id']]);engine=semantic_engine_for(c)
        for qi,q in enumerate(g['queries']):
            if counts[g['family']]>=24:break
            if time.perf_counter()-tick>=plan['batch_seconds']:halt='batch_cap';break
            flags=[read_json(Path('.local_agent')/(n+'.json')) for n in ('rollout','advisor','slack')]
            if any(x.get(k,False) for x in flags for k in ('stopped','research_stopped','stop_requested','user_paused')):halt='scoped_stop';break
            begin=stamp();t=time.perf_counter();legal=s.legal_actions();noisy=[];quiet=[];why=None
            for a in legal:
                if time.perf_counter()-t>=plan['row_seconds'] or time.perf_counter()-tick>=plan['batch_seconds']:why='cap';break
                child=GameSession.replay(c,s.to_record());child.submit(a)
                (noisy if classify_noisy(s.state,[(a,child.state)],c) else quiet).append(record_value(a))
            checked=engine.in_check(s.state.position,s.state.position.side_to_move);complete=why is None and len(noisy)+len(quiet)==len(legal)
            x=dict(family=g['family'],case_id=g['case_id'],game_id=g['game_id'],relative_ply=qi,record=record_value(s.to_record()),in_check=checked,legal_count=len(legal),noisy=noisy,quiet=quiet,complete=complete,status='COMPLETE' if complete else 'UNKNOWN',next_source_candidate=complete and not checked and bool(noisy) and bool(quiet),started_at=begin,ended_at=stamp(),seconds=time.perf_counter()-t)
            rows.append(x);counts[g['family']]+=1;write_record(out/'rows.json',rows);record_interval(begin,x['ended_at'],'analysis',str(out/'rows.json')+':'+str(g['family'])+':'+str(qi),out);s.submit(action(q['decision']['action'],s))
            if why:halt='row_cap';break
        if halt:break
    selected=[next((x for x in rows if x['family']==f and x['next_source_candidate']),None) for f in range(8)]
    write_record(out/'next-source-inputs.json',dict(rows=selected,selection='FIRST mixed-noisy/quiet noncheck frontier per ALL8families from fixed first24observedpositions;not scores/winners/localreply outcomes',new_reply_expansion=0,claim='Descriptor eligibility only;not forced defense,actual Qvisit or WDL'))
    summary=dict(planned_positions=192,observed=len(rows),by_family=dict(counts),complete=sum(x['complete'] for x in rows),mixed_noncheck=sum(x['next_source_candidate'] for x in rows),next_families=[f for f,x in enumerate(selected) if x],halt=halt,new_Player_calls=0,new_games=0,new_solver_controller=0,next_reply_census='NOT_STARTED;requires separately frozen finite design,not refill of closed8-firstquiet census',limitations='Exposed posthoc DEVELOPMENT position descriptors;no winner/score selection,forcing proof or quality claim.')
    write_record(out/'summary.json',summary);print(json.dumps(summary))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepared',type=Path,required=True);p.add_argument('--games',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.prepared,a.games,a.plan,a.output)
