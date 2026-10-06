"""Actual five-mode search integration, preserving full legal context."""
from dataclasses import asdict
from fractions import Fraction as F
from pathlib import Path
from time import monotonic
import hashlib
import json
import sys
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.ai.alphabeta.search import run_root_search
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from scripts.chess_approx_static_inventory import ChessApproxStaticInventory, SCALE
from scripts.chess_exact_contact_family import exact_chess_contact_intervals
from scripts.public_goal_intervals import PublicGame
from scripts.research_state_replay import read_game_state
from scripts.research_record import record_value, write_record
from scripts.audit_chess_multimode_source_replay import fen, uci, MANIFEST_SHA
OUT = ROOT/'docs/research/data/chess_approx_static_search_20261006.json'
FOREST = 'docs/research/data/chess_adjudicated_exchange_20261006.json'
SOURCES = ('scripts/audit_chess_approx_static_search.py', 'scripts/chess_approx_static_inventory.py',
 'docs/research/CHESS_APPROX_STATIC_SEARCH_PROTOCOL.md', 'scripts/chess_exact_contact_family.py',
 'scripts/public_goal_intervals.py', 'scripts/research_state_replay.py', 'scripts/research_record.py',
 'scripts/audit_chess_multimode_source_replay.py', FOREST, 'generic_chess/core/search_runtime.py',
 'generic_chess/core/semantic_executor.py', 'generic_chess/core/transition.py',
 'generic_chess/rules/western_chess.py', 'generic_chess/ai/alphabeta/search.py',
 'generic_chess/ai/alphabeta/tuning.py', 'docs/research/data/chess_zero_target_correction_20261005.json')


