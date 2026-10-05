"""New complete non-Pawn closure, no event or goal observations."""
from collections import Counter
from dataclasses import asdict
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.shared_contact_prefix import Profile
from scripts.nonpromotable_contact_prefix import NonpromotableContactPrefix
from scripts.full_contact_distances import full_distance_slabs
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/chess_full_nonpawn_distance_20261005.json'
SOURCES=('scripts/audit_chess_full_nonpawn_distance.py','scripts/full_contact_distances.py',
 'docs/research/CHESS_FULL_NONPAWN_DISTANCE_PROTOCOL.md','scripts/nonpromotable_contact_prefix.py',
 'scripts/shared_contact_prefix.py','generic_chess/rules/western_chess.py')
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('frozen full nonpawn distance census')
    start=monotonic();r=dict(complete=False,public_transitions=0,source_queries=0,event_materializations=0,slabs=[],
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec total census cap')
    write_record(OUT,r)
    try:
        c=compile_semantic_ruleset(build_western_chess_ruleset());profiles=tuple(Profile(t,t) for t in ('Q','R','N','B'))
        kernel=NonpromotableContactPrefix(c,profiles,checkpoint=check);r['preprocessing']=dict(kernel.stats)
        for blocker,slab in full_distance_slabs(kernel):
            check();r['slabs'].append(dict(blocker=blocker,rows=[dict(profile=asdict(p),**row) for p,row in slab.items()]))
            write_record(OUT,r)
        r['rows']=[]
        for profile in profiles:
            hist=Counter();zeros=0
            for slab in r['slabs']:
                row=next(row for row in slab['rows'] if row['profile']==asdict(profile))
                hist.update({int(t):n for t,n in row['histogram'].items()});zeros+=row['unreachable']
            if sum(hist.values())+zeros!=249984:raise ValueError('world mass lost')
            r['rows'].append(dict(profile=asdict(profile),histogram=dict(sorted(hist.items())),unreachable=zeros,total=249984))
        r['complete']=len(r['slabs'])==64 and len(r['rows'])==4
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k not in ('slabs','source_sha256')}))
