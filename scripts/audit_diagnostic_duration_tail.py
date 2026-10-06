"""Exact sufficient duration conditions, with unqualified H tail left open."""
from fractions import Fraction as F
from pathlib import Path
from time import monotonic
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.research_record import write_record,record_value
OUT=ROOT/'docs/research/data/diagnostic_duration_tail_20261006.json'
SOURCES=('scripts/audit_diagnostic_duration_tail.py','docs/research/DIAGNOSTIC_DURATION_TAIL_PROTOCOL.md',
 'scripts/research_record.py','docs/research/data/diagnostic_duration_order_20261006.json')


def main():
    if OUT.exists():raise FileExistsError('closed tail algebra never rerun')
    start=monotonic();r=dict(complete=False,terms=0,source_queries=0,geometry_queries=0,public_transitions=0,
       source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    try:
        raw=json.loads((ROOT/SOURCES[-1]).read_text())
        if not raw['complete'] or not raw['source_hashes_unchanged']:raise ValueError('qualified cumulative input required')
        for p,pin in raw['source_sha256'].items():
            if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=pin:raise ValueError('input drift')
        c=raw['cumulative'];total=raw['total']
        hs={n:c['H'][str(n)][0]-c['S'][str(n)][1] for n in range(1,18)}
        ce={n:c['C'][str(n)][0]-c['E'][str(n)][1] for n in range(1,18)};r['terms']=len(hs)+len(ce)
        early=min(hs[n] for n in range(1,8));adverse=-min([hs[n] for n in range(8,18)]+[c['H']['infinity'][0]-c['S']['infinity'][1]])
        first=-ce[1];later=min([ce[n] for n in range(2,18)]+[c['C']['infinity'][0]-c['E']['infinity'][1]])
        if min(early,adverse,first,later)<=0:raise ValueError('gate sign premises failed')
        r['horse_soldier']=dict(early_minimum=early,tail_adverse=adverse,strict_m8_over_m1_below=F(early,early+adverse),not_necessary=True)
        r['cannon_elephant']=dict(first_adverse=first,later_minimum=later,strict_first_positive_duration_share_below=F(later,later+first),not_necessary=True)
        r['controls']={}
        for name,m in [('geometric_half',lambda t:F(1,2**t)),('linear_mixture',lambda t:F(2,(t+1)*(t+2)))]:
            p=m(1)-m(8);q=m(8);p1=m(1)-m(2);q2=m(2)
            r['controls'][name]=dict(m8_over_m1=q/m(1),first_positive_duration_share=p1/m(1),
              hs_lower=F(early*p-adverse*q,total),ce_lower=F(later*q2-first*p1,total))
        if r['terms']>64 or monotonic()-start>=15:raise ValueError('tail arithmetic cap')
        r['complete']=all(v['hs_lower']>0 and v['ce_lower']>0 for v in r['controls'].values())
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in r['source_sha256'].items());write_record(OUT,r)
    print(json.dumps(record_value({k:v for k,v in r.items() if k!='source_sha256'})))


if __name__=='__main__':main()
