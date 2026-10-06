"""One frozen first-quiet task; source adjudication precedes proxy stopping."""
from dataclasses import replace
from pathlib import Path
from time import monotonic
from fractions import Fraction as F
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
from scripts.native_chess_contact_intervals import EMPTY_AUX
from scripts.chess_exact_contact_family import exact_chess_contact_intervals
from scripts.material_leaf_choice import material_score, one_ply_choice, inventory_features
from scripts.public_goal_intervals import PublicGame
from scripts.outcome_set_order import set_order
from scripts.research_record import record_value, write_record
from scripts.audit_chess_multimode_source_replay import fen, uci

OUT = ROOT/'docs/research/data/chess_adjudicated_exchange_20261006.json'
PRE = OUT.with_suffix('.selections.json')
SOURCES = ('scripts/audit_chess_adjudicated_exchange.py',
 'docs/research/CHESS_ADJUDICATED_EXCHANGE_PROTOCOL.md',
 'scripts/audit_exchange_custody.py', 'scripts/native_chess_contact_intervals.py',
 'scripts/chess_exact_contact_family.py', 'scripts/material_leaf_choice.py',
 'scripts/public_goal_intervals.py', 'scripts/outcome_set_order.py',
 'scripts/research_record.py', 'scripts/audit_chess_multimode_source_replay.py',
 'generic_chess/rules/western_chess.py', 'generic_chess/core/transition.py',
 'generic_chess/core/semantic_executor.py',
 'docs/research/data/chess_zero_target_correction_20261005.json',
 'docs/research/data/chess_first_quiet_pilot_20261006.json')
MANIFEST = ROOT/'.local_agent/certificate_source/manifest-source-correction.json'
MANIFEST_SHA = '1a2e45d5eb54ff451a0b7cfb8dad5e31f208d63c0654b6f8eac9581d39886a72'


def pick(i, label, options):
    key = f'GenericChess/adjudicated-exchange/v1/proposal/{i}/{label}'
    return options[int.from_bytes(hashlib.sha256(key.encode()).digest(), 'big') % len(options)]


