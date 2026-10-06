"""Same saved source root, legal versus forced EP FEN representation."""
from pathlib import Path
from time import monotonic
import hashlib
import json
import sys
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from scripts.research_record import write_record
OUT = ROOT/'docs/research/data/lichess_ep_view_20261006.json'
RAW = 'docs/research/data/lichess_daily_preflight_20261006.json'
SOURCE = 'docs/research/data/lichess_daily_source_20261006.json'
SOURCES = ('scripts/audit_lichess_ep_view.py', 'docs/research/LICHESS_EP_VIEW_PROTOCOL.md',
           'scripts/research_record.py', RAW, SOURCE)


def main():
    if OUT.exists(): raise FileExistsError('same-source EP view never rerun')
    start = monotonic()
    r = dict(complete=False, author_pushes=0, public_transitions=0, runtime_pushes=0,
             source_queries=0, author_legal_entries=0,
             source_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    try:
        old = json.loads((ROOT/RAW).read_text()); source = json.loads((ROOT/SOURCE).read_text())
        if old['complete'] or old['error'] != 'ValueError: advertised root/complete PGN mismatch' or old['author_pushes'] != 52:
            raise ValueError('exact preserved EP representation failure required')
        for raw in (old, source):
            if not raw['source_hashes_unchanged']: raise ValueError('original source qualification failed')
            for p, digest in raw['source_sha256'].items():
                if hashlib.sha256((ROOT/p).read_bytes()).hexdigest() != digest: raise ValueError('source drift')
        manifest = ROOT/'.local_agent/certificate_source/manifest-source-correction.json'
        if hashlib.sha256(manifest.read_bytes()).hexdigest() != old['manifest_sha256']: raise ValueError('manifest drift')
        entry = next(e for e in json.loads(manifest.read_text())['source_files'] if e['name'] == 'chess/__init__.py')
        author = manifest.parent/'python-chess'/entry['name']
        if hashlib.sha256(author.read_bytes()).hexdigest() != old['author_sha256']: raise ValueError('author drift')
        sys.path.insert(0, str(author.parent.parent)); import chess
        if chess.__version__ != '1.11.2' or Path(chess.__file__).resolve() != author.resolve(): raise ValueError('pinned author required')
        puzzle = source['payload']['puzzle']; last = old['history'][-1]
        if len(old['history']) != old['prefix_plies'] or last['uci'] != puzzle['lastMove']:
            raise ValueError('saved ancestry/last move mismatch')
        board = chess.Board(last['fen'])
        if not board.is_valid() or board.fen(en_passant='fen').split()[:3] != puzzle['fen'].split()[:3]:
            raise ValueError('same exact saved board/actor/rights required')
        if board.ep_square is None or board.has_legal_en_passant() or board.fen().split()[:4] != puzzle['fen'].split()[:4]:
            raise ValueError('not exactly legal-EP serialization omission')
        moves = sorted(move.uci() for move in board.legal_moves)
        if len(moves) > 128 or monotonic()-start >= 15: raise ValueError('EP view scope/cap')
        r['author_legal_entries'] = len(moves)
        if puzzle['solution'][0] not in moves: raise ValueError('advertised first answer not legal')
        r.update(puzzle_id=puzzle['id'], saved_full_fen=last['fen'], api_display_fen=puzzle['fen'],
                 legal_ep_fen=board.fen(), forced_ep_fen=board.fen(en_passant='fen'),
                 ep_target=chess.square_name(board.ep_square), has_legal_en_passant=False,
                 snapshot_stack_length=len(board.move_stack), full_saved_ancestry_length=old['prefix_plies'],
                 root_actions=moves, branch_count=len(moves), reference_first_answer=puzzle['solution'][0],
                 required_three_model_events=old['prefix_plies']+4*len(moves),
                 required_pure_child_events=old['prefix_plies']+len(moves),
                 cumulative_author_pushes=old['author_pushes'],
                 cumulative_author_legal_entries=old['author_legal_entries']+len(moves),
                 full_history_terminal_view_qualified=False)
        r['complete'] = True
    except Exception as error: r['error'] = f'{type(error).__name__}: {error}'
    r['seconds'] = monotonic()-start
    r['source_hashes_unchanged'] = all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == digest for p, digest in r['source_sha256'].items())
    write_record(OUT, r)
    print(json.dumps({k: v for k, v in r.items() if k not in ('source_sha256', 'root_actions')}))


if __name__ == '__main__': main()
