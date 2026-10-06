"""Universal duration CDF certificates with partial Horse mass, no graph work."""
from pathlib import Path
from time import monotonic
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/diagnostic_duration_order_20261006.json'
SOURCES=('scripts/audit_diagnostic_duration_order.py','docs/research/DIAGNOSTIC_DURATION_ORDER_PROTOCOL.md',
 'scripts/research_record.py','docs/research/data/diagnostic_contact_independent_20261005.json',
 'docs/research/data/cannon_distance_closed_form_20261006.json',
 'docs/research/data/soldier_distance_closed_form_20261006.json',
 'docs/research/data/diagnostic_sparse_graphs_20261006.json',
 'docs/research/data/horse_target_graph_20261006.json',
 'docs/research/data/horse_zero_obstruction_20261006.json')


def main():
    if OUT.exists():raise FileExistsError('closed duration algebra never rerun')
    start=monotonic();r=dict(complete=False,histogram_terms=0,comparisons=0,total=704880,
      cumulative={},pairs={},source_queries=0,public_transitions=0,geometry_queries=0,
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    try:
        inputs=[]
        for path in SOURCES[3:]:
            old=json.loads((ROOT/path).read_text())
            if not old['complete'] or not old['source_hashes_unchanged']:raise ValueError('qualified inputs required')
            for p,pin in old['source_sha256'].items():
                if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=pin:raise ValueError('input drift')
            inputs.append(old)
        rook,cannon,soldier,sparse,horse,zero=inputs
        exact={'R':dict(histogram=rook['analytic']['rook_histogram'],unreachable=0,total=704880),
          'C':cannon['full_analytic'],'S':soldier['full_analytic'],**sparse['full_aggregate']}
        for mode,row in exact.items():
            if sum(row['histogram'].values())+row['unreachable']!=r['total']:raise ValueError('whole denominator mismatch')
            r['histogram_terms']+=len(row['histogram'])
            r['cumulative'][mode]={str(n):[sum(count for t,count in row['histogram'].items() if int(t)<=n)]*2 for n in range(1,18)}
            r['cumulative'][mode]['infinity']=[r['total']-row['unreachable']]*2
        direct=horse['full_analytic_prefix']['direct'];second=horse['full_analytic_prefix']['second'];known=zero['known_zero_lower']
        r['cumulative']['H']={'1':[direct,direct],'2':[direct+second]*2,
          **{str(n):[direct+second,r['total']-known] for n in range(3,18)},
          'infinity':[direct+second,r['total']-known]}
        modes=sorted(r['cumulative'])
        for i,a in enumerate(modes):
            for b in modes[i+1:]:
                forward=[];reverse=[];actual_a_below=[];actual_a_above=[]
                for horizon in r['cumulative'][a]:
                    ca=r['cumulative'][a][horizon];cb=r['cumulative'][b][horizon]
                    forward.append(ca[0]-cb[1]);reverse.append(cb[0]-ca[1]);r['comparisons']+=1
                    if ca[1]<cb[0]:actual_a_below.append(horizon)
                    if cb[1]<ca[0]:actual_a_above.append(horizon)
                    if r['comparisons']>512 or r['histogram_terms']>100 or monotonic()-start>=15:raise ValueError('finite algebra cap')
                r['pairs'][a+'/'+b]=dict(forward_proved=min(forward)>=0,reverse_proved=min(reverse)>=0,
                  forward_min_gap=min(forward),reverse_min_gap=min(reverse),
                  definitely_a_below=actual_a_below,definitely_a_above=actual_a_above)
        r['rook_all_duration_normalizer']=all(min(r['cumulative']['R'][n][0]-table[n][1] for n in table)>0 for mode,table in r['cumulative'].items() if mode!='R')
        r['complete']=True
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in r['source_sha256'].items());write_record(OUT,r)
    print(json.dumps({k:v for k,v in r.items() if k not in ('source_sha256','cumulative')}))


if __name__=='__main__':main()
