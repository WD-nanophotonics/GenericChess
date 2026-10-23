"""Zero-Player headroom under the existing, fixed H6 incoming laws.

These are nominal minimax sets, with uniform selection among score ties.
They are neither actual mainline tie choices nor learned-policy occupation.
Oracle information is used only after the incoming distribution is fixed.
"""
from collections import Counter, defaultdict
from fractions import Fraction as F
from functools import lru_cache
from pathlib import Path
import argparse,gzip,hashlib,json,time

from scripts.leaper_explorer_truth import load,digest
from scripts.leaper_h6_initial_truth import admit
from scripts.leaper_cooperative_certificate import decode_position
from scripts.leaper_microgames import role_stop_requested
from generic_chess.learning.incremental import MATE


def evaluate(edges,terminals,sides,features,guard=lambda:None):
    """Exact history and finite nominal search, seat0 convention throughout."""
    calls=Counter()
    def ended(i,h,prior):return i in terminals or h==0 or bool(prior>>i&1)
    @lru_cache(None)
    def truth(i,h,prior):
        calls['truth']+=1
        if calls['truth']%2048==0:guard()
        if i in terminals:return 0 if terminals[i] is None else 1 if terminals[i]==0 else -1
        if h==0 or prior>>i&1:return 0
        pp=prior|1<<i
        return (max if sides[i]==0 else min)(truth(j,h-1,pp)for j in edges[i])
    @lru_cache(None)
    def nominal(i,h,prior,depth,price):
        calls['nominal']+=1
        if calls['nominal']%4096==0:guard()
        if ended(i,h,prior):return MATE*truth(i,h,prior)
        if depth==0:
            A,B=features[i];return A+price*B
        pp=prior|1<<i
        return (max if sides[i]==0 else min)(nominal(j,h-1,pp,depth-1,price)for j in edges[i])
    def decision(i,h,prior,depth,price):
        if ended(i,h,prior):raise ValueError('ongoing context required')
        pp=prior|1<<i;exact=[truth(j,h-1,pp)for j in edges[i]]
        best=(max if sides[i]==0 else min)(exact)
        scores=[nominal(j,h-1,pp,depth-1,price)for j in edges[i]]
        target=(max if sides[i]==0 else min)(scores)
        chosen=tuple(k for k,v in enumerate(scores)if v==target)
        inferior=sum(exact[k]!=best for k in chosen)
        return dict(best=best,chosen=chosen,error=F(inferior,len(chosen)),
                    any_bad=inferior>0,all_bad=inferior==len(chosen),
                    fork=len(set(exact))>1,exact=exact,scores=scores)
    return ended,truth,nominal,decision,calls


