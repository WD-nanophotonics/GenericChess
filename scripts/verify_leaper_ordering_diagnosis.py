"""Data-only replay/qualification for a root-only truth-assisted ordering probe."""
from pathlib import Path
from datetime import datetime
import argparse, json, hashlib, gzip
from collections import defaultdict
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from tools.local_agent.common import write_json


def load(p):
    if not p.exists():p=p.with_suffix(p.suffix+'.gz')
    b=p.read_bytes();b=gzip.decompress(b)if p.suffix=='.gz'else b
    return json.loads(b)


def rows(p):
    if not p.exists():p=p.with_suffix(p.suffix+'.gz')
    b=p.read_bytes();b=gzip.decompress(b)if p.suffix=='.gz'else b
    return [json.loads(x)for x in b.splitlines()if x.strip()]


def qualify(d):
    reg=load(d/'ordering-plan.json');prepared=load(d/'prepared.json');rr=rows(d/'ordering-queries.jsonl')
    assert [r['slot']for r in rr]==reg['slots'],'missing/reordered registered slots'
    compiled={};case_index={};pv_count=0
    for case in prepared['cases']:
        c=L.compile_rule(L.ruleset_from_dict(case['rule']));s=replay(c,case['record'])
        assert L.state_sha(s.state)==case['state_sha256'] and L.record_value(s.state)==case['state']
        assert s.state.position.side_to_move==0 and s.state.ply_count==case['ply']
        assert c.max_ply==64 and c.repetition_limit==4
        assert all(type(a).__name__=='LeapAtom'for t in L.ruleset_from_dict(case['rule']).piece_types for a in t.movement_atoms)
        assert len(case['children'])==len(s.legal_actions())
        for child in case['children']:
            t=replay(c,case['record']);t.submit(L.match_action(t,child['action']))
            assert L.state_sha(t.state)==child['state_sha256']
            assert L.record_value(t.to_record())==child['record']
            assert child['truth']['remaining']==64-t.state.ply_count
        compiled[case['ply']]=c;case_index[case['ply']]=case
    summary=[];by_case=defaultdict(dict)
    for r in rr:
        ply=r['slot']['ply'];case=case_index[ply];c=compiled[ply];dec=r['decision'];s=replay(c,case['record'])
        def truth(a):return next(ch['truth']for ch in case['children']if ch['action']==a)
        L.match_action(s,dec['action']);assert truth(dec['action'])['value']==r['published_child_WDL']
        leaf=replay(c,case['record'])
        for a in dec['principal_variation']:leaf.submit(L.match_action(leaf,a));pv_count+=1
        assert L.record_value(leaf.result)==r['PV_final_result']
        assert dec['runtime_depth_balanced'] and dec['runtime_pushes']==dec['runtime_pops']
        assert dec['qnodes']==0 and dec['result_source']=='main_iteration'
        assert r['PV_plies']==len(dec['principal_variation'])
        assert dec['completed_depth']<=64-ply
        if leaf.result.status.value=='ongoing':assert r['PV_plies']==dec['completed_depth']
        if dec['score']>=900000000:
            assert leaf.result.winner==0 and r['published_child_WDL']==1
        if dec['completed_depth']==64-ply and case['root_truth']['value']==0:assert dec['score']==0
        assert sum(x['count']for x in r['cutoff_positions'])==dec['beta_cutoffs']
        assert all(0<=x['index']<x['frontier'] and x['count']>0 for x in r['cutoff_positions'])
        assert datetime.fromisoformat(r['started_at'])<=datetime.fromisoformat(r['query_ended_at'])<=datetime.fromisoformat(r['ended_at'])<=datetime.fromisoformat(reg['deadline'])
        assert dec['nodes']+dec['qnodes']<=10000000
        assert r['outer_seconds']>=dec['elapsed_seconds']
        assert r['iterations'][-1]['depth']==dec['completed_depth']
        assert r['iterations'][-1]['action']==dec['action'] and r['iterations'][-1]['score']==dec['score']
        for it in r['iterations']:
            assert it['published_child_WDL']==truth(it['action'])['value']
        good=[it for it in r['iterations']if it['published_child_WDL']==case['root_truth']['value']]
        proof=[it for it in r['iterations']if it['score_proves_win']]
        cut=dec['beta_cutoffs'];first=sum(x['count']for x in r['cutoff_positions']if x['index']==0)
        item=dict(slot=r['slot'],completed_depth=dec['completed_depth'],requested_depth=64-ply,complete=dec['completed_depth']==64-ply,reason=dec['termination_reason'],last_action_WDL=r['published_child_WDL'],root_WDL=case['root_truth']['value'],first_correct_iteration=good[0]if good else None,first_proved_win_iteration=proof[0]if proof else None,correct_at_every_completed_iteration=len(good)==len(r['iterations']),outer_seconds=r['outer_seconds'],CPU_seconds=r['cpu_seconds'],nodes=dec['nodes'],qnodes=dec['qnodes'],first_cutoff_fraction=first/cut if cut else None,cutoffs=cut,ordering_seconds=dec['ordering_seconds'],root_order_added_seconds=r['root_order_added_seconds'],limits='First correct action can be a tie selected by exposed labels. A mate-band score requires actual terminal PV; no all-node oracle, no strength or holdout claim.')
        summary.append(item);by_case[ply][r['slot']['arm']]=r
    pairs=[]
    for ply,arms in by_case.items():
        a,b=arms['baseline'],arms['root_truth'];ia={i['depth']:i for i in a['iterations']};ib={i['depth']:i for i in b['iterations']};shared=sorted(set(ia)&set(ib))
        assert all(ia[k]['score']==ib[k]['score']for k in shared),'same-depth exact score mismatch; investigate contract'
        pairs.append(dict(ply=ply,shared_completed_depths=shared,same_scores=True,matched_iteration_work=[dict(depth=k,baseline=ia[k]['nodes']+ia[k]['qnodes'],root_truth=ib[k]['nodes']+ib[k]['qnodes'])for k in shared],warning='Cumulative cold-call iterative work; adjacent depth increments include TT/order learning. Time-only censoring not equal fixed-depth total cost.'))
    return dict(status='PASS',retained_queries=len(rr),entry_failed_attempts=2,entry_failed_values_and_nodes='UNKNOWN; no returned usable decisions',PV_actions=pv_count,summary=summary,pairs=pairs,new_Player_queries=0,new_graph_or_solver_calls=0,original_truth_provenance='Pinned AUX 26d414c; qualified published barrier-rank theorem, not independently re-solved. Current Core root/child/PV binding newly checked.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=qualify(a.directory);write_json(a.output,r);print(json.dumps({k:v for k,v in r.items()if k not in ('summary','pairs')}))
