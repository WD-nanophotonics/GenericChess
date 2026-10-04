"""Frozen actual source controls; no material candidate/use corpus."""
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import shutil
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.core.actions import action_source_square, action_target_square
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_exchange_custody import synthetic_state
from scripts.chess_certificate_request import chess_certificate_request
from scripts.public_goal_intervals import PublicGame

PROTOCOL = 'docs/research/SMALL_CERTIFICATE_FIRST_PROBE_PROTOCOL.md'
PROTOCOL_SHA = '00839e0be79ab5717ba29c94bdd8d601770e55cd97ca978d81e310184426415f'
MANIFEST_SHA = '1a2e45d5eb54ff451a0b7cfb8dad5e31f208d63c0654b6f8eac9581d39886a72'


def audit(report):
    started = monotonic(); source = ROOT/'.local_agent/certificate_source'
    manifest_path = source/'manifest-source-correction.json'
    if (hashlib.sha256((ROOT/PROTOCOL).read_bytes()).hexdigest() != PROTOCOL_SHA
            or hashlib.sha256(manifest_path.read_bytes()).hexdigest() != MANIFEST_SHA):
        raise ValueError('frozen protocol/source manifest drift')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if not manifest['complete']:
        raise ValueError('complete verified source required')
    def checkpoint():
        if monotonic()-started >= 15:
            raise TimeoutError('first-probe15-second cap')
    files = [(source/'tables'/f['name'], f) for f in manifest['tables']]
    files += [(source/'python-chess'/f['name'], f) for f in manifest['source_files']]
    for path, metadata in files:
        data = path.read_bytes()
        if len(data) != metadata['bytes'] or hashlib.sha256(data).hexdigest() != metadata['sha256']:
            raise ValueError('source file integrity conflict')
    working = source/'first-probe-working-tables'
    if working.exists():
        raise FileExistsError('preserve previous working copy; no rerun')
    working.mkdir()
    for path, _ in files[:2]:
        shutil.copyfile(path, working/path.name)
    sys.path.insert(0, str(source/'python-chess'))
    import chess
    import chess.gaviota
    if chess.__version__ != '1.11.2' or Path(chess.__file__).resolve() != (source/'python-chess/chess/__init__.py').resolve():
        raise ValueError('exact isolated source import required')
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    game = PublicGame(compiled); report['source_manifest'] = manifest
    def root(pieces, side):
        board = [None]*64
        for square, owner, base, current in pieces:
            board[square] = Piece(owner, base, current, base != current)
        position = replace(initial_state(compiled).position, board=tuple(board), side_to_move=side,
                           aux_state=(((0, -1), 0), ((1, -1), 0), ((2, -1), None), ((3, -1), 0), ((4, -1), 0)))
        return synthetic_state(compiled, position)
    def reflected(pieces):
        return [((7-s//8)*8+s%8, 1-o, b, t) for s, o, b, t in pieces]
    R = [(0, 0, 'K', 'K'), (63, 1, 'K', 'K'), (27, 0, 'R', 'R')]
    RP = [*R[:2], (27, 0, 'P', 'R')]
    B = [(0, 0, 'K', 'K'), (55, 1, 'K', 'K'), (27, 0, 'B', 'B')]
    BP = [*B[:2], (27, 0, 'P', 'B')]
    cases = [('R-own', R, 0), ('R-other', R, 1), ('RP-own', RP, 0),
             ('R-reflected', reflected(R), 1), ('RP-reflected', reflected(RP), 1),
             ('B-own', B, 0), ('B-other', B, 1), ('BP-own', BP, 0)]
    cached = {}
    def probe(table, fen):
        checkpoint()
        if fen not in cached:
            if report['outer_probe_calls']+2 > 20:
                raise ValueError('20 outer DTM/WDL calls cap')
            external = chess.Board(fen)
            report['outer_probe_calls'] += 1; dtm = table.probe_dtm(external); checkpoint()
            report['outer_probe_calls'] += 1; wdl = table.probe_wdl(external); checkpoint()
            cached[fen] = {'signed_dtm': dtm, 'wdl_stm': wdl}
        return cached[fen]
    with chess.gaviota.PythonTablebase() as table:
        table.add_directory(str(working))
        for name, pieces, side in cases:
            checkpoint(); state = root(pieces, side)
            packet = chess_certificate_request(state, compiled)
            external = chess.Board(packet['fen'])
            if not external.is_valid():
                raise ValueError('invalid converted external board')
            public_choices = set()
            for action in game.actions(state, checkpoint):
                report['enumerated'] += 1; checkpoint()
                a = action_source_square(action); b = action_target_square(action)
                if a is None or b is None or getattr(action, 'promotion_target_id', None) is not None:
                    raise ValueError('pawn-free ordinary coordinate action required')
                key = f'{chr(97+a.file)}{a.rank+1}{chr(97+b.file)}{b.rank+1}'
                if key in public_choices or len(public_choices) >= 128 or report['enumerated'] > 5000:
                    raise ValueError('projected duplicate/choice cap')
                public_choices.add(key)
            external_choices = set()
            for move in external.legal_moves:
                report['enumerated'] += 1; checkpoint()
                if len(external_choices) >= 128 or report['enumerated'] > 5000:
                    raise ValueError('external choice cap')
                external_choices.add(move.uci())
            if public_choices != external_choices:
                raise AssertionError('complete projected legal choices differ')
            label = probe(table, packet['fen'])
            if label['wdl_stm'] and (not label['signed_dtm'] or (1 if label['signed_dtm'] > 0 else -1) != label['wdl_stm']):
                raise AssertionError('ongoing DTM/WDL sign inconsistent')
            report['rows'].append({'name': name, 'request': packet,
                                   'complete_choices': sorted(public_choices), 'source_probe': label})
        for name, pieces in (
            ('mate', [(46, 0, 'K', 'K'), (56, 0, 'R', 'R'), (63, 1, 'K', 'K')]),
            ('stalemate', [(53, 0, 'K', 'K'), (54, 0, 'R', 'R'), (63, 1, 'K', 'K')]),
        ):
            checkpoint(); state = root(pieces, 1); terminal = game.terminal(state)
            if not terminal.is_terminal or terminal.status.value != ('checkmate' if name == 'mate' else 'stalemate'):
                raise AssertionError('declared terminal local control refuted')
            try:
                chess_certificate_request(state, compiled)
            except ValueError as error:
                if 'terminal-first' not in str(error):
                    raise
            else:
                raise AssertionError('terminal request must not reach an ongoing certificate')
            fen = 'R6k/8/6K1/8/8/8/8/8 b - - 0 1' if name == 'mate' else '7k/5KR1/8/8/8/8/8/8 b - - 0 1'
            external = chess.Board(fen)
            if not external.is_valid() or not (external.is_checkmate() if name == 'mate' else external.is_stalemate()):
                raise AssertionError('external terminal disagreement')
            label = probe(table, fen)
            if label != {'signed_dtm': 0, 'wdl_stm': -1 if name == 'mate' else 0}:
                raise AssertionError('DTM zero terminal ambiguity control refuted')
            payload = asdict(state); payload['terminal_status']['status'] = terminal.status.value
            report['terminal_rows'].append({'name': name, 'fen': fen, 'local_state': payload,
                                            'authoritative_owner_zero_value': 1 if name == 'mate' else 0,
                                            'source_probe': label})
    for path, metadata in files:
        if hashlib.sha256(path.read_bytes()).hexdigest() != metadata['sha256']:
            raise ValueError('original/source mutated by probe')
    for path, metadata in files[:2]:
        if hashlib.sha256((working/path.name).read_bytes()).hexdigest() != metadata['sha256']:
            raise ValueError('working table bytes mutated')
    report['original_and_working_integrity_after_close'] = True
    report['unique_probed_fens'] = len(cached)
    report['complete'] = True
    report['seconds'] = monotonic()-started


if __name__ == '__main__':
    target = ROOT/'docs/research/data/small_certificate_first_probe_20261004.json'
    if not target.parent.is_dir() or target.exists():
        raise ValueError('preflight actual destination; preserve old evidence')
    started = monotonic()
    report = {'complete': False, 'public_transitions': 0, 'outer_probe_calls': 0,
              'enumerated': 0, 'rows': [], 'terminal_rows': [],
              'scope': 'source/association controls only; no material candidate or reserved use labels'}
    try:
        audit(report)
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
        report['seconds'] = monotonic()-started
    paths = [PROTOCOL, 'scripts/audit_small_certificate_first_probe.py',
             'scripts/chess_certificate_request.py', 'generic_chess/rules/western_chess.py',
             'generic_chess/core/semantic_executor.py', 'scripts/public_goal_intervals.py',
             'scripts/audit_exchange_custody.py']
    report['source_sha256'] = {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
    target.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ('rows', 'terminal_rows', 'source_manifest', 'source_sha256')}))
