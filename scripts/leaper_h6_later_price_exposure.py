"""Zero-Player price-cell diagnostics on existing H6 paired policy occupation.

The only supported history policy is the supplied exact repeat2 H6 domain.
Uniform incoming policies are held fixed; oracle WDL only describes exposure.
Nominal minimax gradients are possible local leaf gradients, not actual Player
PV, eligibility traces, learning updates or measured strength improvement.
"""
from collections import Counter,defaultdict
from functools import lru_cache
from fractions import Fraction as F
from pathlib import Path
import argparse,json,time,gzip,hashlib
from scripts.leaper_explorer_truth import load,digest
from scripts.leaper_h6_initial_truth import admit
from scripts.leaper_cooperative_certificate import decode_position
from scripts.leaper_microgames import role_stop_requested
from generic_chess.learning.incremental import MATE


def analyze(directory,output,*,seconds=180,max_contexts=1000000):
    directory=Path(directory);output=Path(output)
    if output.exists():raise ValueError('fresh output required')
    output.mkdir(parents=True);tick=time.perf_counter()
    inputs=load(directory/'inputs.json.gz');truth=load(directory/'truth.json.gz');adj=load(directory/'adjacent-pairs.json.gz');laws=load(Path('docs/research/data/leaper_pair_transfer_20261024/policy-laws.json.gz'))
    plan=dict(input_digest=digest(inputs),truth_digest=digest(truth),adjacency_digest=digest(adj),laws_digest=digest(laws),
        question='Do later on-policy H6 forks intersect positive-price-sensitive action-quality and possible free-B leaf gradients?',
        budget=dict(seconds=seconds,max_contexts=max_contexts),prices=[.5,1,2],depths=[1,2],
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scope='Same paired128freshstarts, seat0UNIFORM and seat1UNIFORM/FLOOR. ALLavailablelaterfull-historycontexts withoutnewPlayer,training,policygames,rootselection ormissing-policy-slot refill. Fullvisitedset is exactonlyunderadmittedH6repeat2; nominalpricecells not actualtimedsearch/PV invariance.')
    (output/'plan.json').write_text(json.dumps(plan,indent=2));rows=[];counts=Counter();examples=[];candidates=defaultdict(F)
    truth_by={r['id']:r for r in truth['roots']}
    def guard():
        if role_stop_requested():raise RuntimeError('USER_STOP')
        if time.perf_counter()-tick>=seconds or counts['contexts']>max_contexts:raise RuntimeError('LATER_EXPOSURE_CAP_UNKNOWN')
    for pair in adj['pairs']:
      for tag,key in(('left_family','left_id'),('right_family','right_id')):
        family=next(f for f in inputs['families']if f['family']==pair[tag]);source=next(r for r in inputs['rows']if r['family']==family['family']);c=admit(family,source)
        d=load(directory/f"domain{family['family']}.json.gz")
        receipt=next(f for f in load(directory/'summary.json')['families']if f['family']==family['family'])
        if digest(d)!=receipt['domain_digest']:raise ValueError('retained complete domain digest differs')
        positions=[decode_position(p,c.initial_position)for p in d['positions']];edges=d['edges'];terms={int(i):w for i,w in d['terminals'].items()};sides=[p.side_to_move for p in positions]
        # Verify leaf-affine premise rather than assume generic material counts.
        features=[]
        for p in positions:
            A=sum(z is not None and(z.owner,z.current_type_id)==(0,'A')for z in p.board)
            B=sum(z is not None and(z.owner,z.current_type_id)==(1,'B')for z in p.board)
            if A not in(0,1)or B not in(0,1)or p.aux_state or any(h.counts for h in p.hands):raise ValueError('positive affine cell premise differs')
            if any(z and(z.current_type_id not in('K','A','B')or z.promoted or z.current_type_id!=z.base_type_id or(z.current_type_id=='A'and z.owner!=0)or(z.current_type_id=='B'and z.owner!=1))for z in p.board):raise ValueError('unsupported affine actor')
            features.append((A,-B))
        calls=0
        @lru_cache(None)
        def solve(i,h,prior):
            nonlocal calls
            calls+=1
            if calls%2048==0:guard()
            if i in terms:return 0 if terms[i]is None else 1 if terms[i]==0 else-1
            if h==0 or(prior>>i)&1:return 0
            pp=prior|(1<<i);vv=[solve(j,h-1,pp)for j in edges[i]]
            return (max if sides[i]==0 else min)(vv)
        def ended(i,h,prior):return i in terms or h==0 or(prior>>i)&1
        def leaf(i,h,prior,price):
            if ended(i,h,prior):return MATE*solve(i,h,prior),frozenset([0])
            A,B=features[i];return A+price*B,frozenset([B])
        @lru_cache(None)
        def nominal(i,h,prior,depth,price):
            if depth==0 or ended(i,h,prior):return leaf(i,h,prior,price)
            pp=prior|(1<<i);vv=[nominal(j,h-1,pp,depth-1,price)for j in edges[i]]
            best=(max if sides[i]==0 else min)(v for v,gg in vv)
            grads=frozenset(x for v,gg in vv if v==best for x in gg)
            return best,grads
        @lru_cache(None)
        def diagnostic(i,h,prior):
            pp=prior|(1<<i);exact=[solve(j,h-1,pp)for j in edges[i]];best=(max if sides[i]==0 else min)(exact);fork=len(set(exact))>1;result={}
            for depth in(1,2):
                sets=[];qualities=[];free=[];allfree=[];profile_rows=[]
                for price in(.5,1.,2.):
                    vv=[nominal(j,h-1,pp,depth-1,price)for j in edges[i]];score=(max if sides[i]==0 else min)(v for v,g in vv)
                    selected=tuple(k for k,(v,g)in enumerate(vv)if v==score)
                    error=F(sum(exact[k]!=best for k in selected),len(selected))
                    sets.append(selected);qualities.append(error)
                    grads=[gg for k in selected for gg in vv[k][1]];free.append(any(grads));allfree.append(all(gg!=0 for gg in grads))
                    profile_rows.append(dict(price=price,maximizers=list(selected),selected_WDL=[exact[k]for k in selected],uniform_tie_error=str(error),possible_free=free[-1]))
                result[depth]=dict(fork=fork,action_sensitive=len(set(sets))>1,quality_sensitive=len(set(qualities))>1,
                    possible_free_gradient=any(free),some_price_all_best_leaves_free=any(allfree),
                    useful_intersection=fork and len(set(qualities))>1 and any(free),
                    profiles=profile_rows)
            return result
        for opponent in('UNIFORM','FLOOR'):
            state_mass=defaultdict(F)
            for r in pair['rows']:state_mass[truth_by[r[key]]['root_index'],6,0,0]+=F(1,len(pair['rows']))
            mass=defaultdict(F);by_ply=[]
            for ply in range(6):
                guard();new=defaultdict(F);step=defaultdict(F)
                for(i,h,prior,seen_events),prob in state_mass.items():
                    counts['contexts']+=1
                    if ended(i,h,prior):continue
                    step['decisions']+=prob;mass['decisions']+=prob
                    dg=diagnostic(i,h,prior);next_seen=seen_events
                    if sides[i]==0:
                        mass['seat0_decisions']+=prob
                        for dep,data in dg.items():
                            bit=1<<(dep-1)
                            if data['useful_intersection']and not seen_events&bit:
                                mass[f'D{dep}_first_useful_probability']+=prob
                                step[f'D{dep}_first_useful_probability']+=prob
                                next_seen|=bit
                            if data['useful_intersection']:
                                candidates[family['family'],opponent,i,h,prior,dep]+=prob
                            for event in('fork','action_sensitive','quality_sensitive','possible_free_gradient','some_price_all_best_leaves_free','useful_intersection'):
                                if data[event]:mass[f'D{dep}_{event}']+=prob;step[f'D{dep}_{event}']+=prob
                            if data['useful_intersection']and sum(e['family']==family['family']for e in examples)<4:examples.append(dict(family=family['family'],opponent=opponent,vertex=i,h=h,prior_vertices=[k for k in range(len(positions))if(prior>>k)&1],depth=dep,probability=str(prob),diagnostic=data))
                    pp=prior|(1<<i);selected=list(edges[i])
                    immediate=[j for j in selected if j in terms and terms[j]==sides[i]]
                    if sides[i]==1 and opponent=='FLOOR'and immediate:selected=immediate[:1]
                    for j in selected:new[j,h-1,pp,next_seen]+=prob/len(selected)
                by_ply.append({k:str(v)for k,v in step.items()});state_mass=new
            # Compare identical frozen-law decision counts, not just own output.
            old=[r for r in laws['rows']if r['family']==family['family']and r['opponent']==opponent]
            if len(old)!=len(pair['rows'])or{r['id']for r in old}!={r[key]for r in pair['rows']}:raise ValueError('retained law root support differs')
            expected=sum(F(r['expected_decisions'])for r in old)/len(old)
            if mass['decisions']!=expected:raise ValueError('incoming policy law differs from retained exact law')
            rows.append(dict(family=family['family'],masks=family['masks'],opponent=opponent,roots=len(pair['rows']),expected_visits={k:str(v)for k,v in mass.items()},by_ply=by_ply))
            print({k:v for k,v in rows[-1].items()if k!='by_ply'},flush=True)
        counts['truth_calls']+=calls;counts['nominal_entries']+=nominal.cache_info().currsize
    candidate_rows=[dict(family=f,opponent=o,vertex=i,h=h,prior_vertices=[k for k in range(prior.bit_length())if(prior>>k)&1],depth=dep,probability=str(prob))for(f,o,i,h,prior,dep),prob in sorted(candidates.items())]
    result=dict(plan=plan,status='PASS',rows=rows,examples=examples,candidate_contexts=candidate_rows,counts=dict(counts),seconds=time.perf_counter()-tick)
    (output/'result.json').write_text(json.dumps(result,indent=2));return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();analyze(a.directory,a.output)
