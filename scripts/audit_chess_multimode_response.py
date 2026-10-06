"""One-shot checked multi-mode population; freeze choices before reply labels."""
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
from time import monotonic
import hashlib
import json
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from generic_chess.core.actions import action_target_square
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import initial_state
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_exchange_custody import synthetic_state
from scripts.native_chess_contact_intervals import EMPTY_AUX, _ongoing_features
from scripts.chess_exact_contact_family import exact_chess_contact_intervals
from scripts.material_leaf_choice import material_score, one_ply_choice
from scripts.public_goal_intervals import PublicGame
from scripts.finite_terminal_window import leaf_intervals, combine_replies, tie_margin
from scripts.partial_decision_loss import paired_margin
from scripts.research_record import write_record, record_value
OUT = ROOT/'docs/research/data/chess_multimode_response_20261006.json'
PRE = OUT.with_suffix('.selections.json')
SOURCES = ('scripts/audit_chess_multimode_response.py',
 'docs/research/CHESS_MULTIMODE_RESPONSE_PROTOCOL.md', 'scripts/finite_terminal_window.py',
 'scripts/chess_exact_contact_family.py', 'scripts/native_chess_contact_intervals.py',
 'scripts/material_leaf_choice.py', 'scripts/public_goal_intervals.py',
 'scripts/partial_decision_loss.py', 'scripts/research_record.py',
 'scripts/audit_exchange_custody.py', 'generic_chess/rules/western_chess.py',
 'generic_chess/core/transition.py', 'generic_chess/core/semantic_executor.py',
 'docs/research/data/chess_zero_target_correction_20261005.json')


def choice(i, label, options):
    key = f'GenericChess/multimode-response/v1/proposal/{i}/{label}'
    return options[int.from_bytes(hashlib.sha256(key.encode()).digest(), 'big') % len(options)]


