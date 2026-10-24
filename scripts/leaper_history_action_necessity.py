"""Does truth-history sensitivity require history-dependent optimal action?"""
from collections import Counter,defaultdict,deque
from fractions import Fraction as F
from itertools import combinations
from pathlib import Path
import hashlib,json,time
from scripts.leaper_explorer_truth import load,digest
from scripts.leaper_history_edit_context import SOURCE
from scripts.leaper_h6_initial_truth import admit
from scripts.leaper_h6_headroom import evaluate
from scripts.leaper_cooperative_certificate import decode_position
from scripts.leaper_microgames import role_stop_requested


def run(output,seconds=600,*,with_covers=False):
    tick=time.perf_counter();inputs=load(SOURCE/'inputs.json.gz');truth=load(SOURCE/'truth.json.gz');roots={r['id']:r for r in truth['roots']};adj=load(SOURCE/'adjacent-pairs.json.gz');pair=adj['pairs'][0]
    oldlaws=load(Path('docs/research/data/leaper_pair_transfer_20261024/policy-laws.json.gz'));results=[];work=Counter()
    def guard():
        if role_stop_requested():raise RuntimeError('USER_STOP')
        if time.perf_counter()-tick>seconds:raise RuntimeError('HISTORY_ACTION_CAP_UNKNOWN_NO_REFILL')
    for tag,key,record in(('left_family','left_id','left_record'),('right_family','right_id','right_record')):
        f=next(f for f in inputs['families']if f['family']==pair[tag]);src=next(r for r in inputs['rows']if r['family']==f['family']);c=admit(f,src);d=load(SOURCE/f"domain{f['family']}.json.gz");pos=[decode_position(p,c.initial_position)for p in d['positions']];sides=[p.side_to_move for p in pos];ts={int(i):v for i,v in d['terminals'].items()};end,solve,*_=evaluate(d['edges'],ts,sides,[(0,0)]*len(pos),guard)
        init=[roots[r[key]]['root_index']for r in pair['rows']];todo=deque();rep={};groups=defaultdict(dict);stats=Counter()
        for origin,i in enumerate(init):
            kk=i,6,0
            if kk not in rep:rep[kk]=(origin,());todo.append(kk)
        decisions={}
        while todo:
            if stats['contexts']%1024==0:guard()
            i,h,prior=todo.popleft();stats['contexts']+=1
            if end(i,h,prior):continue
            vv=tuple(solve(j,h-1,prior|1<<i)for j in d['edges'][i]);v=solve(i,h,prior);best=frozenset(k for k,x in enumerate(vv)if x==v);decisions[i,h,prior]=(v,vv,best)
            groups[i,h].setdefault(best,(i,h,prior));stats['ongoing']+=1;origin,path=rep[i,h,prior]
            for offset,j in enumerate(d['edges'][i]):
                kk=(j,h-1,prior|1<<i)
                if kk not in rep:rep[kk]=(origin,(*path,offset));todo.append(kk)
        witnesses=[];hist=Counter();lookup={};covers=[];cover_counts=Counter()
        for(i,h),bb in groups.items():
            shared=set.intersection(*(set(x)for x in bb));hist['Position_clock_groups']+=1;hist['distinct_optimal_set_groups']+=len(bb)>1;hist['no_shared_optimal_action_groups']+=not shared
            if with_covers:
                actions=range(len(d['edges'][i]));cover=None
                for size in range(1,len(d['edges'][i])+1):
                    cover=next((ss for ss in combinations(actions,size)if all(set(ss)&best for best in bb)),None)
                    if cover is not None:break
                if cover is None:raise ValueError('nonempty optimal sets have no action cover')
                cover_counts[str((6-h,len(cover),(len(cover)-1).bit_length()))]+=1
                if len(cover)>1:covers.append(dict(vertex=i,remaining=h,minimum_actions=len(cover),oracle_tag_bits=(len(cover)-1).bit_length(),cover_offsets=cover,optimal_sets=[sorted(b)for b in bb]))
            if shared:lookup[i,h]=min(shared)
            elif len(witnesses)<3:
                minimal=list(bb)
                for candidate in list(minimal):
                    rest=[x for x in minimal if x!=candidate]
                    if rest and not set.intersection(*(set(x)for x in rest)):minimal=rest
                ww=[]
                for best in minimal:
                    context=bb[best];origin,path=rep[context];v,vv,_=decisions[context]
                    ww.append(dict(vertex=i,remaining=h,prior=hex(context[2]),origin=origin,source_record=pair['rows'][origin][record],path_offsets=path,value=v,child_values=vv,optimal_offsets=sorted(best)))
                witnesses.append(dict(vertex=i,remaining=h,actions=d['actions'][i],rows=ww,inclusion_minimal=True))
        laws=[]
        for foe in('UNIFORM','FLOOR'):
            incoming=defaultdict(F)
            for i in init:incoming[i,6,0]+=F(1,len(init))
            costs=defaultdict(lambda:defaultdict(F));mass=defaultdict(F);expected=F(0);seatmass=Counter()
            for ply in range(6):
                nxt=defaultdict(F)
                for(i,h,prior),prob in incoming.items():
                    if end(i,h,prior):continue
                    v,vv,best=decisions[i,h,prior];mass[i,h]+=prob;expected+=prob;seatmass[sides[i]]+=prob
                    for k in range(len(vv)):costs[i,h][k]+=prob*(k not in best)
                    choices=list(range(len(vv)))
                    if foe=='FLOOR' and sides[i]==1:
                        wins=[k for k,j in enumerate(d['edges'][i])if j in ts and ts[j]==1]
                        if wins:choices=wins[:1]
                    for offset in choices:
                        j=d['edges'][i][offset];nxt[j,h-1,prior|1<<i]+=prob/len(choices)
                incoming=nxt
            old=[r for r in oldlaws['rows']if r['family']==f['family']and r['opponent']==foe]
            if expected!=sum((F(r['expected_decisions'])for r in old),F(0))/len(old):raise ValueError('fixed incoming law drift')
            loss_by_seat={s:sum((min(cs.values())for(i,h),cs in costs.items()if sides[i]==s),F(0))for s in(0,1)}
            positive=[dict(vertex=i,remaining=h,mass=str(mass[i,h]),minimum_error_mass=str(min(cs.values())),cost_by_action={str(k):str(v)for k,v in cs.items()})for(i,h),cs in costs.items()if min(cs.values())>0]
            laws.append(dict(opponent=foe,expected_decisions=str(expected),seat_decision_mass={str(s):str(seatmass[s])for s in(0,1)},
                unavoidable_one_decision_errors={str(s):str(loss_by_seat[s])for s in(0,1)},minimum_error_per_decision={str(s):str(loss_by_seat[s]/seatmass[s])for s in(0,1)},positive_groups=positive))
        row=dict(family=f['family'],masks=f['masks'],fingerprint=f['fingerprint'],stats=dict(stats),groups=dict(hist),witnesses=witnesses,laws=laws,
            lookup_if_feasible=[dict(vertex=i,remaining=h,action_offset=k)for(i,h),k in sorted(lookup.items())])
        if with_covers:row.update(action_cover_counts=dict(cover_counts),nontrivial_action_covers=covers)
        results.append(row);print({k:v for k,v in row.items()if k not in('lookup_if_feasible','witnesses','laws')},flush=True)
    result=dict(verified=True,rows=results,seconds=time.perf_counter()-tick,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scope='All original pair histories. Fixed incoming mu is Uniform starts and legal Uniform/FLOOR occupancy, an exogenous ONE-decision diagnostic, not endogenous deployment return. Oracle lookup feasibility/lower bound is not learned policy, empirical strength, cheap computability or a new training gate.')
    Path(output).write_text(json.dumps(result,indent=2));print({k:v for k,v in result.items()if k!='rows'});return result

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.output)
