from pathlib import Path
from fractions import Fraction as F
from time import monotonic
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.research_record import write_record,record_value
OUT=ROOT/'docs/research/data/search_endpoint_robustness_20261006.json'
OLD='docs/research/data/chess_q1_root_20261006.json'
SOURCES=('scripts/audit_search_endpoint_robustness.py','docs/research/SEARCH_ENDPOINT_ROBUSTNESS_PROTOCOL.md',OLD,'scripts/research_record.py')


def main():
    if OUT.exists():raise FileExistsError('one exposed algebra diagnostic')
    start=monotonic();r=dict(complete=False,terms=0,transitions=0,labels=0,rows={},
      leaves={'A':[(0,6,-7,0,0),(0,-6,7,0,0)],'B':[(0,0,0,1,-1)]},
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    try:
        old=json.loads((ROOT/OLD).read_text())
        if not old['complete'] or not old['source_hashes_unchanged']:raise ValueError('qualified coefficients required')
        for p,pin in old['source_sha256'].items():
            if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=pin:raise ValueError('original drift')
        endpoints=[tuple(old['policies'][m]['integer_weights'][t] for t in 'PNBRQ') for m in ('geometric_half','linear_mixture')]
        points=endpoints+[tuple(F(a+b,2) for a,b in zip(*endpoints))]
        for name,w in zip(('geometric_half','linear_mixture','midpoint'),points):
            leaf_scores={}
            for action,rows in r['leaves'].items():
                values=[]
                for f in rows:
                    v=F(0)
                    for a,b in zip(f,w):
                        if r['terms']>=64 or monotonic()-start>=15:raise ValueError('64terms/15sec cap')
                        r['terms']+=1;v+=a*b
                    values.append(v)
                leaf_scores[action]=values
            scores={a:min(vs) for a,vs in leaf_scores.items()};best=max(scores.values())
            r['rows'][name]=dict(weights=w,leaf_scores=leaf_scores,scores=scores,full_ties=sorted(a for a,v in scores.items() if v==best))
        if r['rows']['geometric_half']['full_ties']!=['B'] or r['rows']['linear_mixture']['full_ties']!=['B'] or r['rows']['midpoint']['full_ties']!=['A']:raise ValueError('counterexample failed')
        r['complete']=True
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin for p,pin in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps(record_value({k:v for k,v in r.items() if k!='source_sha256'})))


if __name__=='__main__':main()
