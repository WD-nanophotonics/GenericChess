"""Public complete-successor reuse on one fixed external reference."""
from collections import Counter
from fractions import Fraction as F
from pathlib import Path
from time import monotonic
import hashlib
import json
import sys
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from generic_chess.core.actions import action_promotion_target_id, action_target_square
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.transition import initial_state, legal_successors
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.public_goal_intervals import PublicGame
from scripts.chess_approx_static_inventory import ChessApproxStaticInventory
from scripts.chess_exact_contact_family import exact_chess_contact_intervals
from scripts.research_record import record_value, write_record
from scripts.audit_chess_multimode_source_replay import fen
OUT = ROOT/'docs/research/data/lichess_complete_children_20261006.json'
PRE = OUT.with_suffix('.selections.json')
OLD = 'docs/research/data/lichess_daily_preflight_20261006.json'
VIEW = 'docs/research/data/lichess_ep_view_20261006.json'
SOURCES = ('scripts/audit_lichess_complete_children.py', 'docs/research/LICHESS_COMPLETE_CHILD_PROTOCOL.md',
 'scripts/public_goal_intervals.py', 'scripts/chess_approx_static_inventory.py',
 'scripts/chess_exact_contact_family.py', 'scripts/research_record.py',
 'scripts/audit_chess_multimode_source_replay.py', OLD, VIEW,
 'generic_chess/core/transition.py', 'generic_chess/core/semantic_executor.py',
 'generic_chess/rules/western_chess.py', 'docs/research/data/chess_zero_target_correction_20261005.json')


def uci(action):
    source = action.from_square; target = action_target_square(action)
    if source is None or target is None: raise ValueError('native board action required')
    move = f'{chr(97+source.file)}{source.rank+1}{chr(97+target.file)}{target.rank+1}'
    promoted = action_promotion_target_id(action)
    return move+(promoted.lower() if promoted else '')


