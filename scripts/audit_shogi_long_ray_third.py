"""New L/B/TB frontiers, never rerun completed small-mode populations."""
from dataclasses import asdict
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.shared_contact_prefix import Profile,SharedContactPrefix
from scripts.three_contact_prefix import third_counts
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/shogi_long_ray_third_20261005.json'
SOURCES=('scripts/audit_shogi_long_ray_third.py','docs/research/SHOGI_LONG_RAY_THIRD_PROTOCOL.md',
 'scripts/shared_contact_prefix.py','scripts/three_contact_prefix.py',
 'docs/research/data/shared_contact_prefix_shogi_20261005.json',
 'generic_chess/rules/compiler.py','generic_chess/rules/standard_shogi.py')
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('frozen ray third frontiers')
    start=monotonic();r=dict(complete=False,public_transitions=0,event_materializations=0,source_queries=0,rows=[],
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec total compile/count cap')
    write_record(OUT,r)
    try:
        c=compile_semantic_ruleset(build_standard_shogi_ruleset())
        profiles=(Profile('L','L'),Profile('B','B'),Profile('B','TB',True))
        kernel=SharedContactPrefix(c,profiles,checkpoint=check);r['preprocessing']=dict(kernel.stats)
        old=json.loads((ROOT/SOURCES[4]).read_text());old={x['profile']['current']:x for x in old['rows']}
        for profile,v in third_counts(kernel).items():
            if (v['direct'],v['second'])!=(old[profile.current]['direct'],old[profile.current]['second']):
                raise ValueError('old prefix disagreement')
            r['rows'].append(dict(profile=asdict(profile),**v));write_record(OUT,r)
        r['complete']=len(r['rows'])==3
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps(r))
