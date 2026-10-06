"""Pinned-author history/branch-cost admission; no Core events or search."""
from pathlib import Path
from time import monotonic
import hashlib
import json
import re
import sys
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from scripts.research_record import write_record
OUT = ROOT/'docs/research/data/lichess_daily_preflight_20261006.json'
RAW = 'docs/research/data/lichess_daily_source_20261006.json'
SOURCES = ('scripts/audit_lichess_daily_preflight.py', 'docs/research/LICHESS_DAILY_REFERENCE_PROTOCOL.md',
           'scripts/research_record.py', RAW)
MANIFEST_SHA = '1a2e45d5eb54ff451a0b7cfb8dad5e31f208d63c0654b6f8eac9581d39886a72'


def main():
    if OUT.exists(): raise FileExistsError('single reference preflight never rerun')
    start = monotonic()
    r = dict(complete=False, history_qualified=False, use_admitted=False, author_pushes=0,
             author_legal_entries=0, public_transitions=0, runtime_pushes=0, source_queries=0,
             source_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    try:
        raw = json.loads((ROOT/RAW).read_text())
        if not raw['complete'] or not raw['source_hashes_unchanged']: raise ValueError('successful fixed acquisition required')
        for p, digest in raw['source_sha256'].items():
            if hashlib.sha256((ROOT/p).read_bytes()).hexdigest() != digest: raise ValueError('source drift')
        body = (ROOT/RAW).with_suffix('.response').read_bytes()
        if hashlib.sha256(body).hexdigest() != raw['response_sha256'] or json.loads(body) != raw['payload']:
            raise ValueError('original response mismatch')
        manifest = ROOT/'.local_agent/certificate_source/manifest-source-correction.json'
        if hashlib.sha256(manifest.read_bytes()).hexdigest() != MANIFEST_SHA: raise ValueError('manifest drift')
        entry = next(e for e in json.loads(manifest.read_text())['source_files'] if e['name'] == 'chess/__init__.py')
        author = manifest.parent/'python-chess'/entry['name']
        if author.stat().st_size != entry['bytes'] or hashlib.sha256(author.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('author drift')
        sys.path.insert(0, str(author.parent.parent)); import chess
        if chess.__version__ != '1.11.2' or Path(chess.__file__).resolve() != author.resolve(): raise ValueError('pinned author required')
        r.update(author_sha256=entry['sha256'], manifest_sha256=MANIFEST_SHA)
        puzzle = raw['payload']['puzzle']; pgn = raw['payload']['game']['pgn']
        if type(puzzle['initialPly']) is not int or puzzle['initialPly'] < 0 or re.search(r'[\[\]{}()$]', pgn):
            raise ValueError('plain standard SAN/root index scope required')
        tokens = pgn.split(); length = puzzle['initialPly']+1
        if len(tokens) != length or length > 128: raise ValueError('full declared puzzle prefix required within128')
        r.update(puzzle_id=puzzle['id'], game_id=raw['payload']['game']['id'], prefix_plies=length,
                 reference_first_answer=puzzle['solution'][0], history=[], board_checks=0)
        board = chess.Board()
        for token in tokens:
            if monotonic()-start >= 15: raise TimeoutError('whole15sec cap')
            moves = list(board.legal_moves); r['author_legal_entries'] += 2*len(moves)
            if r['author_legal_entries'] > 5000: raise ValueError('returned/parse membership5000 cap')
            if board.outcome(claim_draw=False) is not None: raise ValueError('automatic terminal before puzzle root')
            move = board.parse_san(token)
            if move not in moves or r['author_pushes'] >= 128: raise ValueError('illegal prefix/source cap')
            board.push(move); r['author_pushes'] += 1
            if not board.is_valid(): raise ValueError('invalid author prefix')
            r['board_checks'] += 1
            r['history'].append(dict(san=token, uci=move.uci(), fen=board.fen(en_passant='fen'), promoted=board.promoted,
                                     automatic_terminal=None if board.outcome(claim_draw=False) is None else board.outcome(claim_draw=False).termination.name))
        if len(board.move_stack) != length or board.outcome(claim_draw=False) is not None:
            raise ValueError('full ongoing root stack required')
        if 'fen' not in puzzle or board.fen(en_passant='fen').split()[:4] != puzzle['fen'].split()[:4]:
            raise ValueError('advertised root/complete PGN mismatch')
        if puzzle.get('lastMove') != board.peek().uci(): raise ValueError('advertised last move mismatch')
        root_actions = sorted(move.uci() for move in board.legal_moves)
        r['author_legal_entries'] += len(root_actions)
        if r['author_legal_entries'] > 5000: raise ValueError('source enumeration cap')
        if puzzle['solution'][0] not in root_actions: raise ValueError('reference answer is not legal')
        r.update(root_fen=board.fen(en_passant='fen'), root_actions=root_actions,
                 branch_count=len(root_actions), required_three_model_events=length+4*len(root_actions),
                 history_qualified=True)
        if r['required_three_model_events'] > 128:
            r['use_rejection'] = 'declared full-history/child-table/three actual searches exceed128 even before runtime overhead'
        else:
            r['use_admitted'] = True
        r['complete'] = True
    except Exception as error: r['error'] = f'{type(error).__name__}: {error}'
    r['seconds'] = monotonic()-start
    r['source_hashes_unchanged'] = all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == digest for p, digest in r['source_sha256'].items())
    write_record(OUT, r)
    print(json.dumps({k: v for k, v in r.items() if k not in ('source_sha256', 'history', 'root_actions')}))


if __name__ == '__main__': main()
