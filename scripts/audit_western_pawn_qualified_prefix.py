"""One new aux-qualified compiled Pawn prefix; no semantic observations."""
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.qualified_western_pawn_prefix import QualifiedWesternPawnPrefix as WesternPawnContactPrefix
OUT=ROOT/'docs/research/data/western_pawn_qualified_prefix_20261005.json'
SOURCES=('scripts/audit_western_pawn_qualified_prefix.py','scripts/qualified_western_pawn_prefix.py','docs/research/CHESS_PAWN_ONE_STEP_RAY_SCOPE.md','docs/research/data/western_pawn_compiled_prefix_20261005.json','scripts/audit_western_pawn_compiled_prefix.py','scripts/western_pawn_contact_prefix.py',
 'docs/research/CHESS_PAWN_COMPILED_PREFIX_PROTOCOL.md','docs/research/CHESS_PAWN_AUX_REDUCTION_RESULTS.md',
 'scripts/shared_contact_prefix.py','generic_chess/rules/western_chess.py','generic_chess/rules/compiler.py')
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('frozen producer never rerun')
    start=monotonic();out=dict(complete=False,physical_events=0,goal_queries=0,
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start+0.031>=15:raise TimeoutError('15sec compiled prefix cap')
    try:
        c=compile_ruleset_for_execution(build_western_chess_ruleset());p=WesternPawnContactPrefix(c,checkpoint=check)
        out['stats']=p.stats;out['discarded_ep']=p.discarded_ep;out['reduced_double']=p.reduced_double
        out['rows']=[dict(profile=str(k),**v) for k,v in p.counts().items()]
        out['complete']=out['rows'][0]['direct']==6076 and out['rows'][0]['second']==16112
    except Exception as e:out['error']=f'{type(e).__name__}: {e}'
    out['seconds']=monotonic()-start
    out['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in out['source_sha256'].items())
    OUT.write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps({k:v for k,v in out.items() if k!='source_sha256'}))
