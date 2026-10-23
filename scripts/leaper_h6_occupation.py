"""Exact analytical uniform-policy occupation on already certified H6 domains."""
from fractions import Fraction as F
from functools import lru_cache
from pathlib import Path
from collections import Counter
import time,json,argparse
from scripts.leaper_explorer_truth import load,save,digest
from scripts.leaper_h6_initial_truth import history_solver,Cap,admit
from scripts.leaper_microgames import role_stop_requested
from scripts.leaper_cooperative_certificate import decode_position

ZERO=(F(0),)*6


def occupation_solver(edges,terms,sides,guard,*,cache_entries=50000,max_calls=2000000):
    solve,wdl_calls=history_solver(edges,terms,sides,guard,max_calls=max_calls)
    calls=0
    @lru_cache(maxsize=cache_entries)
    def visit(i,remaining,prior):
        nonlocal calls
        if calls>=max_calls:raise Cap('OCCUPATION_CALL_CAP_UNKNOWN')
        calls+=1
        if calls%1024==0:guard(calls)
        if i in terms or remaining==0 or i in prior:
            winner=terms.get(i)if i in terms else None
            value=0 if winner is None else 1 if winner==0 else-1
            return tuple(F(int(k==value))for k in(-1,0,1)),F(0),F(0),F(0),ZERO,ZERO
        seen=tuple(sorted((*prior,i)));children=[];vs=[]
        for j in edges[i]:
            children.append(visit(j,remaining-1,seen));vs.append(solve(j,remaining-1,seen)[0])
        n=len(children);mean=lambda xs:sum(xs,F(0))/n
        value=(max if sides[i]==0 else min)(vs);bad=[v!=value for v in vs];fork=len(set(vs))>1
        probs=tuple(mean(ch[0][k]for ch in children)for k in range(3))
        decisions=1+mean(ch[1]for ch in children)
        forks=int(fork)+mean(ch[2]for ch in children)
        losses=F(sum(bad),n)+mean(ch[3]for ch in children)
        first_fork=(F(1),*ZERO[:5])if fork else(F(0),*(mean(ch[4][k]for ch in children)for k in range(5)))
        first_loss=(F(sum(bad),n),*(sum((ch[5][k]for b,ch in zip(bad,children)if not b),F(0))/n for k in range(5)))
        return probs,decisions,forks,losses,tuple(first_fork),tuple(first_loss)
    return visit,lambda:(calls,wdl_calls())


def run(directory,plan,output=None):
    directory=Path(directory);inputs=load(directory/'inputs.json.gz');truth=load(directory/'truth.json.gz');start=time.perf_counter();rows=[];families=[];status='COMPLETE'
    source_by={r['state_sha256']:r for r in inputs['rows']};rby={r['id']:r for r in truth['roots']}
    for family in inputs['families']:
        if family['status']=='MU_UNAVAILABLE':continue
        began=time.perf_counter()
        def guard(calls):
            if role_stop_requested():raise Cap('USER_STOP')
            if time.perf_counter()-start>=plan['whole_cap_seconds']:raise Cap('WHOLE_CAP_UNKNOWN')
            if time.perf_counter()-began>=plan['family_cap_seconds']:raise Cap('FAMILY_CAP_UNKNOWN')
        source=[r for r in inputs['rows']if r['family']==family['family']];c=admit(family,source[0]);domain=load(directory/f"domain{family['family']}.json.gz")
        positions=[decode_position(p,c.initial_position)for p in domain['positions']];edges=domain['edges'];terms={int(k):v for k,v in domain['terminals'].items()}
        visit,calls=occupation_solver(edges,terms,[p.side_to_move for p in positions],guard,cache_entries=plan['memo_entries_per_family'],max_calls=plan['history_calls_per_family'])
        selected=[]
        try:
            for source_row in source:
                guard(0);r=rby[source_row['state_sha256']];v=visit(r['root_index'],6,())
                if sum(v[0])!=1 or sum(v[4])>1 or sum(v[5])>1 or not 0<v[1]<=6:raise ValueError('invalid exact probability/count law')
                if not r['cooperative_decisive']and v[0][0]+v[0][2]!=0:raise ValueError('uniformpolicy scores in proved no-decisive root')
                row=dict(id=r['id'],family_index=family['family'],split=family['split'],
                    uniform_terminal_LDW=list(map(str,v[0])),expected_decisions=str(v[1]),expected_fork_visits=str(v[2]),
                    expected_guarantee_lowering_decisions=str(v[3]),first_fork_ply_mass=list(map(str,v[4])),
                    first_lowering_ply_mass=list(map(str,v[5])))
                rows.append(row);selected.append(row)
        except Cap as exc:status=str(exc)
        if len(selected)!=len(source):break
        n=len(selected);avg=lambda key:sum(F(r[key])for r in selected)/n
        decisions=avg('expected_decisions');forks=avg('expected_fork_visits');losses=avg('expected_guarantee_lowering_decisions')
        item=dict(family=family['family'],masks=family['masks'],roots=n,
            initial_fork_rate=str(F(sum(rby[r['id']]['wdl_fork']for r in selected),n)),
            uniform_terminal_LDW=[str(sum(F(r['uniform_terminal_LDW'][k])for r in selected)/n)for k in range(3)],
            expected_decisions=str(decisions),expected_fork_visits=str(forks),expected_guarantee_lowering_decisions=str(losses),
            decision_weighted_fork_rate=str(forks/decisions),decision_weighted_lowering_rate=str(losses/decisions),
            probability_ever_fork=str(sum(sum(map(F,r['first_fork_ply_mass']))for r in selected)/n),
            probability_ever_lowering=str(sum(sum(map(F,r['first_lowering_ply_mass']))for r in selected)/n),
            first_fork_ply_mass=[str(sum(F(r['first_fork_ply_mass'][k])for r in selected)/n)for k in range(6)],
            first_lowering_ply_mass=[str(sum(F(r['first_lowering_ply_mass'][k])for r in selected)/n)for k in range(6)],
            occupation_calls=calls()[0],wdl_calls=calls()[1],seconds=time.perf_counter()-began)
        families.append(item);print(json.dumps(item),flush=True)
        if status!='COMPLETE':break
    result=dict(format='leaper-H6-exact-uniform-occupation-v1',status=status,truth_digest=digest(truth),plan=plan,rows=rows,families=families,
        seconds=time.perf_counter()-start,scope='Exact independently uniform legal-action law at both seats on the same admitted initial mu. Not actual PRNG/Player games, population/IID inference, policy strength or oracle-selected training. Initial density, decision-weighted visits, event probability and first-event time are separate estimands.')
    if output is not None:save(output,result)
    return result


if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--directory',required=True);cli.add_argument('--plan',required=True);cli.add_argument('--output',required=True);a=cli.parse_args();run(a.directory,load(a.plan),a.output)
