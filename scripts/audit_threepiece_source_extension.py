"""Prospective five-mode source/association controls, never price-use labels."""
from pathlib import Path
from dataclasses import asdict,replace
from time import monotonic
from collections import Counter
import hashlib,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.core.pieces import Piece
from generic_chess.core.actions import action_source_square,action_target_square
from generic_chess.core.transition import initial_state
from generic_chess.core.identity import repetition_identity_key
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_exchange_custody import synthetic_state
from scripts.public_goal_intervals import PublicGame
from scripts.research_record import write_record
PROTOCOL='docs/research/THREEPIECE_SOURCE_EXTENSION_PROTOCOL.md'
PROTOCOL_SHA='91b37407edac1770eecbdbc2c8ae6acbcaecfd666f7dcf7002b4aed391ba26ef'
OLD_MANIFEST_SHA='1a2e45d5eb54ff451a0b7cfb8dad5e31f208d63c0654b6f8eac9581d39886a72'
OUT=ROOT/'docs/research/data/threepiece_source_extension_20261006.json'
SOURCES=(PROTOCOL,'scripts/audit_threepiece_source_extension.py','scripts/research_record.py',
 'generic_chess/rules/western_chess.py','generic_chess/core/semantic_executor.py',
 'scripts/audit_exchange_custody.py','scripts/public_goal_intervals.py')


def audit(r):
    start=monotonic();source=ROOT/'.local_agent/certificate_source'
    def check():
        if monotonic()-start>30:raise TimeoutError('30sec local safety fuse')
        if r['enumerated']>5000:raise ValueError('enumeration safety fuse')
    def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
    if digest(ROOT/PROTOCOL)!=PROTOCOL_SHA:raise ValueError('protocol drift')
    old_path=source/'manifest-source-correction.json'
    if digest(old_path)!=OLD_MANIFEST_SHA:raise ValueError('old manifest drift')
    old=json.loads(old_path.read_text());new=json.loads((source/'extra_threepiece_acquisition_20261006.json').read_text())
    if not old['complete'] or not new['complete'] or new['protocol_sha256']!=PROTOCOL_SHA:raise ValueError('complete source required')
    files=[(source/'tables'/m['name'],m) for m in old['tables']]
    files += [(source/'extra-threepiece-tables'/m['name'],m) for m in new['tables']]
    readers=[(source/'python-chess'/m['name'],m) for m in old['source_files']]
    for path,m in files+readers:
        if len(path.read_bytes())!=m['bytes'] or digest(path)!=m['sha256']:raise ValueError('source integrity')
    r.update(acquisition=new,reader_files=old['source_files'],old_manifest_sha256=OLD_MANIFEST_SHA,
             table_files=[m for _,m in files],table_bytes=sum(m['bytes'] for _,m in files))
    work=source/'five-mode-threepiece-working';work.mkdir(exist_ok=False)
    for path,_ in files:shutil.copyfile(path,work/path.name)
    sys.path.insert(0,str(source/'python-chess'));import chess;import chess.gaviota
    if chess.__version__!='1.11.2' or Path(chess.__file__).resolve()!=(source/'python-chess/chess/__init__.py').resolve():raise ValueError('isolated pinned reader required')
    compiled=compile_ruleset_for_execution(build_western_chess_ruleset());game=PublicGame(compiled)
    r['ruleset_fingerprint']=compiled.ruleset_fingerprint
    with chess.gaviota.PythonTablebase() as table:
        table.add_directory(str(work))
        for mode in ('N','B','R','Q','P'):
            check();square=9 if mode=='P' else 8;board=[None]*64
            for s,o,t in ((18,0,'K'),(63,1,'K'),(square,0,mode)):board[s]=Piece(o,t,t,False)
            position=replace(initial_state(compiled).position,board=tuple(board),side_to_move=0,
                aux_state=(((0,-1),0),((1,-1),0),((2,-1),None),((3,-1),0),((4,-1),0)))
            state=synthetic_state(compiled,position);terminal=game.terminal(state)
            if terminal.is_terminal or len(state.history)!=1 or state.history[-1].position_key!=repetition_identity_key(position,compiled) or dict(state.repetition_counts)!=Counter(h.position_key for h in state.history):raise ValueError('local ongoing history control')
            fen=f'7k/8/8/8/8/2K5/'+('1P6' if mode=='P' else mode+'7')+'/8 w - - 0 1'
            external=chess.Board(fen)
            if not external.is_valid():raise ValueError('invalid prospective external control')
            local=set()
            for action in game.actions(state,check):
                r['enumerated']+=1;check();a=action_source_square(action);b=action_target_square(action)
                if a is None or b is None or getattr(action,'promotion_target_id',None) is not None:raise ValueError('ordinary source-control action')
                local.add(f'{chr(97+a.file)}{a.rank+1}{chr(97+b.file)}{b.rank+1}')
            foreign=set()
            for move in external.legal_moves:r['enumerated']+=1;check();foreign.add(move.uci())
            if local!=foreign:raise AssertionError('complete legal-set mismatch')
            r['outer_probe_calls']+=1;dtm=table.probe_dtm(external);check()
            r['outer_probe_calls']+=1;wdl=table.probe_wdl(external);check()
            if dtm and (1 if dtm>0 else -1)!=wdl:raise AssertionError('DTM/WDL sign mismatch')
            outcome=external.outcome(claim_draw=False)
            payload=asdict(state);payload['terminal_status']['status']=terminal.status.value
            r['rows'].append(dict(mode=mode,fen=fen,local_state=payload,
                state_sha256=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                local_terminal=terminal.status.value,source_terminal=None if outcome is None else dict(termination=outcome.termination.name,winner=outcome.winner),
                complete_choices=sorted(local),signed_dtm=dtm,wdl_stm=wdl))
    if r['outer_probe_calls']!=10:raise ValueError('exact prospective probe scope')
    for path,m in files+readers:
        if digest(path)!=m['sha256']:raise ValueError('original integrity after close')
    for path,m in files:
        if digest(work/path.name)!=m['sha256']:raise ValueError('working integrity after close')
    r.update(complete=True,original_and_working_integrity_after_close=True,seconds=monotonic()-start)


if __name__=='__main__':
    if OUT.exists():raise FileExistsError('preserve one-shot controls')
    r=dict(complete=False,rows=[],enumerated=0,public_transitions=0,outer_probe_calls=0,
           scope='five synthetic source controls; not utility/strength or universal goal bridge',
           source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    start=monotonic()
    try:audit(r)
    except Exception as e:r['error']=f'{type(e).__name__}: {e}'
    r['seconds']=monotonic()-start
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin for p,pin in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k not in ('rows','source_sha256','reader_files','acquisition','table_files')}))
