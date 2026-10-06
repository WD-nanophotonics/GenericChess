from pathlib import Path
from dataclasses import replace
from time import monotonic
import hashlib,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_exchange_custody import synthetic_state
from scripts.chess_certificate_request import chess_certificate_request
from scripts.audit_lichess_complete_children import uci
from scripts.public_goal_intervals import PublicGame
from scripts.research_record import write_record
PROTOCOL='docs/research/MIXED_SYZYGY_SOURCE_PROTOCOL.md'
OUT=ROOT/'docs/research/data/mixed_syzygy_source_20261006.json'
SOURCES=(PROTOCOL,'scripts/audit_mixed_syzygy_source.py','scripts/chess_certificate_request.py',
 'scripts/audit_exchange_custody.py','scripts/audit_lichess_complete_children.py',
 'scripts/public_goal_intervals.py','scripts/research_record.py','generic_chess/rules/western_chess.py',
 'generic_chess/core/semantic_executor.py')


def audit(r):
    start=monotonic();source=ROOT/'.local_agent/certificate_source';work=source/'syzygy-mixed-source'
    acquisition=json.loads((source/'mixed_syzygy_acquisition_20261006.json').read_text())
    if not acquisition['complete'] or acquisition['protocol_sha256']!=hashlib.sha256((ROOT/PROTOCOL).read_bytes()).hexdigest():raise ValueError('qualified acquisition/protocol')
    for m in acquisition['files']:
        if hashlib.sha256((work/m['path']).read_bytes()).hexdigest()!=m['sha256']:raise ValueError('source drift')
    old=json.loads((source/'manifest-source-correction.json').read_text())
    for name in ('chess/__init__.py','LICENSE.txt'):
        m=next(x for x in old['source_files'] if x['name']==name);path=source/'python-chess'/name
        if hashlib.sha256(path.read_bytes()).hexdigest()!=m['sha256']:raise ValueError('original reader/license drift')
        dest=work/name;dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists():raise FileExistsError('preserve isolated reader copy')
        shutil.copyfile(path,dest)
    sys.path.insert(0,str(work));import chess;import chess.syzygy
    if chess.__version__!='1.11.2' or Path(chess.__file__).resolve()!=(work/'chess/__init__.py').resolve():raise ValueError('isolated pinned reader')
    compiled=compile_ruleset_for_execution(build_western_chess_ruleset());game=PublicGame(compiled)
    r.update(acquisition=acquisition,source_reader_sha256=hashlib.sha256((work/'chess/syzygy.py').read_bytes()).hexdigest())
    def check():
        if monotonic()-start>30:raise TimeoutError('30sec control safety fuse')
    with chess.syzygy.open_tablebase(str(work/'data/syzygy/regular'),load_dtz=False,max_fds=8) as table:
        for metadata in acquisition['files']:
            if not metadata['path'].endswith('.rtbw'):continue
            name=Path(metadata['path']).stem;left,right=name.split('v');board=[None]*64
            board[18]=Piece(0,'K','K',False);board[63]=Piece(1,'K','K',False)
            for square,mode in zip((8,9),left[1:]):board[square]=Piece(0,mode,mode,False)
            for square,mode in zip((47,),right[1:]):board[square]=Piece(1,mode,mode,False)
            if len(left)>3 or len(right)>2:raise ValueError('declared two-ordinary scope')
            p=replace(initial_state(compiled).position,board=tuple(board),side_to_move=0,
                aux_state=(((0,-1),0),((1,-1),0),((2,-1),None),((3,-1),0),((4,-1),0)))
            state=synthetic_state(compiled,p);packet=chess_certificate_request(state,compiled);external=chess.Board(packet['fen']);check()
            if not external.is_valid() or external.halfmove_clock!=0:raise ValueError('valid zero-clock native control')
            local=sorted(uci(a) for a in game.actions(state,check));foreign=sorted(m.uci() for m in external.legal_moves)
            r['enumerated']+=len(local)+len(foreign)
            if local!=foreign:raise ValueError('complete legal action mismatch')
            r['outer_wdl_calls']+=1;wdl=table.probe_wdl(external);check()
            if wdl not in (-2,-1,0,1,2):raise ValueError('retain five-way WDL50 class')
            outcome=external.outcome(claim_draw=False)
            r['rows'].append(dict(material=name,request=packet,complete_choices=local,source_wdl50=wdl,
                source_terminal=None if outcome is None else dict(termination=outcome.termination.name,winner=outcome.winner)))
    for m in acquisition['files']:
        if hashlib.sha256((work/m['path']).read_bytes()).hexdigest()!=m['sha256']:raise ValueError('source after-close drift')
    if len(r['rows'])!=24:raise ValueError('missing declared inventory class')
    r.update(complete=True,source_integrity_after_close=True,seconds=monotonic()-start)


if __name__=='__main__':
    if OUT.exists():raise FileExistsError('preserve controls')
    r=dict(complete=False,rows=[],enumerated=0,public_transitions=0,outer_wdl_calls=0,
      scope='24 native pawn-free 3/4piece source controls; not local WDL or pricing quality',
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    start=monotonic()
    try:audit(r)
    except Exception as e:r['error']=f'{type(e).__name__}: {e}'
    r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin for p,pin in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k not in ('rows','acquisition','source_sha256')}))
