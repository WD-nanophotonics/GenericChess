"""Independent first-action/capture-entry obstructions; no shortest paths."""
from collections import Counter, defaultdict
from fractions import Fraction as F
from pathlib import Path
from time import monotonic
import hashlib, json, sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from scripts.horse_target_graph import hops
from scripts.research_record import record_value, write_record
OUT=ROOT/'docs/research/data/horse_zero_obstruction_20261006.json'
SOURCES=('scripts/audit_horse_zero_obstruction.py','docs/research/HORSE_ZERO_OBSTRUCTION_PROTOCOL.md',
 'scripts/horse_target_graph.py','scripts/research_record.py',
 'docs/research/data/horse_target_graph_20261006.json',
 'docs/research/data/diagnostic_moment_bounds_20261006.json')

def main():
    if OUT.exists():raise FileExistsError('zero obstruction arithmetic never rerun')
    started=monotonic();r=dict(complete=False,new_edge_terms=0,first_action_empty=[],corner_entry=[],
      public_transitions=0,source_queries=0,forward_nodes=0,
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def save():r['seconds']=monotonic()-started;write_record(OUT,r)
    save()
    try:
        previous=json.loads((ROOT/SOURCES[-2]).read_text());moments=json.loads((ROOT/SOURCES[-1]).read_text())
        for old in (previous,moments):
            if not old['complete'] or not old['source_hashes_unchanged']:raise ValueError('frozen qualified input required')
            for p,pin in old['source_sha256'].items():
                if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=pin:raise ValueError('old source drift')
        incoming=defaultdict(list);group_classes=Counter()
        for source in range(90):
            groups=defaultdict(set)
            for dest,leg in hops(source,9,10):
                r['new_edge_terms']+=1;incoming[dest].append((source,leg));groups[leg].add(dest)
            group_classes[len(groups)]+=1
            if len(groups)!=2:continue
            for target in groups:
                other=next(leg for leg in groups if leg!=target)
                blockers={other}|(groups[other] if len(groups[other])==1 else set())
                for blocker in sorted(blockers):
                    if any(leg not in (target,blocker) and dest!=blocker for dest,leg in hops(source,9,10)):
                        raise ValueError('claimed initial trap has a legal first action')
                    if target in (0,8,81,89):raise ValueError('zero categories not disjoint')
                    r['first_action_empty'].append(dict(source=source,target=target,blocker=blocker))
        for target in (0,8,81,89):
            edges=incoming[target];r['new_edge_terms']+=len(edges)
            legs={leg for source,leg in edges}
            if len(edges)!=2 or len(legs)!=1:raise ValueError('corner capture-entry theorem failed')
            r['corner_entry'].append(dict(target=target,blocker=next(iter(legs)),sources=88))
        zero=sum(row['sources'] for row in r['corner_entry'])+len(r['first_action_empty'])
        if len({(x['source'],x['target'],x['blocker']) for x in r['first_action_empty']})!=48 or zero!=400:
            raise ValueError('obstruction cardinality failed')
        r['leg_group_counts']=dict(sorted(group_classes.items()));r['known_zero_lower']=zero
        r['cumulative_terms']=previous['motifs']+r['new_edge_terms']
        if r['cumulative_terms']>5000 or monotonic()-started+previous['seconds']>=15:raise ValueError('original cumulative family cap')
        prefix=previous['full_analytic_prefix'];r['moments']=[]
        for old in moments['rows']:
            law=old['law'];m=(lambda t:F(1,2**t)) if law=='geometric_half' else (lambda t:F(2,(t+1)*(t+2)))
            lower=(prefix['direct']*m(1)+prefix['second']*m(2))/704880
            upper=lower+(704880-prefix['direct']-prefix['second']-zero)*m(3)/704880
            r['moments'].append(dict(law=law,horse_interval=(lower,upper),upper_reduction=F(zero,704880)*m(3)))
        r['saved_zero_consistent']=previous['saved_horse_unreachable']==zero
        r['complete']=r['saved_zero_consistent'];r['complement_reachability_proved']=False
        r['cumulative_seconds']=monotonic()-started+previous['seconds']
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin for p,pin in r['source_sha256'].items())
    save();print(json.dumps(record_value({k:v for k,v in r.items() if k not in ('source_sha256','first_action_empty')})))

if __name__=='__main__':main()
