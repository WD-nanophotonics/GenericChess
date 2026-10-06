from pathlib import Path
from time import monotonic
from dataclasses import asdict
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.core.semantic_executor import semantic_engine_for
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/chess_capture_vocabulary_20261006.json'
SOURCES=('scripts/audit_chess_capture_vocabulary.py','docs/research/CHESS_CAPTURE_VOCABULARY_PROTOCOL.md',
 'scripts/chess_capture_effect_hint.py','scripts/chess_capture_effect_hint_v2.py',
 'generic_chess/core/semantic_executor.py','generic_chess/rules/compiler.py','generic_chess/rules/western_chess.py',
 'docs/research/data/chess_capture_effect_hint_20261006.json','docs/research/data/chess_capture_effect_v2_20261006.json',
 'scripts/research_record.py')


def main():
    if OUT.exists():raise FileExistsError('structural admission diagnostic never rerun')
    start=monotonic();r=dict(complete=False,public_transitions=0,runtime_pushes=0,source_pushes=0,terms=0,patterns=[],
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    try:
        compiled=compile_ruleset_for_execution(build_western_chess_ruleset());r['compilations']=1
        ir=semantic_engine_for(compiled).ir
        a1={'move','remove','set_token','clear_token','set_flag','promote'}
        a2={'move','remove','set_current_type','set_bool','clear_right','set_token','clear_token'}
        for p in ir.patterns:
            row=dict(pattern_id=p.pattern_id,geometries=[ir.geometry[g].kind for g in p.geometry_ids],effects=[],unsupported_v1=[],unsupported_v2=[])
            for e in p.effects:
                if r['terms']>=5000 or monotonic()-start>=15:raise ValueError('term/time cap')
                r['terms']+=1;row['effects'].append(asdict(e))
                if e.kind not in a1:row['unsupported_v1'].append(e.kind)
                if e.kind not in a2:row['unsupported_v2'].append(e.kind)
            r['patterns'].append(row)
        r['vocabulary']=sorted({e['kind'] for p in r['patterns'] for e in p['effects']})
        r['complete']=True
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k not in ('source_sha256','patterns')}))
    print(json.dumps([{'id':p['pattern_id'],'geometry':p['geometries'],'v1':p['unsupported_v1'],'v2':p['unsupported_v2']} for p in r['patterns'] if p['unsupported_v1'] or p['unsupported_v2']]))


if __name__=='__main__':main()