def analyze(directory,output,*,seconds=180):
    directory=Path(directory);output=Path(output)
    output.mkdir(parents=True,exist_ok=False);tick=time.perf_counter()
    inputs=load(directory/'inputs.json.gz');truth=load(directory/'truth.json.gz');adj=load(directory/'adjacent-pairs.json.gz')
    laws=load(Path('docs/research/data/leaper_pair_transfer_20261024/policy-laws.json.gz'))
    profiles=[(d,p)for d in(1,2,3)for p in(F(1,2),F(1),F(2))]
    plan=dict(question='What nominal zero-training error remains outside the price-sensitive panel, and does depth remove it?',
        inputs_digest=digest(inputs),truth_digest=digest(truth),pairs_digest=digest(adj),laws_digest=digest(laws),
        profiles=[dict(depth=d,B=str(p))for d,p in profiles],seconds_cap=seconds,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        support='Every original128start/rule and every later complete repeat2 history class under seat0UNIFORM/seat1UNIFORM or FLOOR. No outcome filtering, newPlayer, training, old-slot refill or new initial distribution.',
        interpretation='Nominal uniform-tie error under fixed incoming law. Not actual mainline action/tie choice, policy outcome, training occupation or strength.')
    (output/'plan.json').write_text(json.dumps(plan,indent=2))
    def guard():
        if role_stop_requested():raise RuntimeError('USER_STOP')
        if time.perf_counter()-tick>=seconds:raise RuntimeError('HEADROOM_CAP_UNKNOWN_NO_REFILL')
    roots={r['id']:r for r in truth['roots']};rows=[];counts=Counter();examples=[]
    for pair in adj['pairs']:
      for tag,key in(('left_family','left_id'),('right_family','right_id')):
        family=next(f for f in inputs['families']if f['family']==pair[tag]);first=next(r for r in inputs['rows']if r['family']==family['family']);c=admit(family,first)
        domain=load(directory/f"domain{family['family']}.json.gz")
        old=next(f for f in load(directory/'summary.json')['families']if f['family']==family['family'])
        if digest(domain)!=old['domain_digest']:raise ValueError('source domain differs')
        positions=[decode_position(p,c.initial_position)for p in domain['positions']]
        edges=domain['edges'];terms={int(i):v for i,v in domain['terminals'].items()};sides=[p.side_to_move for p in positions];features=[]
        for pos in positions:
            if pos.aux_state or any(h.counts for h in pos.hands):raise ValueError('unsupported affine state')
            if any(p and(p.current_type_id not in('K','A','B')or p.promoted or p.base_type_id!=p.current_type_id or(p.current_type_id=='A'and p.owner!=0)or(p.current_type_id=='B'and p.owner!=1))for p in pos.board):raise ValueError('unsupported affine actor')
            A=sum(p is not None and(p.owner,p.current_type_id)==(0,'A')for p in pos.board);B=sum(p is not None and(p.owner,p.current_type_id)==(1,'B')for p in pos.board)
            if A not in(0,1)or B not in(0,1):raise ValueError('affine multiplicity differs')
            features.append((A,-B))
        ended,solve,nominal,diagnostic,work=evaluate(edges,terms,sides,features,guard)
        for foe in('UNIFORM','FLOOR'):
            incoming=defaultdict(F)
            for r in pair['rows']:incoming[roots[r[key]]['root_index'],6,0]+=F(1,len(pair['rows']))
            mass=defaultdict(F);tables={pr:defaultdict(F)for pr in profiles};steps=[];unique=Counter()
            for ply in range(6):
                guard();new=defaultdict(F);step=defaultdict(F)
                for(i,h,prior),prob in incoming.items():
                    counts['contexts']+=1
                    if ended(i,h,prior):continue
                    mass['all_decisions']+=prob
                    if sides[i]==0:
                        mass['seat0_decisions']+=prob;unique['seat0']+=1
                        all_diag={pr:diagnostic(i,h,prior,*pr)for pr in profiles}
                        for pr,dg in all_diag.items():
                            t=tables[pr];t['bad_mass']+=prob*dg['error'];t['any_bad_mass']+=prob*dg['any_bad'];t['all_bad_mass']+=prob*dg['all_bad'];t['fork_mass']+=prob*dg['fork']
                            unique[f'D{pr[0]}_B{pr[1]}_bad_contexts']+=dg['any_bad']
                            step[f'D{pr[0]}_B{pr[1]}_bad_mass']+=prob*dg['error']
                        for depth in(1,2,3):
                            ds=[all_diag[depth,p]for p in(F(1,2),F(1),F(2))]
                            invariant=len({x['chosen']for x in ds})==1
                            error_invariant=len({x['error']for x in ds})==1
                            mass[f'D{depth}_price_set_sensitive_mass']+=prob*(not invariant)
                            mass[f'D{depth}_price_error_sensitive_mass']+=prob*(not error_invariant)
                            mass[f'D{depth}_unit_error_price_invariant_mass']+=prob*ds[1]['error']*error_invariant
                            if depth==2 and ds[1]['any_bad'] and sum(x['family']==family['family']and x['foe']==foe for x in examples)<4:
                                examples.append(dict(family=family['family'],foe=foe,vertex=i,h=h,prior_vertices=[k for k in range(prior.bit_length())if prior>>k&1],incoming_mass=str(prob),price_set_invariant=invariant,price_error_invariant=error_invariant,profiles=[dict(depth=depth,B=str(p),**{k:(str(v)if isinstance(v,F)else v)for k,v in all_diag[depth,p].items()})for p in(F(1,2),F(1),F(2))]))
                    pp=prior|1<<i;choices=edges[i];immediate=[j for j in choices if j in terms and terms[j]==sides[i]]
                    if sides[i]==1 and foe=='FLOOR'and immediate:choices=immediate[:1]
                    for j in choices:new[j,h-1,pp]+=prob/len(choices)
                steps.append({k:str(v)for k,v in step.items()});incoming=new
            oldlaws=[r for r in laws['rows']if r['family']==family['family']and r['opponent']==foe]
            if {r['id']for r in oldlaws}!={r[key]for r in pair['rows']}or mass['all_decisions']!=sum(F(r['expected_decisions'])for r in oldlaws)/len(oldlaws):raise ValueError('incoming law mismatch')
            row=dict(family=family['family'],masks=family['masks'],foe=foe,unique_counts=dict(unique),mass={k:str(v)for k,v in mass.items()},profiles=[dict(depth=d,B=str(p),**{k:str(v)for k,v in tables[d,p].items()},bad_per_seat0_decision=str(tables[d,p]['bad_mass']/mass['seat0_decisions']))for d,p in profiles],by_ply=steps)
            rows.append(row);print({k:v for k,v in row.items()if k not in('by_ply','profiles')},flush=True)
        counts.update(work);counts['nominal_cache_entries']+=nominal.cache_info().currsize
    result=dict(status='PASS',plan=plan,rows=rows,examples=examples,counts=dict(counts),seconds=time.perf_counter()-tick)
    (output/'result.json').write_text(json.dumps(result,indent=2));return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();analyze(args.directory,args.output)
