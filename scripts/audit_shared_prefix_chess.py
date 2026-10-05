"""One-shot prospective Chess cross-game control; never rerun saved output."""
from dataclasses import asdict
import hashlib,json
from pathlib import Path
import sys
from time import monotonic
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.shared_contact_prefix import Profile,SharedContactPrefix
OUT=ROOT/'docs/research/data/shared_prefix_chess_20261005.json'
SOURCES=('scripts/audit_shared_prefix_chess.py','scripts/shared_contact_prefix.py',
 'docs/research/SHARED_PREFIX_CHESS_CONTROL_PROTOCOL.md','generic_chess/rules/compiler.py',
 'generic_chess/rules/ir.py','generic_chess/rules/western_chess.py')
EXPECTED=dict(N=(20832,66472),B=(33936,85824),R=(53760,194432),Q=(87696,162048))

if __name__=='__main__':
    if OUT.exists():raise FileExistsError('frozen output never rerun')
    start=monotonic()
    r=dict(complete=False,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},
           public_transitions=0,goal_queries=0,event_materializations=0,rows=[])
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec whole control cap')
    try:
        c=compile_semantic_ruleset(build_western_chess_ruleset());check()
        kernel=SharedContactPrefix(c,[Profile(t,t) for t in EXPECTED],checkpoint=check)
        r['preprocessing']=dict(kernel.stats);r['preprocessing_seconds']=monotonic()-start
        for p,row in kernel.counts().items():r['rows'].append(dict(profile=asdict(p),**row))
        r['matches_prior_arithmetic']=all((x['direct'],x['second'])==EXPECTED[x['profile']['current']] for x in r['rows'])
        r['complete']=len(r['rows'])==4 and r['matches_prior_arithmetic']
    except Exception as e:r['error']=f'{type(e).__name__}: {e}'
    r['seconds']=monotonic()-start
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items())
    OUT.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(r))
