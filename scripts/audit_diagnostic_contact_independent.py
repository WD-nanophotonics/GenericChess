"""Independent fixed-target numerical and whole-shape analytic qualification."""
from collections import Counter
from math import comb
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.diagnostic_contact_coordinate_oracle import distance
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/diagnostic_contact_independent_20261005.json'
SOURCES=('scripts/audit_diagnostic_contact_independent.py','scripts/diagnostic_contact_coordinate_oracle.py','docs/research/DIAGNOSTIC_CONTACT_INDEPENDENT_PROTOCOL.md','docs/research/data/diagnostic_native_contact_mirrored_20261005.json','generic_chess/rules/xiangqi_diagnostic.py')
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('fixed-target independent study never rerun')
    start=monotonic();r=dict(complete=False,rows=[],public_transitions=0,source_queries=0,enumerated=0,
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec entire independent study')
    try:
        saved=json.loads((ROOT/SOURCES[3]).read_text());assert saved['complete'];by={row['profile']['current']:row for row in saved['rows']}
        for mode in ('A','C','E','H','R','S'):
            digest=hashlib.sha256();hist=Counter();worlds=0
            for blocker in range(1,90):
                for source in range(1,90):
                    if source==blocker:continue
                    check();d=distance(mode,source,0,blocker);digest.update(f'{blocker},{source}:{d};'.encode());hist[d]+=1;worlds+=1
            row=dict(mode=mode,target=0,worlds=worlds,histogram={t:n for t,n in sorted(hist.items()) if t},unreachable=hist[0],ordered_coordinate_sha256=digest.hexdigest(),ordered_compiled_sha256=by[mode]['target0_ordered_sha256'])
            row['match']=row['ordered_coordinate_sha256']==row['ordered_compiled_sha256'];r['rows'].append(row);write_record(OUT,r)
            if worlds!=7832 or not row['match']:raise ValueError('prospective target0 digest mismatch')
        W,H=9,10;total=W*H*(W*H-1)*(W*H-2);direct=2*(H*comb(W,3)+W*comb(H,3));screenpairs=H*(W-2)*(W-1)+W*(H-2)*(H-1)
        r['analytic']=dict(cannon_reachable=screenpairs*(W*H-2),cannon_zero=total-screenpairs*(W*H-2),cannon_direct=direct,
            rook_histogram={1:W*H*(W+H-2)*(W*H-2)-direct,2:W*H*(W-1)*(H-1)*(W*H-2),3:direct},rook_zero=0)
        assert r['analytic']['cannon_zero']==by['C']['unreachable'] and direct==by['C']['histogram']['1']
        assert {str(t):n for t,n in r['analytic']['rook_histogram'].items()}==by['R']['histogram'] and by['R']['unreachable']==0
        r['complete']=len(r['rows'])==6
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k not in ('rows','source_sha256')}))