def proposal(i):
    k = choice(i, 'K', [8*y+x for y in range(2, 6) for x in range(2, 6)])
    squares = [8*(k//8+dy)+k%8+dx for dx in (-1, 0, 1)
               for dy in (-1, 0, 1) if dx or dy]
    row = [(k, 0, 'K')]
    for mode in ('N', 'B', 'Q'):
        sq = choice(i, mode, squares); squares.remove(sq); row.append((sq, 1, mode))
    occupied = {sq for sq, _, _ in row}
    king = choice(i, 'enemy-K', [sq for sq in (0, 7, 56, 63) if sq not in occupied])
    row.append((king, 1, 'K')); occupied.add(king)
    pawn = choice(i, 'own-P', [sq for sq in range(24, 48) if sq not in occupied])
    row.append((pawn, 0, 'P')); occupied.add(pawn)
    rook = choice(i, 'own-R', [sq for sq in range(64) if sq not in occupied])
    row.append((rook, 0, 'R'))
    return row


def main():
    if OUT.exists() or PRE.exists():
        raise FileExistsError('frozen experiment never rerun')
    started = monotonic()
    report = dict(complete=False, proposals=0, enumerated=0, public_transitions=0,
        source_queries=0, rejection_counts={}, goal_intervals={},
        source_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def save():
        report['seconds'] = monotonic()-started; write_record(OUT, report)
    def check():
        if monotonic()-started >= 15:
            raise TimeoutError('15sec family cap')
    def reject(reason):
        report['rejection_counts'][reason] = report['rejection_counts'].get(reason, 0)+1
    save()
    try:
        c = compile_ruleset_for_execution(build_western_chess_ruleset())
        report['compilations'] = 1
        game = PublicGame(c); engine = semantic_engine_for(c)
        template = initial_state(c).position
        def actions(state):
            result = {}
            for action in game.actions(state, check):
                check()
                if report['enumerated'] >= 5000 or len(result) >= 128:
                    raise ValueError('enumeration/list cap')
                report['enumerated'] += 1; key = str(action)
                if key in result: raise ValueError('lossless action collision')
                result[key] = action
            return result
        def apply(state, action, parent_count):
            check()
            if report['public_transitions'] >= 128 or report['enumerated']+parent_count > 5000:
                raise ValueError('transition/membership cap')
            report['enumerated'] += parent_count
            report['public_transitions'] += 1
            child = game.successor(state, action); check(); return child
        root = None
        for i in range(128):
            check(); report['proposals'] += 1
            entries = proposal(i); board = [None]*64
            for sq, owner, tid in entries: board[sq] = Piece(owner, tid, tid)
            position = replace(template, board=tuple(board), side_to_move=0, aux_state=EMPTY_AUX)
            if engine.in_check(position, 1): reject('previous_mover_check'); continue
            if not engine.in_check(position, 0): reject('not_checked'); continue
            candidate = synthetic_state(c, position)
            if game.terminal(candidate).is_terminal: reject('terminal_root'); continue
            table = actions(candidate)
            if len(table) not in (2, 3): reject('branch_count'); continue
            captured = set()
            for action in table.values():
                target = action_target_square(action)
                piece = None if target is None else board[target.rank*8+target.file]
                if piece is not None and piece.owner == 1 and piece.current_type_id != 'K':
                    captured.add(piece.current_type_id)
            if len(captured) < 2: reject('two_capture_types'); continue
            root = candidate; report['proposal_index'] = i
            report['root'] = record_value(root); report['root_entries'] = entries
            report['all_root_actions'] = list(table); break
        if root is None: raise ValueError('no eligible root within128 proposals')
        # Compare only root board fields of old four exposed stress records.
        key = record_value(root.position.board)
        for name in ('chess_double_check_20261005.selections.json',
                     'chess_contact_scoped_use_20261005.selections.json',
                     'chess_knight_interposition_20261005.json',
                     'chess_pinned_queen_mate_20261005.json'):
            old = json.loads((OUT.parent/name).read_text())
            def root_boards(value):
                if isinstance(value, dict):
                    for field, item in value.items():
                        if field == 'root' and isinstance(item, dict):
                            state = item.get('local_state', item)
                            p = state.get('position', {})
                            if p.get('board') == key: raise ValueError('exposed root identity')
                        elif isinstance(item, (dict, list)): root_boards(item)
                elif isinstance(value, list):
                    for item in value: root_boards(item)
            root_boards(old)
        report['old_root_identity_check'] = True
        children = {}; report['children'] = {}; save()
        for key, action in table.items():
            child = apply(root, action, len(table)); children[key] = child
            report['children'][key] = record_value(child); save()
            _ongoing_features(child.position)
        methods = {}
        for law in ('geometric_half', 'linear_mixture'):
            boxes = exact_chess_contact_intervals(law)
            weights = {k: lo for k, (lo, hi) in boxes.items() if lo == hi}
            methods[law] = one_ply_choice(children, game,
                lambda s, weights=weights: material_score(s.position, weights, {'K'}, 30),
                owner=0, complete=True)
        for name, value in (('unit', F(1)), ('zero', F(0))):
            weights = {('board', mode): value for mode in 'PNBRQ'}
            methods[name] = one_ply_choice(children, game,
                lambda s, weights=weights: material_score(s.position, weights, {'K'}, 30),
                owner=0, complete=True)
        for value in methods.values():
            if not value['complete']: raise ValueError('candidate admission failed')
            value['tie_set'] = sorted(k for k, score in value['scores'].items() if score == value['score'])
        report['selections_before_labels'] = record_value(methods)
        write_record(PRE, report); report['prelabel_sha256'] = hashlib.sha256(PRE.read_bytes()).hexdigest()
        report['replies'] = {}; save()
        for key, child in children.items():
            terminal = game.terminal(child)
            if terminal.is_terminal:
                report['goal_intervals'][key] = leaf_intervals(terminal); save(); continue
            reply_table = actions(child)
            report['replies'][key] = dict(all_actions=list(reply_table), rows=[]); save()
            rows = []
            for reply_id, action in reply_table.items():
                end = apply(child, action, len(reply_table)); label = leaf_intervals(game.terminal(end))
                rows.append(label)
                report['replies'][key]['rows'].append(dict(action=reply_id, state=record_value(end), labels=label))
                save()
            report['goal_intervals'][key] = combine_replies(rows, owner=1, complete=True); save()
        report['comparisons'] = {}
        for law in ('geometric_half', 'linear_mixture'):
            for baseline in ('unit', 'zero'):
                name = law+'/'+baseline; report['comparisons'][name] = {}
                for target in ('window', 'eventual'):
                    intervals = {key: value[target] for key, value in report['goal_intervals'].items()}
                    margin = paired_margin(intervals, methods[law]['selected'], methods[baseline]['selected'])
                    report['comparisons'][name][target] = dict(canonical_margin=margin,
                        tie_margin=tie_margin(intervals, methods[law]['tie_set'], methods[baseline]['tie_set'], owner=0),
                        delta='1/10', verdict='improvement' if margin[0] >= F(1, 10) else 'failure' if margin[1] < F(1, 10) else 'inconclusive')
        report['complete'] = True
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
    report['source_hashes_unchanged'] = all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == h for p, h in report['source_sha256'].items())
    save()
    print(json.dumps({k: v for k, v in report.items() if k not in ('source_sha256', 'root', 'children', 'replies', 'selections_before_labels')}, default=str))


if __name__ == '__main__': main()