def main():
    if OUT.exists(): raise FileExistsError('search integration never rerun')
    start = monotonic()
    r = dict(complete=False, compilations=0, public_transitions=0, runtime_pushes=0,
             runtime_pops=0, returned_actions=0, author_pushes=0, author_legal_entries=0,
             source_queries=0, searches=[], opening_children={}, opening_source=[],
             unmetered_prefix=dict(compilations=1, public_transitions=1,
                                  returned_list_and_membership_entries=40,
                                  elapsed_seconds=None, semantic_candidates=None),
             source_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    push, pop, legal = SearchPathRuntime.push, SearchPathRuntime.pop, SearchPathRuntime.legal_actions
    stack = []; current = None; saved = {}

    def save():
        r['metered_main_seconds'] = monotonic()-start; write_record(OUT, r)

    def check():
        if monotonic()-start >= 15: raise TimeoutError('new main15sec cap')
        if r['runtime_pushes']+r['public_transitions']+1 > 128:
            raise ValueError('combined materialization cap incl prefix')
        if r['returned_actions']+40 > 5000: raise ValueError('returned/member cap incl prefix')

    def counted_legal(self, *args, **kwargs):
        check(); result = legal(self, *args, **kwargs)
        r['returned_actions'] += len(result); check(); return result

    def counted_push(self, action, *args, **kwargs):
        check()
        if r['runtime_pushes']+r['public_transitions']+1 >= 128: raise ValueError('runtime push cap')
        r['runtime_pushes'] += 1; result = push(self, action, *args, **kwargs)
        stack.append(str(action))
        if len(stack) != 1: raise ValueError('frozen depth1 only')
        expected = saved[stack[0]]
        if (record_value(self.position) != expected['position'] or self.ply_count != expected['ply_count']
                or record_value(self.terminal_status) != expected['terminal_status']):
            raise ValueError('actual runtime child differs from complete public record')
        current['visited'].append(str(action)); return result

    def counted_pop(self, *args, **kwargs):
        result = pop(self, *args, **kwargs); stack.pop(); r['runtime_pops'] += 1; return result

    save()
    try:
        raw = json.loads((ROOT/FOREST).read_text())
        if not raw['complete'] or not raw['source_hashes_unchanged']: raise ValueError('qualified saved forest required')
        for p, digest in raw['source_sha256'].items():
            if hashlib.sha256((ROOT/p).read_bytes()).hexdigest() != digest: raise ValueError('forest drift')
        compiled = compile_ruleset_for_execution(build_western_chess_ruleset()); r['compilations'] = 1
        game = PublicGame(compiled); engine = semantic_engine_for(compiled)
        small = read_game_state(raw['root']); opening = initial_state(compiled)
        if game.terminal(small).is_terminal or game.terminal(opening).is_terminal: raise ValueError('ongoing roots required')
        r['opening_root'] = record_value(opening)
        table = {}
        for a in game.actions(opening, check):
            key = str(a)
            if key in table: raise ValueError('canonical collision')
            table[key] = a; r['returned_actions'] += 1; check()
        r['opening_actions'] = list(table)
        for key, a in table.items():
            check(); r['public_transitions'] += 1; r['returned_actions'] += len(table); check()
            r['opening_children'][key] = record_value(game.successor(opening, a))
        if len(table) != 20: raise ValueError('full native initial action set not20')
        manifest = ROOT/'.local_agent/certificate_source/manifest-source-correction.json'
        if hashlib.sha256(manifest.read_bytes()).hexdigest() != MANIFEST_SHA: raise ValueError('manifest drift')
        entry = next(e for e in json.loads(manifest.read_text())['source_files'] if e['name'] == 'chess/__init__.py')
        author = manifest.parent/'python-chess'/entry['name']
        if author.stat().st_size != entry['bytes'] or hashlib.sha256(author.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('author drift')
        sys.path.insert(0, str(author.parent.parent)); import chess
        if chess.__version__ != '1.11.2' or Path(chess.__file__).resolve() != author.resolve(): raise ValueError('pinned author required')
        r.update(author_sha256=entry['sha256'], manifest_sha256=MANIFEST_SHA)
        board = chess.Board()
        moves = sorted(move.uci() for move in board.legal_moves); r['author_legal_entries'] = len(moves)
        if sorted(uci(k) for k in table) != moves: raise ValueError('complete initial source action mismatch')
        castles = {p.name: p.slot_guards[0].slot_id for p in engine.ir.patterns if p.name.startswith('castle_')}
        if set(castles) != {'castle_w_ks', 'castle_w_qs', 'castle_b_ks', 'castle_b_qs'}: raise ValueError('castle slot binding failed')
        ep_slots = {e.slot_id for p in engine.ir.patterns for e in p.effects if e.kind == 'set_token'}
        if len(ep_slots) != 1: raise ValueError('EP effect binding failed')
        ep_slot = next(iter(ep_slots)); r['castle_slot_bindings'] = castles; r['ep_slot'] = ep_slot
        for key, stored in r['opening_children'].items():
            check(); eb = board.copy(stack=True); eb.push_uci(uci(key)); r['author_pushes'] += 1
            state = read_game_state(stored)
            if not eb.is_valid() or eb.board_fen() != fen(stored).split()[0] or eb.turn != (state.position.side_to_move == 0):
                raise ValueError('opening source board/actor invalid')
            rights = {name: engine._slot_value(state.position, slot, 0) for name, slot in castles.items()}
            if any(value != 1 for value in rights.values()) or not eb.has_kingside_castling_rights(chess.WHITE) or not eb.has_queenside_castling_rights(chess.WHITE) or not eb.has_kingside_castling_rights(chess.BLACK) or not eb.has_queenside_castling_rights(chess.BLACK):
                raise ValueError('effective castling rights not preserved')
            ep = engine._slot_value(state.position, ep_slot, 0)
            expected_ep = None if ep is None else ep[0]+8*ep[1]
            if expected_ep != eb.ep_square: raise ValueError('opening EP mismatch')
            if state.ply_count != len(eb.move_stack) or len(state.history) != 2:
                raise ValueError('opening fresh history mismatch')
            if game.terminal(state).is_terminal or eb.outcome(claim_draw=False) is not None:
                raise ValueError('unexpected local/author child terminal')
            r['opening_source'].append(dict(action=key, effective_rights=rights, ep_target=ep))
        weights = {law: {mode: lo for (loc, mode), (lo, hi) in exact_chess_contact_intervals(law).items()}
                   for law in ('geometric_half', 'linear_mixture')}
        weights['unit'] = {mode: F(1) for mode in 'PNBRQ'}
        SearchPathRuntime.push = counted_push; SearchPathRuntime.pop = counted_pop; SearchPathRuntime.legal_actions = counted_legal
        for scope, root, children, laws in (('small_exposed', small, raw['children'], tuple(weights)),
                                          ('initial_full_rights', opening, r['opening_children'], ('geometric_half', 'unit'))):
            saved = children
            for law in laws:
                check(); evaluator = ChessApproxStaticInventory(weights[law])
                values = {}
                for key, child in children.items():
                    s = read_game_state(child)
                    signed = evaluator.evaluate(s); values[key] = signed if s.position.side_to_move == 0 else -signed
                best = max(values.values()); ties = sorted(k for k, v in values.items() if v == best)
                evaluator.calls = 0
                current = dict(scope=scope, law=law, complete=False, reference_score=best,
                               reference_ties=ties, child_scores=values, integer_weights=evaluator.weights, visited=[])
                r['searches'].append(current); save()
                stats = SearchStatistics()
                a, score, pv, reason = run_root_search(root, compiled, evaluator, TranspositionTable(max_entries=16),
                    SearchLimits(max_depth=1, max_nodes=128, max_time_seconds=max(0.001, 15-(monotonic()-start)), quiescence_max_depth=0),
                    None, stats, use_tt=False, use_ordering=False, tuning=SearchTuning(use_root_tactical=False))
                current.update(selected=str(a), score=score, pv=[str(x) for x in pv], reason=reason,
                               statistics=asdict(stats), evaluation_calls=evaluator.calls)
                if reason != 'completed_depth' or stats.completed_depth != 1 or stats.qnodes != 0 or stats.root_scan_used_fallback:
                    raise ValueError('complete depth1/q0 search required')
                if score != best or str(a) not in ties or stack or set(current['visited']) != set(children):
                    raise ValueError('search/full-table score, ties or coverage mismatch')
                current['complete'] = True; save()
        if r['runtime_pushes'] != r['runtime_pops']: raise ValueError('unbalanced runtime mutation')
        check(); r['complete'] = True
        r['not_proved'] = 'strength, source automatic-draw runtime adapter, full auxiliary virtual equivalence or new performance'
    except Exception as error: r['error'] = f'{type(error).__name__}: {error}'
    finally:
        SearchPathRuntime.push, SearchPathRuntime.pop, SearchPathRuntime.legal_actions = push, pop, legal
    r['source_hashes_unchanged'] = all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == digest for p, digest in r['source_sha256'].items())
    save()
    print(json.dumps(record_value({k: v for k, v in r.items() if k not in ('source_sha256', 'searches', 'opening_children', 'opening_root', 'opening_source')})))
    print(json.dumps([{k: v for k, v in row.items() if k in ('scope', 'law', 'complete', 'selected', 'score', 'reference_ties', 'evaluation_calls')} for row in r['searches']]))


if __name__ == '__main__': main()
