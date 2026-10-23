"""Exact *nominal* policy utility and tie intervals on the existing H6 mu.

No Player, simulation or learning. Uniform-tie values are not claims about
the actual implementation's deterministic tie rule. Optimistic/pessimistic
tie envelopes allow arbitrary history-dependent choices within nominal sets.
"""
from collections import Counter
from fractions import Fraction as F
from functools import lru_cache
from pathlib import Path
import argparse,json,time,hashlib
from scripts.leaper_explorer_truth import load,digest
from scripts.leaper_h6_initial_truth import admit
from scripts.leaper_cooperative_certificate import decode_position
from scripts.leaper_h6_headroom import evaluate
from scripts.leaper_microgames import role_stop_requested


def policy_values(edges,terminals,sides,ended,truth,decision,depth,price,foe,guard=lambda:None):
    """Return (uniform-tie WLD, min utility tie, max utility tie, regret)."""
    calls=Counter()
    @lru_cache(None)
    def walk(i,h,prior):
        calls['policy_contexts']+=1
        if calls['policy_contexts']%2048==0:guard()
        if ended(i,h,prior):
            v=truth(i,h,prior);dist=tuple(F(int(v==k))for k in(1,0,-1))
            return dist,F(v),F(v),F(0)
        pp=prior|1<<i
        if sides[i]==0:
            dg=decision(i,h,prior,depth,price);selected=[edges[i][k]for k in dg['chosen']]
            children=[walk(j,h-1,pp)for j in selected]
            dist=tuple(sum(x[0][k]for x in children)/len(children)for k in range(3))
            return dist,min(x[1]for x in children),max(x[2]for x in children),dg['error']+sum(x[3]for x in children)/len(children)
        selected=edges[i]
        immediate=[j for j in selected if j in terminals and terminals[j]==1]
        if foe=='FLOOR'and immediate:selected=immediate[:1]
        children=[walk(j,h-1,pp)for j in selected]
        dist=tuple(sum(x[0][k]for x in children)/len(children)for k in range(3))
        return dist,sum(x[1]for x in children)/len(children),sum(x[2]for x in children)/len(children),sum(x[3]for x in children)/len(children)
    return walk,calls


def analyze(directory,output,models,*,seconds=180):
    directory=Path(directory);output=Path(output);output.mkdir(parents=True,exist_ok=False);tick=time.perf_counter()
    inputs=load(directory/'inputs.json.gz');truth=load(directory/'truth.json.gz');adj=load(directory/'adjacent-pairs.json.gz')
    plan=dict(question='Can all final-positive-cell nominal choices be truth-optimal while actual useful policy gain remains unmeasured?',
        inputs_digest=digest(inputs),truth_digest=digest(truth),pairs_digest=digest(adj),models=models,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),seconds_cap=seconds,
        support='Same two exposed rules and all original128freshstarts each; no new sampled rules, histories or Player.',
        interpretation='Exact chance-opponent utility of nominal uniform-tie policies plus arbitrary-tie envelopes. Not actual deterministic tie policy or empirical measured gain; no updates or counterfactual training.')
    (output/'plan.json').write_text(json.dumps(plan,indent=2))
    def guard():
        if role_stop_requested():raise RuntimeError('USER_STOP')
        if time.perf_counter()-tick>=seconds:raise RuntimeError('POLICY_BOUNDS_CAP_UNKNOWN_NO_REFILL')
    source={r['id']:r for r in truth['roots']};rows=[];counts=Counter()
    for pair in adj['pairs']:
      for tag,key in(('left_family','left_id'),('right_family','right_id')):
        f=next(f for f in inputs['families']if f['family']==pair[tag]);first=next(r for r in inputs['rows']if r['family']==f['family']);c=admit(f,first);d=load(directory/f"domain{f['family']}.json.gz")
        expected=next(r['domain_digest']for r in load(directory/'summary.json')['families']if r['family']==f['family'])
        if digest(d)!=expected:raise ValueError('domain differs')
        positions=[decode_position(p,c.initial_position)for p in d['positions']];sides=[p.side_to_move for p in positions]
        features=[(sum(p is not None and(p.owner,p.current_type_id)==(0,'A')for p in pos.board),-sum(p is not None and(p.owner,p.current_type_id)==(1,'B')for p in pos.board))for pos in positions]
        terms={int(i):v for i,v in d['terminals'].items()};ended,exact,nominal,decision,work=evaluate(d['edges'],terms,sides,features,guard)
        weights=next(m['weights']for m in models if m['family']==f['family']);B=F(str(weights[1]))
        if not F(1)<B<F(500000):raise ValueError('final positive price cell differs')
        for foe in('UNIFORM','FLOOR'):
          for label,depth,price in(('unitD1',1,F(1)),('positive_cellD1',1,F(2)),('finalD1',1,B),('unitD2',2,F(1))):
            guard();walk,paid=policy_values(d['edges'],terms,sides,ended,exact,decision,depth,price,foe,guard)
            rr=[]
            for r in pair['rows']:
                i=source[r[key]]['root_index'];dist,lo,hi,regret=walk(i,6,0)
                if sum(dist)!=1 or lo>dist[0]-dist[2]or dist[0]-dist[2]>hi:raise ValueError('invalid nominal policy bounds')
                rr.append(dict(id=r[key],exact_WDL=exact(i,6,0),WLD=list(map(str,dist)),U=str(dist[0]-dist[2]),tie_U_bounds=[str(lo),str(hi)],expected_bad_decisions=str(regret)))
            mean=lambda fn:sum(fn(r)for r in rr)/len(rr)
            rows.append(dict(family=f['family'],foe=foe,policy=label,depth=depth,B=str(price),roots=len(rr),
                WLD=[str(mean(lambda r:F(r['WLD'][k])))for k in range(3)],
                U=str(mean(lambda r:F(r['U']))),tie_U_bounds=[str(mean(lambda r:F(r['tie_U_bounds'][k])))for k in range(2)],
                expected_bad_decisions=str(mean(lambda r:F(r['expected_bad_decisions']))),root_rows=rr))
            counts.update(paid);print({k:v for k,v in rows[-1].items()if k!='root_rows'},flush=True)
        counts.update(work)
    result=dict(status='PASS',plan=plan,rows=rows,counts=dict(counts),seconds=time.perf_counter()-tick)
    (output/'result.json').write_text(json.dumps(result,indent=2));return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--models',type=Path,required=True);a=p.parse_args();analyze(a.directory,a.output,load(a.models)['models'])
