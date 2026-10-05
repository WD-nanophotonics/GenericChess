"""One-shot S/N/G prefix; no completed-output rerun."""
from dataclasses import asdict
import hashlib,json
from pathlib import Path
import sys
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.shared_contact_prefix import Profile,SharedContactPrefix
from scripts.three_contact_prefix import third_counts
OUT=ROOT/'docs/research/data/shogi_small_three_prefix_20261005.json'
SOURCES=('scripts/audit_shogi_small_three_prefix.py','scripts/three_contact_prefix.py',
 'scripts/shared_contact_prefix.py','docs/research/SHOGI_SMALL_THREE_PREFIX_PROTOCOL.md',
 'generic_chess/rules/compiler.py','generic_chess/rules/ir.py','generic_chess/rules/standard_shogi.py')

if __name__=='__main__':
    if OUT.exists():raise FileExistsError('preserve frozen output')
    start=monotonic();r=dict(complete=False,rows=[],event_materializations=0,public_transitions=0,goal_queries=0,
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec compile and arithmetic cap')
    try:
        c=compile_semantic_ruleset(build_standard_shogi_ruleset())
        k=SharedContactPrefix(c,[Profile(t,t) for t in ('S','N','G')],checkpoint=check)
        r['preprocessing']=dict(k.stats);r['preprocessing_seconds']=monotonic()-start
        r['rows']=[dict(profile=asdict(p),**v) for p,v in third_counts(k).items()]
        r['complete']=len(r['rows'])==3
    except Exception as e:r['error']=f'{type(e).__name__}: {e}'
    r['seconds']=monotonic()-start
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items())
    OUT.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(r))
