"""Post-hoc scope of capacity/WDL on the already closed singleton domains.

The original common opening support excludes a bare King within Chebyshev
distance two of A: it must be safe under the UNION of all five offset groups.
This is stronger than a legal fresh opening for a particular rule. Labels
outside each saved complete component remain unlabelled.
"""
from collections import Counter
from pathlib import Path
import argparse,hashlib,json,time
from scripts.leaper_explorer_truth import load
from scripts.leaper_frozen_truth_packet import reconstruct
from scripts.leaper_parity_scope import orthogonally_independent
from scripts.leaper_design import offsets
from scripts.leaper_microgames import role_stop_requested


def summarize(g):
    n=g['n'];m=g['mask'];counts=Counter();rank=Counter();common=set();by={}
    for i,(side,b)in enumerate(g['positions']):
        if side or '2'not in b:continue
        a=b.index('2');k=b.index('1');v=b.index('3');dist=max(abs(a%n-v%n),abs(a//n-v//n))
        # These actor0 vertices came from legal source roots or actual moves:
        # both Kings are safe. No arbitrary illegal turn snapshot is added.
        category='union_safe'if dist>=3 else'particular_rule_only'
        value=g['graph_values'][i];rr=g['graph_ranks'][i]
        value64=value if value and rr<=64 else 0
        counts[category+'/vertices']+=1;counts[category+('/WIN64'if value64 else'/DRAW64')]+=1
        if value64:rank[category+'/max_force_rank']=max(rank[category+'/max_force_rank'],rr)
        if dist>=3:common.add((k,a,v));by[k,a,v]=value64
    # Full union-safe opening support, independent of a particular mask.
    expected=set()
    for k in range(n*n):
      for a in range(n*n):
       if a==k:continue
       for v in range(n*n):
        if v in(k,a):continue
        if max(abs(k%n-v%n),abs(k//n-v//n))<=1:continue
        if max(abs(a%n-v%n),abs(a//n-v//n))<3:continue
        expected.add((k,a,v))
    if not common<=expected:raise ValueError('saved union-safe scope differs')
    support=len(expected);known=sum(by.values());unknown=support-len(common)
    return dict(n=n,mask=m,static_capacity1=not orthogonally_independent(offsets(m)),counts=dict(counts),ranks=dict(rank),
        full_union_safe_support=support,covered_union_safe=len(common),unlabelled_union_safe=unknown,
        uniform_union_safe_WIN64_count_bounds=[known,known+unknown],
        source_roots=len(g['roots']),source_root_WIN64=sum(next(x for x in r['clocks']if x['H']==64)['WDL']for r in g['roots']))


def analyze(packet,output,*,seconds=600):
    output=Path(output);output.mkdir(parents=True,exist_ok=False);tick=time.perf_counter();raw=Path(packet).read_bytes();p=load(packet)
    plan=dict(question='Is the apparent static-capacity iff a property of the fixed cross-rule common support rather than arbitrary legal fresh roots?',
        source_packet_sha256=hashlib.sha256(raw).hexdigest(),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cap_seconds=seconds,
        method='Reconstructexisting75completeintegerclosures andchecktheirretainedfullCorefrontierdigests. Posthocallcoveredlegalactor0vertices; no newCore, rule/root selection, Player, graph expansion, trainingoroldallowancerefill.',
        limits='Closedcomponentsarefiniteexposedsupport,notnewblindtruth. Missingphysicalplacementsunlabelled. union-safe meansbothKingssafeundertheunionmask31,notonlytheparticularrule.')
    (output/'plan.json').write_text(json.dumps(plan,indent=2));rows=[]
    for entry in p['graphs']:
        if role_stop_requested():raise RuntimeError('USER_STOP')
        if time.perf_counter()-tick>=seconds:raise RuntimeError('CAPACITY_SCOPE_CAP_UNKNOWN')
        g=reconstruct(entry);row=summarize(g);rows.append(row);print(row,flush=True)
    result=dict(status='PASS',plan=plan,rows=rows,seconds=time.perf_counter()-tick)
    (output/'result.json').write_text(json.dumps(result,indent=2));return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--packet',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();analyze(a.packet,a.output)
