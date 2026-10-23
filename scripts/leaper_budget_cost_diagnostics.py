"""Account for paid search, interface and recording costs of CLOSED Leaper runs.

No new queries. Residual time combines setup, submission and record transport;
it does not causally isolate disk I/O. Unknown serving costs remain unidentified.
"""
import argparse
from pathlib import Path
from collections import defaultdict
from scripts import leaper_design as L


def analyze(d):
    r=L.load(d/'results.json');assert r['status']=='CLOSED';ww=L.load(d/'inputs.json')['worlds'];rows=[];groups=defaultdict(lambda:defaultdict(float));raw={}
    for sl in r['slots']:
        if not sl.get('receipt'):continue
        g=L.load(d/sl['receipt']);qs=g['queries'];main=sum(q['decision']['nodes']for q in qs);qn=sum(q['decision']['qnodes']for q in qs)
        interface=sum(q['seconds']for q in qs);search=sum(q['decision']['elapsed_seconds']for q in qs);outer=g['seconds']-interface
        assert interface+1e-6>=search and outer>=-1e-6
        row=dict(world=sl['world'],code=ww[sl['world']]['code_world'],placement=ww[sl['world']]['placement_index'],pair=sl['pair'],role=sl['role'],known=sl['utility'][0]==sl['utility'][1],utility=sl['utility'],queries=len(qs),main_nodes=main,qnodes=qn,total_nodes=main+qn,interface_seconds=interface,reported_search_seconds=search,setup_submit_record_residual_seconds=outer,game_seconds=g['seconds'])
        rows.append(row);raw[sl['world'],sl['pair']]=row
        for key in ('ALL',f"pair:{sl['pair']}",f"code:{row['code']}",f"code:{row['code']}/pair:{sl['pair']}"):
            for f in ('queries','main_nodes','qnodes','total_nodes','interface_seconds','reported_search_seconds','setup_submit_record_residual_seconds','game_seconds'):groups[key][f]+=row[f]
            groups[key]['physical_executions']+=1;groups[key]['known']+=row['known']
    total=groups['ALL'];assert r['seconds']+1e-6>=total['game_seconds'];virtual=None
    if set(L.load(d/'registration.json')['pairs'])=={'LL','HL','LH'}:
        complete=all((w['world'],p)in raw and raw[w['world'],p]['known']for w in ww for p in ('LL','HL','LH'))
        virtual={'fully_identified':complete,'scope':'LL(role0)+LH(role1) versus HL(role0)+LH(role1); derived reuse, not new executions/timings.'}
        if complete:
            for f in ('total_nodes','queries','reported_search_seconds','interface_seconds','game_seconds'):
                a=sum(raw[w['world'],'LL'][f]+raw[w['world'],'LH'][f]for w in ww);h=sum(raw[w['world'],'HL'][f]+raw[w['world'],'LH'][f]for w in ww);virtual[f]={'adaptive':a,'always_high':h,'ratio':None if not h else a/h}
    out=dict(status='CLOSED',actual_partial_and_complete_paid_cost=dict(total),groups={k:dict(v)for k,v in groups.items()},rows=rows,virtual_serving_comparison=virtual,loop_seconds=r['seconds'],between_game_final_persistence_residual_seconds=r['seconds']-total['game_seconds'],UNKNOWN=sum(s['utility'][0]!=s['utility'][1]for s in r['slots']),scope='All actual paid costs, not known-only utility imputation. Residuals combine setup/submit/serialization/saving, not a disk-only benchmark. Reported search clock, outer query clock and total wall clock are distinct. Node/ply budgets do not guarantee wall ratios. Frozen criterion remains the registered total-node ratio.')
    L.write_record(d/'cost-decomposition.json',out);print({k:out[k]for k in ('actual_partial_and_complete_paid_cost','virtual_serving_comparison','loop_seconds','between_game_final_persistence_residual_seconds','UNKNOWN')},flush=True)


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();analyze(a.output)
if __name__=='__main__':main()
