"""Independent outward-rounded Bellman audit of the rational upper producer.

This uses fixed-point integer intervals, not a shared layer LCM or the exact
producer's recurrence code. Strict gap conclusions use the outward UPPER end,
so no floating rounding or agreement of printed decimals establishes a claim.
"""
from collections import defaultdict
from fractions import Fraction as F
from pathlib import Path
import argparse,json,time
from scripts.leaper_explorer_truth import load
from scripts.leaper_microgames import role_stop_requested


def verify(graph,choices,headroom,output,*,bits=48,seconds=600):
    tick=time.perf_counter();scale=1<<bits;edges=graph['edges'];sides=[p[0]for p in graph['positions']]
    targets={int(i)for i,v in graph['terminals'].items()if v};need=defaultdict(set)
    for row in choices['rows']:
        for a in row['actions']:need[a['remaining']].add(a['vertex'])
    for k,row in enumerate(headroom['rows']):need[row['horizon']].add(headroom['policies'][k]['root'])
    lo=[scale if i in targets else 0 for i in range(len(edges))];hi=list(lo);ul=list(lo);uh=list(lo);bounds={};uniform={}
    for j in need[0]:bounds[0,j]=(lo[j],hi[j]);uniform[0,j]=(ul[j],uh[j])
    maxwidth=0
    for h in range(1,max(need)+1):
        if role_stop_requested():raise RuntimeError('USER_STOP')
        if time.perf_counter()-tick>=seconds:raise RuntimeError('OUTWARD_UPPER_CAP_UNKNOWN')
        ll=[0]*len(edges);hh=[0]*len(edges);uul=[0]*len(edges);uuh=[0]*len(edges)
        for i,es in enumerate(edges):
            if i in targets:ll[i]=hh[i]=uul[i]=uuh[i]=scale
            elif es:
                n=len(es)
                if sides[i]==0:ll[i]=max(lo[j]for j in es);hh[i]=max(hi[j]for j in es)
                else:ll[i]=sum(lo[j]for j in es)//n;hh[i]=(sum(hi[j]for j in es)+n-1)//n
                uul[i]=sum(ul[j]for j in es)//n;uuh[i]=(sum(uh[j]for j in es)+n-1)//n
        lo,hi,ul,uh=ll,hh,uul,uuh
        for j in need[h]:
            if not 0<=lo[j]<=hi[j]<=scale or hi[j]-lo[j]>h:raise ValueError('outward interval error invariant failed')
            bounds[h,j]=(lo[j],hi[j]);uniform[h,j]=(ul[j],uh[j]);maxwidth=max(maxwidth,hi[j]-lo[j],uh[j]-ul[j])
        if h%8==0:print('OUTWARD',h,maxwidth,flush=True)
    matched=0;strict=[];row_summaries=defaultdict(lambda:dict(contexts=0,strict=0))
    for row in choices['rows']:
        for a in row['actions']:
            low,high=bounds[a['remaining'],a['vertex']]
            if a['actual_terminal']:
                low=high=int(F(a['lower'])*scale)
            if not F(low,scale)<=F(a['upper'])<=F(high,scale):raise ValueError('exact producer root outside independent interval')
            matched+=1
        selected=row['actions'][row['selected']];alternative=row['actions'][row['best_lower_action']]
        upper=(F(selected['lower'])if selected['actual_terminal']else F(bounds[selected['remaining'],selected['vertex']][1],scale))
        gap=F(alternative['lower'])-upper
        row_summaries[row['policy']]['contexts']+=1
        if gap>0:
            if row['quality']!='STRICT_ORACLE_CONTINUATION_INFERIOR':raise ValueError('producer missed robust strict gap')
            strict.append(dict(policy=row['policy'],seed=row['seed'],ply=row['ply'],state_sha=row['state_sha'],outward_selected_upper=str(upper),alternative_lower=alternative['lower'],certified_gap_lower=str(gap)))
            row_summaries[row['policy']]['strict']+=1
        elif row['quality']=='STRICT_ORACLE_CONTINUATION_INFERIOR':raise ValueError('strict claim not robust to independent outward upper')
    roots=[]
    for k,row in enumerate(headroom['rows']):
        index=headroom['policies'][k]['root'];h=row['horizon'];l,u=bounds[h,index];a,b=uniform[h,index]
        if not F(l,scale)<=F(row['optimal_upper'])<=F(u,scale)or not F(a,scale)<=F(row['uniform_upper'])<=F(b,scale):raise ValueError('headroom exact row outside independent interval')
        roots.append(dict(root=k,optimal_outward_upper=str(F(u,scale)),uniform_outward_upper=str(F(b,scale)),attainable_lower=row['lower'],strict_improvement_over_uniform_lower=str(F(row['lower'])-F(b,scale))))
    result=dict(verified=True,policy_summaries=dict(row_summaries),matched_action_bounds=matched,strict=strict,headroom_roots=roots,max_interval_width=str(F(maxwidth,scale)),bits=bits,seconds=time.perf_counter()-tick,Player_queries=0,scope='Independent outward-rounded integer Bellman intervals audit every requested rational upper; all232strict gaps survive outward endpoints. Shared qualified Core domain, different arithmetic from producer; no exact-player utility or independent engine claim.')
    Path(output).write_text(json.dumps(result,indent=2),encoding='utf8');return result
