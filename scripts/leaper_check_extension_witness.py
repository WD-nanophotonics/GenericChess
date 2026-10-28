"""Core-only development witness search; never calls Player/solver or labels WDL."""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
import argparse,time
from scripts.verify_leaper_pvs_quality_pilot import load,action,full_digest
from scripts.leaper_pvs_quality_pilot import make_session
from scripts.research_record import record_value,write_record
from generic_chess.session.session import GameSession
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.ai.alphabeta.quiescence import classify_noisy

def run(inputs,games,out):
    assert not out.exists();out.mkdir(parents=True)
    rows={r['id']:r for r in load(inputs)['rows']};selected=[];counts=Counter();start=datetime.now(timezone.utc).isoformat();tick=time.perf_counter()
    # Selection is the first TWO checked, ongoing full histories per family in
    # original game/ply order. Never condition on scores, winner or effect size.
    for g in load(games):
        f=g['family']
        if counts[f]>=2:continue
        c,s=make_session(rows[g['case_id']]);engine=semantic_engine_for(c)
        for q in g['queries']:
            assert full_digest(s.to_record())==q['record_before_sha256']
            if counts[f]<2 and not s.state.terminal_status.is_terminal and engine.in_check(s.state.position,s.state.position.side_to_move):
                selected.append(dict(case_id=g['case_id'],family=f,game_id=g['game_id'],ply=s.state.ply_count,record=record_value(s.to_record()),fingerprint=g['fingerprint']))
                counts[f]+=1
            if counts[f]>=2:break
            s.submit(action(q['decision']['action'],s))
    write_record(out/'selected-before-expansion.json',dict(at=datetime.now(timezone.utc).isoformat(),selection='first2checkedongoingperfamily/gameplyorder/nooutcomeselection',rows=selected))
    results=[]
    for row in selected:
        c,_=make_session(rows[row['case_id']]);from generic_chess.session.serialization import deserialize_game_record
        import json
        rec=deserialize_game_record(json.dumps(row['record']));s=GameSession.replay(c,rec);engine=semantic_engine_for(c);assert engine.in_check(s.state.position,s.state.position.side_to_move)
        witness=None;tested=0;t=time.perf_counter();stop=None
        for e in sorted(s.legal_actions(),key=str):
            E=GameSession.replay(c,rec);E.submit(e)
            if E.state.terminal_status.is_terminal or engine.in_check(E.state.position,E.state.position.side_to_move):continue
            for r in sorted(E.legal_actions(),key=str):
                if tested>=2000 or time.perf_counter()-t>=10:stop='frozen2000or10secondcap';break
                L=GameSession.replay(c,E.to_record());L.submit(r);tested+=1
                noisy=classify_noisy(E.state,[(r,L.state)],c)
                if not noisy and not L.state.terminal_status.is_terminal:
                    witness=dict(evasion=record_value(e),quiet_opponent_response=record_value(r),E=record_value(E.to_record()),L=record_value(L.to_record()),E_full_sha256=full_digest(E.to_record()),L_full_sha256=full_digest(L.to_record()),not_noisy=True,actor_C=s.state.position.side_to_move,actor_E=E.state.position.side_to_move,actor_L=L.state.position.side_to_move);break
            if witness or stop:break
        results.append(dict(**row,witness=witness,tested_responses=tested,stop=stop,elapsed_seconds=time.perf_counter()-t));write_record(out/'witnesses.json',results)
    families=sorted({r['family'] for r in results if r['witness']})
    result=dict(started_at=start,ended_at=datetime.now(timezone.utc).isoformat(),seconds=time.perf_counter()-tick,selected=len(selected),witnesses=sum(bool(r['witness']) for r in results),families=families,mechanism_gate=len(families)>=3,new_Player=0,new_solver=0,new_games=0,limits='Two actual legal Core moves show potential extra main coverage,not actual search traversal or correctedWDL/quality. All selected histories exposed development. No absent/noisy candidate relabeled quiet.')
    write_record(out/'summary.json',result);print(result)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);p.add_argument('--games',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.inputs,a.games,a.output)
