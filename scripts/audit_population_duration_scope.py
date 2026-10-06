"""World-population counterexample and conservative TV robustness, once."""
from fractions import Fraction as F
from pathlib import Path
from time import monotonic
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.diagnostic_contact_coordinate_oracle import distance
from scripts.research_record import write_record,record_value
OUT=ROOT/'docs/research/data/population_duration_scope_20261006.json'
SOURCES=('scripts/audit_population_duration_scope.py','docs/research/POPULATION_DURATION_SCOPE_PROTOCOL.md',
 'scripts/diagnostic_contact_coordinate_oracle.py','scripts/research_record.py',
 'docs/research/data/diagnostic_duration_order_20261006.json',
 'docs/research/data/diagnostic_moment_bounds_20261006.json',
 'docs/research/data/horse_zero_obstruction_20261006.json',
 'generic_chess/rules/xiangqi_diagnostic.py')


def main():
    if OUT.exists():raise FileExistsError('scope counterexample never rerun')
    start=monotonic();r=dict(complete=False,world_queries=0,arithmetic_terms=0,geometry_queries=0,
      public_transitions=0,source_queries=0,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    try:
        inputs=[]
        for path in SOURCES[4:7]:
            old=json.loads((ROOT/path).read_text())
            if not old['complete'] or not old['source_hashes_unchanged']:raise ValueError('qualified input required')
            for p,pin in old['source_sha256'].items():
                if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=pin:raise ValueError('input drift')
            inputs.append(old)
        order,moments,horse=inputs;dists={}
        for mode in ('A','R'):
            if r['world_queries']>=2 or monotonic()-start>=15:raise ValueError('two-world/15sec cap')
            dists[mode]=distance(mode,13,23,0);r['world_queries']+=1
        if dists!={'A':1,'R':2}:raise ValueError('predeclared coordinate counterexample failed')
        total=order['total'];r['counterexample']=dict(source=13,target=23,blocker=0,distances=dists,
          point_population_duration1=dict(A=1,R=0),uniform_dependent_duration=dict(A=F(1,total),R=F(0)),
          compiled_per_world_reproduced=False,official_goal_claim=False)
        c=order['cumulative'];r['universal_tv_gates']={}
        for mode,table in c.items():
            if mode=='R':continue
            gaps=[c['R'][h][0]-interval[1] for h,interval in table.items()];r['arithmetic_terms']+=len(gaps)
            gap=min(gaps)
            if gap<=0:raise ValueError('positive uniform gap required')
            r['universal_tv_gates'][mode]=dict(minimum_count_gap=gap,strict_epsilon_below=F(gap,2*total),not_necessary=True)
        r['endpoint_horse_tv_gates']={}
        for row,z in zip(moments['rows'],horse['moments']):
            if row['law']!=z['law']:raise ValueError('law alignment')
            m1=F(1,2) if row['law']=='geometric_half' else F(1,3)
            gap=F(row['exact_means']['R'])-F(z['horse_interval'][1]);r['arithmetic_terms']+=1
            r['endpoint_horse_tv_gates'][row['law']]=dict(raw_gap_lower=gap,strict_epsilon_below=gap/(2*m1),not_necessary=True)
        if r['arithmetic_terms']>128 or monotonic()-start>=15:raise ValueError('scope arithmetic cap')
        r['complete']=True
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in r['source_sha256'].items());write_record(OUT,r)
    print(json.dumps(record_value({k:v for k,v in r.items() if k!='source_sha256'})))


if __name__=='__main__':main()
