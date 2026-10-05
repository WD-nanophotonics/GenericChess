"""Exact five-mode moments plus independent Horse direct bounds."""
import hashlib,json,sys
from fractions import Fraction as F
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.research_record import write_record,record_value
OUT=ROOT/'docs/research/data/diagnostic_moment_bounds_20261006.json'
SOURCES=('scripts/audit_diagnostic_moment_bounds.py','docs/research/DIAGNOSTIC_MOMENT_BOUNDS_PROTOCOL.md',
 'docs/research/data/diagnostic_contact_independent_20261005.json',
 'docs/research/data/cannon_distance_closed_form_20261006.json',
 'docs/research/data/soldier_distance_closed_form_20261006.json',
 'docs/research/data/diagnostic_sparse_graphs_20261006.json')

def moment(law,t):
    if type(t) is not int or t<1:raise ValueError('positive integer distance required')
    if law=='geometric_half':return F(1,2**t)
    if law=='linear_mixture':return F(2,(t+1)*(t+2))
    raise ValueError('frozen law required')

if __name__=='__main__':
    if OUT.exists():raise FileExistsError('closed arithmetic bound certificate')
    start=monotonic();r=dict(complete=False,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},
      distance_terms=0,comparisons=0,rows=[],source_queries=0,public_transitions=0,runtime_pushes=0,geometry_queries=0)
    try:
        records=[]
        for path in SOURCES[2:]:
            old=json.loads((ROOT/path).read_text());assert old['complete'] and old['source_hashes_unchanged']
            for source,pin in old['source_sha256'].items():assert hashlib.sha256((ROOT/source).read_bytes()).hexdigest()==pin
            records.append(old)
        rook,cannon,soldier,sparse=records
        full=dict(R=dict(histogram=rook['analytic']['rook_histogram'],unreachable=0,total=704880),
                  C=cannon['full_analytic'],S=soldier['full_analytic'],**sparse['full_aggregate'])
        direct_edges=4*(9-2)*(10-1)+4*(9-1)*(10-2);direct=direct_edges*87;total=704880
        assert direct_edges==508 and direct==44196
        r.update(horse_direct_edges=direct_edges,horse_direct_worlds=direct,total=total)
        for law in ('geometric_half','linear_mixture'):
            means={}
            for mode,raw in full.items():
                assert sum(raw['histogram'].values())+raw['unreachable']==total
                means[mode]=sum((n*moment(law,int(t)) for t,n in raw['histogram'].items()),F(0))/total
                r['distance_terms']+=len(raw['histogram']);assert r['distance_terms']<=100
            lower=F(direct,total)*moment(law,1)
            upper=lower+F(total-direct,total)*moment(law,2)
            max_checks={mode:means['R']>value for mode,value in means.items() if mode!='R'}
            max_checks['H_upper']=means['R']>upper
            r['comparisons']+=len(max_checks)+len(means)*2;assert r['comparisons']<=64
            r['rows'].append(dict(law=law,exact_means=means,horse_interval=(lower,upper),
                rook_strict_max_checks=max_checks,rook_normalization_qualified=all(max_checks.values()),
                normalized_exact={mode:v/means['R'] for mode,v in means.items()},
                normalized_horse_interval=(lower/means['R'],upper/means['R']),
                horse_above_exact={mode:lower>v for mode,v in means.items()},
                horse_below_exact={mode:upper<v for mode,v in means.items()},
                soldier_cannon_sign=1 if means['S']>means['C'] else -1 if means['S']<means['C'] else 0))
            assert monotonic()-start<15
        r['law_reversal']=r['rows'][0]['soldier_cannon_sign']==-1 and r['rows'][1]['soldier_cannon_sign']==1
        r['complete']=len(r['rows'])==2
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin for p,pin in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps({k:record_value(v) for k,v in r.items() if k not in ('source_sha256','rows')}))
    for row in r['rows']:print(json.dumps(record_value(row)))
