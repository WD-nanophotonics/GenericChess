from pathlib import Path
from time import monotonic
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.core.semantic_executor import semantic_engine_for
from scripts.chess_capture_effect_hint import ChessCaptureEffectHint
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/chess_capture_effect_hint_20261006.json'
INPUT='docs/research/data/chess_qsearch_ep_20261006.json'
SOURCES=('scripts/audit_chess_capture_effect_hint.py','scripts/chess_capture_effect_hint.py',
 'docs/research/CHESS_CAPTURE_EFFECT_HINT_PROTOCOL.md',INPUT,
 'generic_chess/core/semantic_executor.py','generic_chess/rules/ir.py',
 'generic_chess/rules/western_chess.py','scripts/native_chess_contact_intervals.py','scripts/research_record.py')


def main():
    if OUT.exists(): raise FileExistsError('capture-hint qualification closed')
    start=monotonic();r=dict(complete=False,public_transitions=0,runtime_pushes=0,source_pushes=0,
        terms=0,rows=[],source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    try:
        raw=json.loads((ROOT/INPUT).read_text())
        if not raw['complete'] or not raw['source_hashes_unchanged']:raise ValueError('qualified saved inputs required')
        for p,pin in raw['source_sha256'].items():
            if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=pin:raise ValueError('old record drift')
        compiled=compile_ruleset_for_execution(build_western_chess_ruleset());r['compilations']=1
        engine=semantic_engine_for(compiled);hint=ChessCaptureEffectHint(compiled.ruleset_fingerprint,engine.ir.patterns)
        r['pattern_bits']=hint.bits
        for move,row in raw['children'].items():
            if r['terms']>=5000 or monotonic()-start>=15:raise ValueError('term/time cap')
            fields=row['action'].split(':')
            if len(fields)!=3 or fields[2].replace('-','')!=move:raise ValueError('saved native pattern encoding')
            r['terms']+=1;bit=hint.legal_pattern_captures(fields[0])
            r['rows'].append(dict(uci=move,pattern_id=fields[0],hint_capture=bit,source_capture=row['is_capture']))
            if bit!=row['is_capture']:raise ValueError('capture metadata/source mismatch')
        r['complete']=True
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin for p,pin in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k not in ('source_sha256','rows','pattern_bits')}))


if __name__=='__main__':main()
