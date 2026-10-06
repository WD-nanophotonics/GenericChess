"""Author-source replay of stored events only; no Core new transitions."""
from pathlib import Path
from time import monotonic
import hashlib
import json
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.research_record import write_record
OUT = ROOT/'docs/research/data/chess_multimode_source_replay_20261006.json'
RAW = 'docs/research/data/chess_multimode_response_20261006.json'
SOURCES = ('scripts/audit_chess_multimode_source_replay.py',
 'docs/research/CHESS_MULTIMODE_SOURCE_REPLAY_PROTOCOL.md', RAW,
 'docs/research/data/chess_multimode_response_20261006.selections.json',
 'scripts/research_record.py')
MANIFEST = ROOT/'.local_agent/certificate_source/manifest-source-correction.json'
MANIFEST_SHA = '1a2e45d5eb54ff451a0b7cfb8dad5e31f208d63c0654b6f8eac9581d39886a72'


def uci(key):
    move = key.rsplit(':', 1)[-1]
    if len(move) != 5 or move[2] != '-':
        raise ValueError('this recorded nonpromotion scope requires full board action')
    return move.replace('-', '')


def fen(state):
    position = state['position']; cells = position['board']; rows = []
    for rank in reversed(range(8)):
        row = ''; empty = 0
        for file in range(8):
            p = cells[rank*8+file]
            if p is None: empty += 1
            else:
                if empty: row += str(empty); empty = 0
                if p['base_type_id'] != p['current_type_id'] or p['promoted']:
                    raise ValueError('stored native origin scope failed')
                t = p['current_type_id']; row += t if p['owner'] == 0 else t.lower()
        if empty: row += str(empty)
        rows.append(row)
    return '/'.join(rows)+(' w' if position['side_to_move'] == 0 else ' b')+' - - 0 1'


def main():
    if OUT.exists(): raise FileExistsError('independent replay never rerun')
    start = monotonic()
    r = dict(complete=False, author_pushes=0, author_legal_entries=0,
        public_transitions=0, source_table_queries=0, state_checks=0,
        parent_choice_checks=0, records=[],
        source_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def save(): r['seconds'] = monotonic()-start; write_record(OUT, r)
    save()
    try:
        raw = json.loads((ROOT/RAW).read_text())
        if not raw['complete'] or not raw['source_hashes_unchanged']:
            raise ValueError('complete frozen local census required')
        for p, pin in raw['source_sha256'].items():
            if hashlib.sha256((ROOT/p).read_bytes()).hexdigest() != pin:
                raise ValueError('original census source drift')
        if hashlib.sha256(MANIFEST.read_bytes()).hexdigest() != MANIFEST_SHA:
            raise ValueError('manifest drift')
        manifest = json.loads(MANIFEST.read_text())
        entry = next(e for e in manifest['source_files'] if e['name'] == 'chess/__init__.py')
        source = MANIFEST.parent/'python-chess'; author = source/entry['name']
        if author.stat().st_size != entry['bytes'] or hashlib.sha256(author.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('author implementation drift')
        r['author_sha256'] = entry['sha256']; r['manifest_sha256'] = MANIFEST_SHA
        sys.path.insert(0, str(source)); import chess
        if chess.__version__ != '1.11.2' or Path(chess.__file__).resolve() != author.resolve():
            raise ValueError('isolated pinned author implementation required')
        r['original_family_seconds'] = raw['seconds']
        def check():
            if monotonic()-start+raw['seconds'] >= 15:
                raise TimeoutError('combined15sec family cap')
        def state_check(board, local):
            check()
            if not board.is_valid(): raise ValueError('author state not valid')
            if board.board_fen() != fen(local).split()[0] or board.turn != (local['position']['side_to_move'] == 0):
                raise ValueError('independent board/actor mismatch')
            if board.castling_rights or board.ep_square is not None:
                raise ValueError('independent rights/EP scope mismatch')
            if local['ply_count'] != len(board.move_stack) or len(local['history']) != len(board.move_stack)+1:
                raise ValueError('fresh full history/stack mismatch')
            # At most two plies since fresh root: no threefold/50/75-move draw.
            if len(board.move_stack) > 2 or board.halfmove_clock > 2 or board.is_repetition(3):
                raise ValueError('short fresh adjudication scope failed')
            outcome = board.outcome(claim_draw=False); cached = local['terminal_status']
            if outcome is None:
                if cached['status'] != 'ongoing' or cached['winner'] is not None:
                    raise ValueError('independent ongoing terminal mismatch')
            else:
                mapping = {chess.Termination.CHECKMATE: 'checkmate', chess.Termination.STALEMATE: 'stalemate'}
                if outcome.termination not in mapping: raise ValueError('extra author adjudication outside local comparison scope')
                winner = None if outcome.winner is None else 0 if outcome.winner else 1
                if cached['status'] != mapping[outcome.termination] or cached['winner'] != winner:
                    raise ValueError('independent terminal/winner mismatch')
            r['state_checks'] += 1
        def choices_check(board, keys):
            check(); local = [uci(k) for k in keys]
            author_moves = sorted(move.uci() for move in board.legal_moves)
            if len(local) != len(set(local)) or sorted(local) != author_moves:
                raise ValueError('independent COMPLETE action/multiplicity mismatch')
            r['author_legal_entries'] += len(author_moves); r['parent_choice_checks'] += 1
            if r['author_legal_entries'] > 5000: raise ValueError('author enumeration cap')
        def pushed(board, key):
            check()
            if r['author_pushes'] >= 128: raise ValueError('128 independent pushes cap')
            result = board.copy(stack=True); result.push_uci(uci(key)); r['author_pushes'] += 1
            return result
        board = chess.Board(fen(raw['root']))
        state_check(board, raw['root']); choices_check(board, raw['all_root_actions'])
        for key, child in raw['children'].items():
            cb = pushed(board, key); state_check(cb, child)
            if key not in raw['replies']: raise ValueError('unexpected root terminal in stored actual scope')
            reply = raw['replies'][key]; choices_check(cb, reply['all_actions'])
            if sorted(row['action'] for row in reply['rows']) != sorted(reply['all_actions']):
                raise ValueError('stored reply events not complete')
            for row in reply['rows']:
                eb = pushed(cb, row['action']); state_check(eb, row['state'])
                outcome = eb.outcome(claim_draw=False)
                label = 0 if outcome is None or outcome.winner is None else 1 if outcome.winner else -1
                if row['labels']['window'] != [label, label]: raise ValueError('independent window label mismatch')
                expected = [-1, 1] if outcome is None else [label, label]
                if row['labels']['eventual'] != expected: raise ValueError('independent eventual enclosure mismatch')
                r['records'].append(dict(root_action=key, reply=row['action'], window=label,
                    independent_terminal=None if outcome is None else outcome.termination.name))
                save()
        r['complete'] = r['author_pushes'] == raw['public_transitions'] == 90
        r['independent_scope'] = 'all90 stored transitions,91 states,4 complete choice sets; fresh2ply only; no new roots/WDL or untouched strength'
    except Exception as error: r['error'] = f'{type(error).__name__}: {error}'
    r['source_hashes_unchanged'] = all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == pin for p, pin in r['source_sha256'].items())
    save(); print(json.dumps({k: v for k, v in r.items() if k not in ('source_sha256', 'records')}))


if __name__ == '__main__': main()