def main():
    if OUT.exists() or PRE.exists(): raise FileExistsError('fixed-reference child comparison never rerun')
    start = monotonic()
    r = dict(complete=False, public_transitions=0, enumerated_entries=0, compilations=0,
             runtime_pushes=0, new_author_pushes=0, new_author_legal_entries=0,
             source_table_queries=0, prefix_checks=0, children={}, source_checks={}, policies={},
             source_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})

    def save():
        r['seconds'] = monotonic()-start; write_record(OUT, r)

    def check():
        if monotonic()-start >= 30: raise TimeoutError('whole30sec cap')
        if r['public_transitions'] > 128 or r['enumerated_entries'] > 5000: raise ValueError('public128/list5000 cap')

    def table(state):
        result = {}
        for a in game.actions(state, check):
            r['enumerated_entries'] += 1; check()
            key = uci(a)
            if key in result: raise ValueError('action multiplicity collision')
            result[key] = a
        return result

    def position_check(state, author):
        check()
        if not author.is_valid() or author.board_fen() != fen(record_value(state)).split()[0]:
            raise ValueError('source/native board mismatch')
        if author.turn != (state.position.side_to_move == 0): raise ValueError('source actor mismatch')
        for name, slot in castle_slots.items():
            color = chess.WHITE if '_w_' in name else chess.BLACK
            expected = author.has_kingside_castling_rights(color) if name.endswith('_ks') else author.has_queenside_castling_rights(color)
            if bool(engine._slot_value(state.position, slot, 0)) != expected: raise ValueError('effective castle mismatch')
        ep = engine._slot_value(state.position, ep_slot, 0)
        if (None if ep is None else ep[0]+8*ep[1]) != author.ep_square: raise ValueError('forced EP mismatch')
        if author.promoted or any(p.promoted for p in state.position.board if p): raise ValueError('nonpromoted selected history scope required')

    save()
    try:
        old = json.loads((ROOT/OLD).read_text()); view = json.loads((ROOT/VIEW).read_text())
        if not view['complete'] or not view['source_hashes_unchanged'] or old['complete'] or not old['source_hashes_unchanged']:
            raise ValueError('fixed saved history/qualified EP view required')
        for original in (old, view):
            for p, digest in original['source_sha256'].items():
                if hashlib.sha256((ROOT/p).read_bytes()).hexdigest() != digest: raise ValueError('source drift')
        if any(row['promoted'] or row['automatic_terminal'] is not None for row in old['history']):
            raise ValueError('qualified ongoing nonpromoted ancestry required')
        if view['required_pure_child_events'] > 128: raise ValueError('prospective materialization bound')
        manifest = ROOT/'.local_agent/certificate_source/manifest-source-correction.json'
        if hashlib.sha256(manifest.read_bytes()).hexdigest() != old['manifest_sha256']: raise ValueError('manifest drift')
        author_path = manifest.parent/'python-chess/chess/__init__.py'
        if hashlib.sha256(author_path.read_bytes()).hexdigest() != old['author_sha256']: raise ValueError('author drift')
        sys.path.insert(0, str(author_path.parent.parent)); import chess
        if chess.__version__ != '1.11.2' or Path(chess.__file__).resolve() != author_path.resolve(): raise ValueError('pinned author required')
        compiled = compile_ruleset_for_execution(build_western_chess_ruleset()); r['compilations'] = 1
        engine = semantic_engine_for(compiled); game = PublicGame(compiled); root = initial_state(compiled)
        castle_slots = {p.name: p.slot_guards[0].slot_id for p in engine.ir.patterns if p.name.startswith('castle_')}
        if set(castle_slots) != {'castle_w_ks', 'castle_w_qs', 'castle_b_ks', 'castle_b_qs'}: raise ValueError('castle effect-binding scope')
        ep_slots = {e.slot_id for p in engine.ir.patterns for e in p.effects if e.kind == 'set_token'}
        if len(ep_slots) != 1: raise ValueError('single EP slot required')
        ep_slot = next(iter(ep_slots))
        ancestors = [chess.Board()]+[chess.Board(row['fen']) for row in old['history']]
        occurrences = Counter(' '.join(b.fen().split()[:4]) for b in ancestors)
        r['ancestor_count'] = len(ancestors); r['source_snapshot_constructions'] = len(ancestors)
        position_check(root, ancestors[0])
        for i, row in enumerate(old['history'], 1):
            choices = table(root)
            if row['uci'] not in choices: raise ValueError('selected PGN step missing locally')
            r['enumerated_entries'] += len(choices); r['public_transitions'] += 1; check()
            root = game.successor(root, choices[row['uci']]); position_check(root, ancestors[i])
            if root.ply_count != i or len(root.history) != i+1 or game.terminal(root).is_terminal:
                raise ValueError('complete ongoing Core history mismatch')
            r['prefix_checks'] += 1
        r['root'] = record_value(root); r['puzzle_id'] = view['puzzle_id']
        parent = ancestors[-1]; choices = table(root)
        if sorted(choices) != view['root_actions']: raise ValueError('ALL source/root actions mismatch')
        source_moves = list(parent.legal_moves); r['new_author_legal_entries'] = len(source_moves)
        if sorted(move.uci() for move in source_moves) != sorted(choices): raise ValueError('source snapshot/root action mismatch')
        r['public_transitions'] += len(choices); r['enumerated_entries'] += 2*len(choices); check()
        successors = legal_successors(root, compiled)
        if sorted(uci(a) for a, _ in successors) != sorted(choices): raise ValueError('public complete successor multiplicity mismatch')
        r['all_root_actions'] = [str(a) for a, _ in successors]
        known_moves = {move.uci(): move for move in source_moves}
        for action, child in successors:
            check(); move = uci(action); key = str(action)
            eb = parent.copy(stack=False); eb.push(known_moves[move]); r['new_author_pushes'] += 1
            position_check(child, eb)
            if child.ply_count != 53 or len(child.history) != 54: raise ValueError('child full Core history lost')
            occurrence = occurrences[' '.join(eb.fen().split()[:4])]+1
            if eb.halfmove_clock >= 150 or occurrence >= 5: raise ValueError('snapshot cannot determine automatic history draw')
            outcome = eb.outcome(claim_draw=False); local = game.terminal(child)
            if outcome is None:
                if local.is_terminal: raise ValueError('unmatched local terminal')
            else:
                mapping = {chess.Termination.CHECKMATE: 'checkmate', chess.Termination.STALEMATE: 'stalemate'}
                winner = None if outcome.winner is None else 0 if outcome.winner else 1
                if outcome.termination not in mapping or local.status.value != mapping[outcome.termination] or local.winner != winner:
                    raise ValueError('automatic source/local goal mismatch; no patched fallback')
            r['children'][key] = record_value(child)
            r['source_checks'][key] = dict(uci=move, author_stack_length=len(eb.move_stack),
                full_ancestry_occurrence_count=occurrence, author_halfmove_clock=eb.halfmove_clock,
                automatic_terminal=None if outcome is None else outcome.termination.name)
        if old['author_pushes']+r['new_author_pushes'] > 128 or view['cumulative_author_legal_entries']+r['new_author_legal_entries'] > 5000:
            raise ValueError('original cumulative author caps')
        weights = {law: {mode: lo for (_, mode), (lo, hi) in exact_chess_contact_intervals(law).items()}
                   for law in ('geometric_half', 'linear_mixture')}
        weights['unit'] = {mode: F(1) for mode in 'PNBRQ'}
        for law, w in weights.items():
            evaluator = ChessApproxStaticInventory(w); scores = {}
            for action, child in successors:
                if game.terminal(child).is_terminal: raise ValueError('all actual child ongoing required for this integer comparison')
                score = evaluator.evaluate(child); scores[str(action)] = score if child.position.side_to_move == 0 else -score
            best = max(scores.values()); ties = sorted(k for k, value in scores.items() if value == best)
            r['policies'][law] = dict(selected=ties[0], tie_set=ties, scores=scores, integer_weights=evaluator.weights)
        write_record(PRE, r); r['precomparison_sha256'] = hashlib.sha256(PRE.read_bytes()).hexdigest()
        answer = view['reference_first_answer']
        r['reference_comparison'] = {law: dict(advertised_answer=answer,
            canonical_matches=r['source_checks'][p['selected']]['uci'] == answer,
            answer_in_full_ties=any(r['source_checks'][key]['uci'] == answer for key in p['tie_set']),
            selected_uci=r['source_checks'][p['selected']]['uci']) for law, p in r['policies'].items()}
        r.update(cumulative_author_pushes=old['author_pushes']+r['new_author_pushes'],
                 cumulative_author_legal_entries=view['cumulative_author_legal_entries']+r['new_author_legal_entries'], complete=True)
        r['not_proved'] = 'independent WDL/solution proof, natural performance, unseen corpus, broader physical or production adoption'
    except Exception as error: r['error'] = f'{type(error).__name__}: {error}'
    r['source_hashes_unchanged'] = all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == digest for p, digest in r['source_sha256'].items())
    save()
    print(json.dumps({k: v for k, v in r.items() if k not in ('source_sha256', 'root', 'children', 'source_checks', 'policies', 'all_root_actions')}))


if __name__ == '__main__': main()
