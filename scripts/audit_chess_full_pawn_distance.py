"""One complete new Pawn closure; target-aware, no replayed game events."""
from collections import Counter
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.shared_contact_prefix import Profile
from scripts.qualified_western_pawn_prefix import QualifiedWesternPawnPrefix
from scripts.target_aware_contact_distances import target_aware_slabs
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/chess_full_pawn_distance_20261005.json'
SOURCES=('scripts/audit_chess_full_pawn_distance.py','scripts/target_aware_contact_distances.py',
 'docs/research/CHESS_FULL_PAWN_DISTANCE_PROTOCOL.md','scripts/qualified_western_pawn_prefix.py',
 'scripts/western_pawn_contact_prefix.py','scripts/shared_contact_prefix.py',
 'docs/research/data/chess_pawn_third_prefix_20261005.json','generic_chess/rules/western_chess.py')
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('frozen target-aware full Pawn census')
    start=monotonic();r=dict(complete=False,public_transitions=0,source_queries=0,event_materializations=0,slabs=[],
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec total compile/census cap')
    write_record(OUT,r)
    try:
        c=compile_semantic_ruleset(build_western_chess_ruleset());kernel=QualifiedWesternPawnPrefix(c,checkpoint=check)
        r['preprocessing']=dict(kernel.stats)
        for blocker,slab in target_aware_slabs(kernel,Profile('P','P')):
            check();r['slabs'].append(dict(blocker=blocker,**slab));write_record(OUT,r)
        hist=Counter();zeros=0
        for slab in r['slabs']:hist.update({int(t):n for t,n in slab['histogram'].items()});zeros+=slab['unreachable']
        r['histogram']=dict(sorted(hist.items()));r['unreachable']=zeros;r['total']=249984
        old=json.loads((ROOT/SOURCES[6]).read_text())
        if [hist[i] for i in (1,2,3)]!=[old[k] for k in ('direct','second','third')]:raise ValueError('old prefix mismatch')
        if zeros!=old['permanent_zero'] or sum(hist.values())+zeros!=249984:raise ValueError('support mass mismatch')
        r['complete']=len(r['slabs'])==64
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k not in ('slabs','source_sha256')}))
