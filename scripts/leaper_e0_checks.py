"""Literal full-history qualification of E0 depth and query-cost claims.

Shared Core replay, not independent WDL or another solver. New Player calls: 0.
"""
import argparse,json,time
from collections import Counter
from pathlib import Path
from scripts import leaper_design as L


def qualify(d):
    tick=time.perf_counter();res=L.load(d/('recovered-results.json' if (d/'recovered-results.json').exists() else 'results.json'));assert res['status']=='CLOSED';ws=L.load(d/'inputs.json')['worlds'];counts=Counter();examples=[];maxratio=0;bindings=[]
    for slot in res['slots']:
        if slot['status']!='finished':continue
        g=L.load(d/slot['receipt']);w=ws[slot['world']];c=L.compile_rule(L.ruleset_from_dict(w['rule']));s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(g['initial_record'])));assert g['initial_record']==w['initial_record'];final=L.deserialize_game_record(json.dumps(g['final_record']));prefix=s.to_record().actions;assert final.actions[:len(prefix)]==prefix
        for q,raw_action in zip(g['queries'],final.actions[len(prefix):],strict=True):
            assert q['state_sha256']==L.state_sha(s.state) and q['actor']==s.state.position.side_to_move
            a=L.match_action(s,q['action']);assert L.record_value(raw_action)==q['action'] and len(s.legal_actions())==q['legal_count'];dec=q.get('decision')
            if dec:
                assert dec['action']==q['action'];counts['Player_returns']+=1;counts['main_nodes']+=dec['nodes'];counts['qnodes']+=dec['qnodes'];maxratio=max(maxratio,(dec['nodes']+dec['qnodes'])/q['node_budget']);counts['reported_sources:'+str(dec.get('result_source'))]+=1
                counts['actual_iterations:'+str(dec['completed_depth'])]+=1
                pv=L.GameSession.replay(c,s.to_record())
                for v in dec['principal_variation']:pv.submit(L.match_action(pv,v));counts['literal_PV_edges']+=1
                if dec['completed_depth']==0:
                    child=L.GameSession.replay(c,s.to_record());child.submit(a);assert child.state.terminal_status.is_terminal and child.result.winner==q['actor'],'D0 exception must be actual scoring child';counts['D0_actual_winning_children']+=1
                elif dec['completed_depth']<q['requested_depth']:
                    counts['undercompleted_requested_depth']+=1
                    if len(examples)<8:examples.append({'slot':slot['slot'],'ply':q['root_ply'],'completed':dec['completed_depth'],'requested':q['requested_depth'],'node_budget':q['node_budget']})
            s.submit(a);counts['history_actions']+=1
        assert L.record_value(s.to_record())==g['final_record'] and L.record_value(s.state)==g['final_state'] and L.record_value(s.result)==g['terminal'];expected=L.outcome_value(s.result,g['role'],g['censor']);assert g['utility']==([expected,expected] if expected is not None else [-1,1]);counts['finished_deployments']+=1;bindings.append({'slot':slot['slot'],'sha256':L.sha(d/slot['receipt'])})
    out={'status':'PASS','counts':dict(counts),'max_reported_nodes_plus_q_over_node_cap':maxratio,'undercompleted_examples':examples,'actual_game_file_bindings':bindings,'seconds':time.perf_counter()-tick,'new_Player_calls':0,'scope':'Literal typedhistory/legality/selectedPV andD0winningchild checks throughsameauthoritativeCore. Reported counters/sources are observedfields, not binaryattestation or independent WDL. Undercompletion retained; no relabeling.'};L.write_record(d/'e0-qualification.json',out);print({'status':out['status'],'counts':out['counts'],'seconds':out['seconds']},flush=True);return out


def main():
 p=argparse.ArgumentParser(__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();qualify(a.output)
if __name__=='__main__':main()