def proposal(i):
    k = pick(i, 'K', [8*y+x for y in range(2, 6) for x in range(2, 6)])
    adjacent = [8*(k//8+dy)+k%8+dx for dx in (-1, 0, 1)
                for dy in (-1, 0, 1) if dx or dy]
    entries = [(k, 0, 'K')]
    for mode in ('N', 'B'):
        sq = pick(i, mode, adjacent); adjacent.remove(sq); entries.append((sq, 1, mode))
    occupied = {sq for sq, _, _ in entries}
    enemy = pick(i, 'enemy-K', [sq for sq in (0, 7, 56, 63) if sq not in occupied])
    entries.append((enemy, 1, 'K')); occupied.add(enemy)
    entries.append((pick(i, 'own-R', [sq for sq in range(64) if sq not in occupied]), 0, 'R'))
    return entries


def nominal_risk(entries):
    """Raw occupation geometry only; no legal/action or successor queries."""
    by_type = {(owner, mode): sq for sq, owner, mode in entries}
    rook = by_type[0, 'R']; results = []; scanned = 0
    for captured, remaining in (('N', 'B'), ('B', 'N')):
        src = by_type[1, remaining]; dst = by_type[1, captured]
        occupied = {sq for sq, _, _ in entries} - {by_type[0, 'K'], dst}
        occupied.add(dst)  # nominal own King now occupies captured minor square
        dx, dy = rook % 8-src % 8, rook//8-src//8
        if remaining == 'N':
            attack = sorted((abs(dx), abs(dy))) == [1, 2]
        elif dx and abs(dx) == abs(dy):
            sx, sy = (1 if dx > 0 else -1), (1 if dy > 0 else -1)
            intermediates = [8*(src//8+sy*t)+src%8+sx*t for t in range(1, abs(dx))]
            scanned += len(intermediates)
            attack = not any(sq in occupied for sq in intermediates)
        else:
            attack = False
        results.append(dict(captured=captured, remaining=remaining, nominal_attack=attack))
    return results, scanned


def ordinary(state):
    return sum(p is not None and p.current_type_id != 'K' for p in state.position.board)


def main():
    if OUT.exists() or PRE.exists():
        raise FileExistsError('frozen one-shot task never rerun')
    start = monotonic()
    r = dict(complete=False, proposals=0, enumerated=0, public_transitions=0,
             nominal_checks=0, nominal_scanned=0, author_pushes=0,
             author_legal_entries=0, state_checks=0, parent_choice_checks=0,
             source_table_queries=0, compilations=0, rejection_counts={},
             children={}, replies={}, leaves={}, policies={}, outcomes={},
             source_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})

    def save():
        r['seconds'] = monotonic()-start; write_record(OUT, r)

    def check():
        if monotonic()-start >= 30:
            raise TimeoutError('whole local/source30sec cap')

    def actions(state):
        table = {}
        for a in game.actions(state, check):
            check()
            if r['enumerated'] >= 5000:
                raise ValueError('enumeration cap')
            key = str(a)
            if key in table:
                raise ValueError('canonical collision')
            table[key] = a; r['enumerated'] += 1
        return table

    def apply(state, a, n):
        check()
        if r['public_transitions'] >= 128 or r['enumerated']+n > 5000:
            raise ValueError('public128/membership5000 cap')
        r['public_transitions'] += 1; r['enumerated'] += n
        return game.successor(state, a)

    def state_check(board, state):
        check(); local = record_value(state); cached = game.terminal(state)
        if not board.is_valid() or board.board_fen() != fen(local).split()[0]:
            raise ValueError('author validity/board mismatch')
        if board.turn != (state.position.side_to_move == 0) or board.castling_rights or board.ep_square is not None:
            raise ValueError('author actor/rights/EP mismatch')
        if state.ply_count != len(board.move_stack) or len(state.history) != len(board.move_stack)+1:
            raise ValueError('fresh history mismatch')
        if len(board.move_stack) > 2 or board.halfmove_clock > 2 or board.is_repetition(3):
            raise ValueError('short fresh stack scope failed')
        outcome = board.outcome(claim_draw=False)
        result = None
        if outcome is None:
            if cached.is_terminal or cached.winner is not None:
                raise ValueError('local terminal without author terminal')
        else:
            winner = None if outcome.winner is None else 0 if outcome.winner else 1
            result = dict(termination=outcome.termination.name, winner=winner,
                          value=0 if winner is None else 1 if winner == 0 else -1)
            if outcome.termination == chess.Termination.INSUFFICIENT_MATERIAL:
                modes = [(p.owner, p.current_type_id) for p in state.position.board if p]
                if sorted(modes) not in ([(0, 'K'), (1, 'B'), (1, 'K')],
                                         [(0, 'K'), (1, 'K'), (1, 'N')]):
                    raise ValueError('insufficient draw outside declared recapture stock')
                if state.ply_count != 2 or cached.is_terminal or winner is not None:
                    raise ValueError('source/local draw contract difference outside scope')
                result['local_difference'] = 'ongoing versus automatic insufficient-material draw'
            else:
                mapping = {chess.Termination.CHECKMATE: 'checkmate', chess.Termination.STALEMATE: 'stalemate'}
                if outcome.termination not in mapping or cached.status.value != mapping[outcome.termination] or cached.winner != winner:
                    raise ValueError('source/local terminal mismatch')
        r['state_checks'] += 1
        return result

    def choices_check(board, table):
        check(); moves = sorted(m.uci() for m in board.legal_moves)
        local = [uci(k) for k in table]
        if len(local) != len(set(local)) or sorted(local) != moves:
            raise ValueError('complete independent action/multiplicity mismatch')
        r['parent_choice_checks'] += 1; r['author_legal_entries'] += len(moves)
        if r['author_legal_entries'] > 5000:
            raise ValueError('author action cap')

    def push(board, key):
        check()
        if r['author_pushes'] >= 128:
            raise ValueError('author push cap')
        result = board.copy(stack=True); result.push_uci(uci(key)); r['author_pushes'] += 1
        return result

    def leaf(path, parent, state, result):
        delta = ordinary(parent)-ordinary(state)
        if result is not None:
            row = dict(kind='source_terminal', source_terminal=result)
        elif delta == 0:
            f = inventory_features(state.position, {'K'})
            if any(loc != 'board' or mode not in 'PNBRQ' for loc, mode in f):
                raise ValueError('quiet inventory scope mismatch')
            row = dict(kind='quiet', vector=[f.get(('board', mode), 0) for mode in 'PNBRQ'])
        else:
            return False
        row.update(state=record_value(state), local_terminal=record_value(game.terminal(state)),
                   information_increment=state.ply_count > 1)
        r['leaves'][path] = row
        return True

    save()
    try:
        if hashlib.sha256(MANIFEST.read_bytes()).hexdigest() != MANIFEST_SHA:
            raise ValueError('manifest drift')
        entry = next(e for e in json.loads(MANIFEST.read_text())['source_files'] if e['name'] == 'chess/__init__.py')
        author = MANIFEST.parent/'python-chess'/entry['name']
        if author.stat().st_size != entry['bytes'] or hashlib.sha256(author.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('author drift')
        sys.path.insert(0, str(author.parent.parent)); import chess
        if chess.__version__ != '1.11.2' or Path(chess.__file__).resolve() != author.resolve():
            raise ValueError('pinned author required')
        r.update(author_sha256=entry['sha256'], manifest_sha256=MANIFEST_SHA)
        compiled = compile_ruleset_for_execution(build_western_chess_ruleset()); r['compilations'] = 1
        game = PublicGame(compiled); engine = semantic_engine_for(compiled)
        template = initial_state(compiled).position; root = None
        for i in range(120):
            check(); r['proposals'] += 1; entries = proposal(i)
            risks, scanned = nominal_risk(entries)
            r['nominal_checks'] += 2; r['nominal_scanned'] += scanned
            if r['nominal_checks'] > 240 or r['nominal_scanned'] > 1680:
                raise ValueError('nominal geometry reserve exceeded')
            reason = 'no_nominal_risk'
            if any(row['nominal_attack'] for row in risks):
                cells = [None]*64
                for sq, owner, mode in entries: cells[sq] = Piece(owner, mode, mode)
                p = replace(template, board=tuple(cells), side_to_move=0, aux_state=EMPTY_AUX)
                if engine.in_check(p, 1): reason = 'previous_mover_check'
                else:
                    candidate = synthetic_state(compiled, p)
                    if game.terminal(candidate).is_terminal: reason = 'terminal_root'
                    else:
                        table = actions(candidate)
                        if len(table) > 22: raise ValueError('root action structural bound failed')
                        captured = set(); quiet = 0
                        for a in table.values():
                            t = action_target_square(a); piece = None if t is None else cells[t.rank*8+t.file]
                            if piece and piece.owner == 1 and piece.current_type_id != 'K': captured.add(piece.current_type_id)
                            else: quiet += 1
                        if captured != {'N', 'B'} or not quiet: reason = 'dual_capture_and_quiet'
                        else:
                            root = candidate; r.update(proposal_index=i, root_entries=entries, nominal_risk=risks)
                            break
            r['rejection_counts'][reason] = r['rejection_counts'].get(reason, 0)+1
        if root is None: raise ValueError('no eligible root in frozen120 proposals')
        r['root'] = record_value(root); r['all_root_actions'] = list(table)
        board = chess.Board(fen(r['root']))
        if state_check(board, root) is not None: raise ValueError('unexpected author terminal root')
        choices_check(board, table)
        children = {}; boards = {}; goals = {}
        for key, a in table.items():
            children[key] = apply(root, a, len(table)); boards[key] = push(board, key)
            goals[key] = state_check(boards[key], children[key]); r['children'][key] = record_value(children[key])
        weights = {}
        for law in ('geometric_half', 'linear_mixture'):
            weights[law] = {k: lo for k, (lo, hi) in exact_chess_contact_intervals(law).items() if lo == hi}
        for law, v in (('unit', F(1)), ('zero', F(0))):
            weights[law] = {('board', mode): v for mode in 'PNBRQ'}
        for law, w in weights.items():
            policy = one_ply_choice(children, game, lambda s, w=w: material_score(s.position, w, {'K'}, 30), owner=0, complete=True)
            if not policy['complete']: raise ValueError('unqualified root controller')
            policy['tie_set'] = sorted(k for k, v in policy['scores'].items() if v == policy['score'])
            r['policies'][law] = record_value(policy)
        r['root_source_goals'] = goals
        r['selection_public_transition_count'] = r['public_transitions']
        write_record(PRE, r); r['prelabel_sha256'] = hashlib.sha256(PRE.read_bytes()).hexdigest()
        for key, child in children.items():
            if leaf(key, root, child, goals[key]): continue
            if ordinary(root)-ordinary(child) != 1: raise ValueError('root capture decrease failed')
            replies = actions(child)
            if len(replies) > 21: raise ValueError('defender action structural bound failed')
            choices_check(boards[key], replies)
            rr = dict(all_actions=list(replies), rows=[]); r['replies'][key] = rr
            for reply, a in replies.items():
                state = apply(child, a, len(replies)); eb = push(boards[key], reply)
                goal = state_check(eb, state); path = key+'/'+reply
                if not leaf(path, child, state, goal):
                    raise ValueError('capture did not stop at automatic draw; no deeper fallback')
                rr['rows'].append(dict(action=reply, path=path)); save()
        for law, policy in r['policies'].items():
            r['outcomes'][law] = {}
            for kind, keys in (('canonical', [policy['selected']]), ('all_ties', policy['tie_set'])):
                leaves = {p: row for p, row in r['leaves'].items() if p.split('/')[0] in keys}
                r['outcomes'][law][kind] = dict(paths=list(leaves),
                    vectors={p: row['vector'] for p, row in leaves.items() if row['kind'] == 'quiet'},
                    terminals={p: row['source_terminal'] for p, row in leaves.items() if row['kind'] == 'source_terminal'},
                    future_information=sum(row['information_increment'] for row in leaves.values()))
        r['comparisons'] = {}
        for law in ('geometric_half', 'linear_mixture'):
            for base in ('unit', 'zero'):
                for kind in ('canonical', 'all_ties'):
                    a = r['outcomes'][law][kind]; b = r['outcomes'][base][kind]
                    r['comparisons'][law+'/'+base+'/'+kind] = dict(unknown='mixed terminal classes') if a['terminals'] or b['terminals'] else dict(forward=set_order(a['vectors'], b['vectors']), reverse=set_order(b['vectors'], a['vectors']))
        if not r['leaves'] or r['author_pushes'] != r['public_transitions']:
            raise ValueError('empty/incomplete event forest')
        r['complete'] = True
    except Exception as error:
        r['error'] = f'{type(error).__name__}: {error}'
    r['source_hashes_unchanged'] = all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == pin for p, pin in r['source_sha256'].items())
    save()
    print(json.dumps({k: v for k, v in r.items() if k not in ('source_sha256', 'root', 'children', 'replies', 'leaves', 'policies', 'outcomes', 'comparisons')}, default=str))
    print(json.dumps({law: {kind: dict(paths=len(row['paths']), quiet=len(row['vectors']), terminals=len(row['terminals']), future_information=row['future_information']) for kind, row in cases.items()} for law, cases in r['outcomes'].items()}))


if __name__ == '__main__': main()
