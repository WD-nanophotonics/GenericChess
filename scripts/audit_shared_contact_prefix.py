"""One-shot Shogi prefix and actual total cost; no engine/goal experiment."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
from time import monotonic
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.shared_contact_prefix import Profile,SharedContactPrefix

OUT=ROOT/'docs/research/data/shared_contact_prefix_shogi_20261005.json'
SOURCES=('scripts/audit_shared_contact_prefix.py','scripts/shared_contact_prefix.py',
         'docs/research/SHARED_GEOMETRY_CONTACT_PREFIX_DESIGN.md',
         'generic_chess/rules/compiler.py','generic_chess/rules/ir.py',
         'generic_chess/rules/standard_shogi.py')

if __name__=='__main__':
    if OUT.exists():raise FileExistsError('frozen prefix producer never rerun')
    start=monotonic()
    report=dict(complete=False,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},
                public_transitions=0,goal_queries=0,event_materializations=0,owner=0,rows=[])
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec total preprocessing/count cap')
    try:
        c=compile_semantic_ruleset(build_standard_shogi_ruleset());check()
        native=[Profile(t,t) for t in ('P','L','N','S','G','B','R')]
        promoted=[Profile(b,t,True) for b,t in (('P','TP'),('L','TL'),('N','TN'),('S','TS'),('B','TB'),('R','TR'))]
        kernel=SharedContactPrefix(c,native+promoted,checkpoint=check)
        report['preprocessing']=dict(kernel.stats)
        report['preprocessing_seconds']=monotonic()-start
        for p,row in kernel.counts().items():
            report['rows'].append(dict(profile=asdict(p),**row))
        report['complete']=len(report['rows'])==13
    except Exception as e:
        report['error']=f'{type(e).__name__}: {e}'
    report['seconds']=monotonic()-start
    report['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in report['source_sha256'].items())
    OUT.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(report))
