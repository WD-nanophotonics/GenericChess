"""Frozen complete-selector source/use diagnostic, not prior validation."""
from dataclasses import replace
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import shutil
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_exchange_custody import synthetic_state
from scripts.chess_certificate_request import chess_certificate_request
from scripts.conditional_dtm_bridge import dtm_horizon_interval, PREMISES
from scripts.material_leaf_choice import inventory_features, material_score, one_ply_choice
from scripts.partial_decision_loss import paired_margin
from scripts.public_goal_intervals import PublicGame

PROTOCOL = 'docs/research/SMALL_SELECTOR_DIAGNOSTIC_PROTOCOL.md'
PROTOCOL_SHA = 'ddd53260fd617c1f510fdb0dcee8744ec2879709dc372a45a133e3ef0c23be61'
MANIFEST_SHA = '1a2e45d5eb54ff451a0b7cfb8dad5e31f208d63c0654b6f8eac9581d39886a72'


def audit(report):
    start = monotonic()
    def check():
        if monotonic()-start >= 15:
            raise TimeoutError('frozen15-second cap')
    source = ROOT/'.local_agent/certificate_source'
    manifest_path = source/'manifest-source-correction.json'
    if hashlib.sha256((ROOT/PROTOCOL).read_bytes()).hexdigest() != PROTOCOL_SHA or hashlib.sha256(manifest_path.read_bytes()).hexdigest() != MANIFEST_SHA:
        raise ValueError('frozen inputs drift')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    files = [(source/'tables'/m['name'], m) for m in manifest['tables']]
    files += [(source/'python-chess'/m['name'], m) for m in manifest['source_files']]
    for p, m in files:
        if len(p.read_bytes()) != m['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest() != m['sha256']:
            raise ValueError('source integrity conflict')
    working = source/'selector-diagnostic-working-tables'
    if working.exists():
        raise FileExistsError('no unchanged rerun')
    working.mkdir()
    for p, _ in files[:2]:
        shutil.copyfile(p, working/p.name)
    sys.path.insert(0, str(source/'python-chess'))
    import chess
    import chess.gaviota
    if chess.__version__ != '1.11.2' or Path(chess.__file__).resolve() != (source/'python-chess/chess/__init__.py').resolve():
        raise ValueError('isolated source required')
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    game = PublicGame(compiled)
    base = [(27, 0, 'K'), (63, 1, 'K'), (18, 1, 'R'), (28, 1, 'B')]
    plans = []
    for file_flip, owner_flip in ((False, False), (True, False), (False, True), (True, True)):
        check(); board = [None]*64
        for s, owner, kind in base:
            rank, file = divmod(s, 8)
            square = (7-rank if owner_flip else rank)*8+(7-file if file_flip else file)
            board[square] = Piece(1-owner if owner_flip else owner, kind, kind, False)
        position = replace(initial_state(compiled).position, board=tuple(board), side_to_move=int(owner_flip),
                           aux_state=(((0, -1), 0), ((1, -1), 0), ((2, -1), None), ((3, -1), 0), ((4, -1), 0)))
        root = synthetic_state(compiled, position)
        packet = chess_certificate_request(root, compiled)
        children = {}
        for action in game.actions(root, check):
            report['enumerated'] += 1; check()
            if len(children) >= 128 or report['public_transitions'] >= 128 or report['enumerated'] > 5000:
                raise ValueError('choice/transition/enum cap')
            key = str(action)
            if key in children:
                raise ValueError('canonical key collision')
            report['public_transitions'] += 1
            children[key] = game.successor(root, action)
        selections = {}
        for name, weights in (('ordering', {('board', 'R'): F(1), ('board', 'B'): F(1, 2)}),
                              ('unit', {('board', 'R'): F(1), ('board', 'B'): F(1)}),
                              ('zero', {('board', 'R'): F(0), ('board', 'B'): F(0)})):
            result = one_ply_choice(children, game, lambda s: material_score(s.position, weights, {'K'}, 2),
                                    owner=int(owner_flip), complete=True)
            if not result['complete']:
                raise ValueError('unqualified selector')
            selections[name] = result
        row = {'file_flip': file_flip, 'owner_flip': owner_flip, 'root_request': packet,
               'complete_choice_count': len(children), 'selections_before_labels': selections,
               'all_child_features': {k: {str(t): n for t, n in inventory_features(s.position, {'K'}).items()} for k, s in children.items()},
               'selected_goal_evidence': {}, 'paired_margins': {}}
        report['rows'].append(row); plans.append((children, row))
    report['all_selections_frozen_before_probes'] = True
    cached = {}
    with chess.gaviota.PythonTablebase() as table:
        table.add_directory(str(working))
        for children, row in plans:
            intervals = {k: (-1, 1) for k in children}
            for key in {v['selected'] for v in row['selections_before_labels'].values()}:
                check(); child = children[key]; terminal = game.terminal(child)
                if terminal.is_terminal:
                    value = 0 if terminal.winner is None else 1 if terminal.winner == 0 else -1
                    intervals[key] = (value, value)
                    row['selected_goal_evidence'][key] = {'local_terminal': terminal.status.value, 'interval': intervals[key]}
                    continue
                packet = chess_certificate_request(child, compiled)
                if sum(p is not None for p in child.position.board) > 3:
                    row['selected_goal_evidence'][key] = {'request': packet, 'interval': (-1, 1), 'reason': 'missing four-piece source; retained unknown'}
                    continue
                fen = packet['fen']
                if fen not in cached:
                    if report['outer_probe_calls']+2 > 20:
                        raise ValueError('source call cap')
                    board = chess.Board(fen)
                    if not board.is_valid():
                        raise ValueError('invalid converted child')
                    report['outer_probe_calls'] += 1; dtm = table.probe_dtm(board); check()
                    report['outer_probe_calls'] += 1; wdl = table.probe_wdl(board); check()
                    cached[fen] = (dtm, wdl)
                dtm, wdl = cached[fen]
                # Explicit conditional source/semantic premises from the first
                # probe report and scoped argument, not packet verification.
                result = dtm_horizon_interval(side=child.position.side_to_move, ply=child.ply_count,
                    max_ply=1000, repetition_limit=100000,
                    max_repetition_count=max(n for _, n in child.repetition_counts),
                    signed_dtm=dtm, wdl_stm=wdl, premises={p: True for p in PREMISES})
                intervals[key] = result['interval']
                row['selected_goal_evidence'][key] = {'request': packet, 'signed_dtm': dtm, 'wdl_stm': wdl,
                                                     'conditional_bridge': result}
            selection = row['selections_before_labels']
            for baseline in ('unit', 'zero'):
                row['paired_margins'][baseline] = paired_margin(intervals, selection['ordering']['selected'],
                                                               selection[baseline]['selected'], int(row['owner_flip']))
    for p, m in files:
        if hashlib.sha256(p.read_bytes()).hexdigest() != m['sha256']:
            raise ValueError('original integrity lost')
    for p, m in files[:2]:
        if hashlib.sha256((working/p.name).read_bytes()).hexdigest() != m['sha256']:
            raise ValueError('working bytes changed')
    report['source_manifest_sha256'] = MANIFEST_SHA
    report['complete'] = True; report['seconds'] = monotonic()-start


if __name__ == '__main__':
    target = ROOT/'docs/research/data/small_selector_diagnostic_20261004.json'
    if not target.parent.is_dir() or target.exists():
        raise ValueError('preflight destination; no rerun')
    report = {'complete': False, 'public_transitions': 0, 'enumerated': 0, 'outer_probe_calls': 0, 'rows': []}
    try:
        audit(report)
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
    paths = [PROTOCOL, 'scripts/audit_small_selector_diagnostic.py', 'scripts/chess_certificate_request.py',
             'scripts/conditional_dtm_bridge.py', 'scripts/material_leaf_choice.py', 'scripts/partial_decision_loss.py',
             'scripts/public_goal_intervals.py', 'scripts/audit_exchange_custody.py',
             'generic_chess/core/semantic_executor.py', 'generic_chess/rules/western_chess.py']
    report['source_sha256'] = {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
    target.write_text(json.dumps(report, indent=2, default=str)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ('rows', 'source_sha256')}))
