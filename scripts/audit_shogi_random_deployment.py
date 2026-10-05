"""One-shot named coarse deployment law, not official drops or game value."""
from collections import Counter
from fractions import Fraction as F
import hashlib,json
from pathlib import Path
import sys
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.shared_contact_prefix import Profile,SharedContactPrefix
from scripts.shogi_native_promotion_routes import promotion_prefix
from scripts.shogi_pawn_promotion_support import classify_pawn_world
from scripts.shogi_complete_board_intervals import moment,BOUND
OUT=ROOT/'docs/research/data/shogi_random_deployment_20261005.json'
SOURCES=('scripts/audit_shogi_random_deployment.py','scripts/shared_contact_prefix.py',
 'scripts/shogi_native_promotion_routes.py','scripts/shogi_pawn_promotion_support.py',
 'scripts/shogi_complete_board_intervals.py','docs/research/SHOGI_RANDOM_DEPLOYMENT_PROTOCOL.md',
 'generic_chess/rules/compiler.py','generic_chess/rules/standard_shogi.py')
TYPES=('P','L','N','S','G','B','R')

if __name__=='__main__':
    if OUT.exists():raise FileExistsError('frozen output never rerun')
    start=monotonic();r=dict(complete=False,rows=[],empty_drop_worlds=0,
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},
      event_materializations=0,public_transitions=0,goal_queries=0,
      excluded_constraints=['own_anchor_safe','Pawn drop mate/postconditions','official stock/history/opponent turns'])
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec total compile/count cap')
    try:
        c=compile_semantic_ruleset(build_standard_shogi_ruleset())
        k=SharedContactPrefix(c,[Profile(t,t) for t in TYPES],checkpoint=check)
        r['preprocessing']=dict(k.stats)
        for t in TYPES:
            p=Profile(t,t);mask=c.support.drop_allowed[t][0]
            size=sum(mask);expected=72 if t in ('P','L') else 63 if t=='N' else 81
            if size!=expected:raise ValueError('drop-mask drift')
            bad={(q,b):promotion_prefix(t,q,b) is None for q in range(81) for b in range(81) if q!=b} if t in ('S','N','B') else {}
            pairs={(q,d):k.pair_success(p,q,d) for q in range(81) for d in range(81) if q!=d}
            buckets={name:Counter() for name in ('direct','second','zero','tail')};sizes=Counter()
            for d in range(81):
                check()
                for b in range(81):
                    if d==b:continue
                    cases=((False,6),(True,1)) if t=='P' else ((False,7),)
                    for nifu,native_weight in cases:
                        eligible=[q for q in range(81) if mask[q] and q not in (d,b) and (not nifu or q%9!=b%9)]
                        n=len(eligible);sizes[n]+=native_weight
                        if not n:r['empty_drop_worlds']+=native_weight;continue
                        for q in eligible:
                            first,second=pairs[q,d]
                            if first&(1<<b):name='direct'
                            elif second&(1<<b):name='second'
                            elif (classify_pawn_world(q,d,b,0)[0]=='zero' if t in ('P','L') else bad.get((q,b),False)):name='zero'
                            else:name='tail'
                            buckets[name][n]+=native_weight
            masses={name:sum((F(count,n) for n,count in bucket.items()),F(0))/(81*80*7) for name,bucket in buckets.items()}
            if sum(masses.values())!=1:raise ValueError('world mass lost')
            bounds={}
            for law in ('geometric_half','linear_mixture'):
                exact=masses['direct']*moment(law,2)+masses['second']*moment(law,3)
                bounds[law]=[str(exact+masses['tail']*moment(law,BOUND[t]+1)),str(exact+masses['tail']*moment(law,4))]
            r['rows'].append(dict(type=t,mask_size=size,drop_set_sizes=dict(sizes),
                masses={name:str(v) for name,v in masses.items()},bounds=bounds))
        r['complete']=len(r['rows'])==7
    except Exception as e:r['error']=f'{type(e).__name__}: {e}'
    r['seconds']=monotonic()-start
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items())
    OUT.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(r))
