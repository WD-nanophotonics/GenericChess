"""Exact rational bounds on fixed-UNIFORM visits to candidate decisions.

The shadow chain omits repeat-draw stopping, retaining actual physical move
frontiers, mates, stalemates and the absolute H64 clock. Therefore its first
hit probability is an upper bound on actual repeat4 first-hit exposure.
Before absolute ply12 no repeated Position can occur four times: there is
no pass, capture restores nothing, and two opposing moves cannot undo each
other, so a Position cycle has at least four plies. Early first-hit mass is
an exact lower bound. Candidate visitation is not actual error or utility.
"""
from collections import Counter
from fractions import Fraction
from functools import reduce
from math import lcm
from pathlib import Path
import json,time,hashlib
from scripts.leaper_explorer_truth import digest
from scripts.leaper_microgames import role_stop_requested


def first_hit(edges,terminals,root,remaining,absolute_ply,targets,guard=lambda:None):
    # One denominator per layer avoids rounding and per-edge Fraction objects.
    base=reduce(lcm,(len(e)for e in edges if e),1);den=1;mass={root:1};hit=ended=0;early=Fraction(0);rows=[];counts=Counter()
    for step in range(remaining):
        guard();fresh={};current_hit=0;current_end=0
        for i,p in mass.items():
            if i in terminals:current_end+=p
            elif i in targets:current_hit+=p
            else:fresh[i]=p
        hit+=current_hit;ended+=current_end
        if hit+ended+sum(fresh.values())!=den:raise ValueError('exact mass conservation failed')
        now=Fraction(hit,den)
        if absolute_ply+step<12:early=now
        rows.append(dict(absolute_ply=absolute_ply+step,cumulative_shadow_first_hit=str(now),live_vertices=len(fresh)))
        nxt={}
        for i,p in fresh.items():
            out=edges[i]
            if not out:raise ValueError('ongoing empty frontier')
            w=p*(base//len(out));counts['arithmetic_edges']+=len(out)
            for j in out:nxt[j]=nxt.get(j,0)+w
        hit*=base;ended*=base;den*=base;mass=nxt
    if hit+ended+sum(mass.values())!=den:raise ValueError('final exact mass conservation failed')
    return dict(lower=str(early),upper=str(Fraction(hit,den)),denominator_base=base,by_ply=rows,counts=dict(counts))


def analyze(graph,output,*,seconds=600):
    output=Path(output);output.mkdir(exist_ok=False);tick=time.perf_counter();rows=[]
    plan=dict(question='How often can fixed Uniform play reach the few candidate search/learning decisions in the supplied two-A histories?',
        graph_digest=digest(graph),seconds_cap=seconds,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        estimand='BothseatsUniformoverALLactuallegalactions. Firstvisitofstaticrank3seat0(48),oranyforcedWINseat0(136). ThisincominglawisNOTactualmainlinelearneroccupation. EarlyactualfirsthitlowerboundandH64no-repeat-stopshadowupperbound,noterrorprobability,trainingstartsorutility.',
        histories='TwoexactPRIMARYmixed-colorfullrecordsatabsolute0/4, remaining64/60. NoPlayer, sampledrollout, training, newrule/layoutselection, frozen-caprefill or outcome-conditionedmu.')
    (output/'plan.json').write_text(json.dumps(plan,indent=2))
    def guard():
        if role_stop_requested():raise RuntimeError('USER_STOP')
        if time.perf_counter()-tick>=seconds:raise RuntimeError('TWOA_EXPOSURE_CAP_UNKNOWN_NO_REFILL')
    terms={int(i):v for i,v in graph['terminals'].items()}
    for name,targets in(('rank3',set(i for i,r in enumerate(graph['ranks'])if r==3 and graph['positions'][i][0]==0)),
                         ('any_force_WIN',set(i for i,v in enumerate(graph['values'])if v==1 and graph['positions'][i][0]==0))):
      for root in graph['roots']:
        guard();r=first_hit(graph['edges'],terms,root['root_index'],root['remaining'],64-root['remaining'],targets,guard)
        row=dict(event=name,targets=len(targets),source_record=root['record'],source_state_sha=root['state_sha'],**r);rows.append(row)
        print({k:v for k,v in row.items()if k not in('by_ply','source_record')},flush=True)
    result=dict(status='PASS',plan=plan,rows=rows,seconds=time.perf_counter()-tick)
    (output/'result.json').write_text(json.dumps(result,indent=2));return result
