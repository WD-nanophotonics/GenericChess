"""Repeatable Chess development comparisons and short games, using production search.

This entry has no oracle, training, extra worker or exact-WDL prerequisite.
Reference-answer misses are not automatically proven tactical mistakes.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter, process_time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.ai.alphabeta.search import run_root_search
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.identity import position_identity_key
from generic_chess.core.movegen import iter_legal_actions
from generic_chess.core.position import GameState, HistoryRecord
from generic_chess.core.terminal import TerminalResult, TerminalStatus, terminal_result
from generic_chess.core.transition import apply_action
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_f24f_western_chess_perft import position_from_fen
from scripts.audit_lichess_complete_children import uci
from scripts.chess_approx_static_inventory import ChessApproxStaticInventory
from scripts.chess_exact_contact_family import exact_chess_contact_intervals
from scripts.research_record import record_value, write_record

POLICIES = ('geometric_half', 'linear_mixture', 'unit')


class DevelopmentInventory(ChessApproxStaticInventory):
    """Leaf prices vary; capture-order prices stay common across all methods."""
    def __init__(self, weights):
        super().__init__(weights)
        common = {m: lo for (_, m), (lo, hi) in exact_chess_contact_intervals('geometric_half').items()}
        self.order_values = ChessApproxStaticInventory(common).weights

    def type_value(self, type_id):
        return 0 if type_id == 'K' else self.order_values[type_id]

    def capture_order_value(self, moving_piece, captured_piece):
        return self.type_value(captured_piece.current_type_id)*10-self.type_value(moving_piece.current_type_id)//10


class SharedDynamicInventory(DevelopmentInventory):
    """Use existing mobility/anchor terms without adding a learned price table."""
    def __init__(self, weights, compiled):
        super().__init__(weights)
        from generic_chess.ai.evaluation.config import EvaluationConfig, config_hash
        from generic_chess.ai.evaluation.evaluator import Evaluator
        from generic_chess.ai.evaluation.profile import RuleSetEvaluationProfile
        config = EvaluationConfig()
        zero = {pt.type_id: 0 for pt in compiled.piece_types}
        profile = RuleSetEvaluationProfile(compiled.ruleset_fingerprint, 1,
            'development-shared-dynamic', config_hash(config), {}, 0, zero, zero, zero)
        self.dynamic = Evaluator(compiled, profile, config)

    def evaluate(self, state):
        from generic_chess.ai.evaluation.config import MAX_STATIC_EVAL
        # Existing weights2/5 retain their original units with Queen=1000.
        # Material Queen=100000 here, so scale the shared residual by100.
        value = super().evaluate(state)+100*self.dynamic.evaluate(state)
        if abs(value) >= MAX_STATIC_EVAL:
            raise ValueError('dynamic/static mate separation failed')
        return value


def evaluator(policy, *, compiled=None, dynamic=False):
    if policy not in POLICIES:
        raise ValueError(f'unsupported candidate: {policy}')
    weights = ({m: Fraction(1) for m in 'PNBRQ'} if policy == 'unit' else
               {m: lo for (_, m), (lo, hi) in exact_chess_contact_intervals(policy).items()})
    if dynamic:
        if compiled is None:
            raise ValueError('compiled rules required for dynamic terms')
        return SharedDynamicInventory(weights, compiled)
    return DevelopmentInventory(weights)


def root_from_fen(fen, compiled):
    # FEN cannot restore played repetition history. Use explicit fresh snapshots,
    # never silently discard an encoded nonzero halfmove/fullmove counter.
    fields = fen.split()
    if len(fields) != 6 or fields[4:] != ['0', '1']:
        raise ValueError('fresh FEN snapshot requires counters 0 1; played state needs history')
    if fields[1] not in ('w', 'b'):
        raise ValueError('invalid side to move')
    position = position_from_fen(fen, compiled)
    if len(position.board) != 64:
        raise ValueError('8x8 Chess board required')
    key = position_identity_key(position, compiled)
    state = GameState(position, 0, ((key, 1),), TerminalResult(TerminalStatus.ONGOING),
                      (HistoryRecord(key, -1, '', False),))
    state = replace(state, terminal_status=terminal_result(state, compiled))
    evaluator('unit').evaluate(state)  # supported material/anchor scope
    return state


def search_move(state, compiled, policy, limits, *, provider=None, ordering=False, use_tt=False, dynamic=False, tuning=None, _history_witnesses=None):
    evaluation = evaluator(policy, compiled=compiled, dynamic=dynamic)
    stats = SearchStatistics()
    wall, cpu = perf_counter(), process_time()
    action, score, pv, reason = run_root_search(
        state, compiled, evaluation, TranspositionTable(max_entries=65536 if use_tt else 16), limits,
        None, stats, use_tt=use_tt, use_ordering=ordering,
        tuning=tuning if tuning is not None else SearchTuning(use_root_tactical=False),
        _history_witnesses=_history_witnesses, legal_binding_provider=provider)
    return action, dict(policy=policy, move=None if action is None else uci(action),
                        score=score, pv=[uci(a) for a in pv], reason=reason,
                        wall_seconds=perf_counter()-wall, cpu_seconds=process_time()-cpu,
                        evaluation_calls=evaluation.calls, statistics=asdict(stats),
                        integer_weights=evaluation.weights)


def compare_case(case, compiled, limits, *, provider=None, ordering=False, use_tt=False, dynamic=False, tuning=None):
    state = root_from_fen(case['fen'], compiled)
    if state.terminal_status.is_terminal:
        raise ValueError(f"terminal tactical root: {case['id']}")
    legal = {uci(a): a for a in iter_legal_actions(state, compiled)}
    accepted = set(case['accepted_uci'])
    if not accepted or not accepted <= legal.keys():
        raise ValueError(f"invalid declared answers: {case['id']}")
    initial = record_value(state)
    rows = []
    for policy in POLICIES:
        try:
            action, row = search_move(state, compiled, policy, limits, provider=provider,
                                      ordering=ordering, use_tt=use_tt, dynamic=dynamic, tuning=tuning)
            row['legal'] = row['move'] in legal
            row['completed'] = (row['legal'] and row['reason'] == 'completed_depth'
                                and row['statistics']['completed_depth'] == limits.max_depth
                                and not row['statistics']['root_scan_used_fallback'])
            row['reference_hit'] = (row['move'] in accepted) if row['completed'] else None
            row['state_preserved'] = record_value(state) == initial
            if not row['state_preserved']:
                raise ValueError('search mutated public root')
        except Exception as exc:
            row = dict(policy=policy, completed=False, reference_hit=None,
                       error=f'{type(exc).__name__}: {exc}')
        rows.append(row)
    return dict(id=case['id'], fen=case['fen'], accepted_uci=sorted(accepted),
                answer_basis=case['answer_basis'], answer_scope=case.get('answer_scope', 'reference'),
                root_legal_count=len(legal), rows=rows)


def comparison_summary(cases):
    methods = {}
    for policy in POLICIES:
        rows = [next(r for r in c['rows'] if r['policy'] == policy) for c in cases]
        complete = [r for r in rows if r['completed']]
        methods[policy] = dict(cases=len(rows), completed=len(complete),
            execution_failures=len(rows)-len(complete), reference_hits=sum(r['reference_hit'] for r in complete),
            reference_misses=sum(not r['reference_hit'] for r in complete),
            wall_seconds=sum(r.get('wall_seconds', 0) for r in rows),
            cpu_seconds=sum(r.get('cpu_seconds', 0) for r in rows),
            nodes=sum(r.get('statistics', {}).get('nodes', 0) for r in rows))
    paired = {}
    for other in ('unit', 'linear_mixture'):
        count = dict(paired_completed=0, candidate_only_hit=0, other_only_hit=0,
                     both_hit=0, neither_hit=0, different_moves=0)
        for case in cases:
            by = {r['policy']: r for r in case['rows']}
            a, b = by['geometric_half'], by[other]
            if not a['completed'] or not b['completed']:
                continue
            count['paired_completed'] += 1
            count['different_moves'] += a['move'] != b['move']
            key = ('both_hit' if a['reference_hit'] and b['reference_hit'] else
                   'candidate_only_hit' if a['reference_hit'] else
                   'other_only_hit' if b['reference_hit'] else 'neither_hit')
            count[key] += 1
        paired[other] = count
    return dict(methods=methods, paired=paired,
                interpretation='Reference-answer agreement, not proof of tactical error, Elo or generic strength')


def play_game(fen, compiled, white, black, limits, max_plies, save_move=None, *, provider=None, ordering=False, use_tt=False, dynamic=False, external=None, tuning=None):
    state = root_from_fen(fen, compiled)
    # These are our actual Core-produced positions, as in GameSession. Retain
    # them across played moves; never replace history with a fresh FEN snapshot.
    witnesses = [state.position]
    policies = (white, black)
    moves = []
    result = dict(white=white, black=black, initial_fen=fen, moves=moves,
                  end='ply_limit', winner=None, finished=False)
    for _ in range(max_plies):
        if state.terminal_status.is_terminal:
            break
        legal = set(iter_legal_actions(state, compiled))
        policy = policies[state.position.side_to_move]
        if policy == 'uci_reference':
            if external is None:
                raise ValueError('external player required')
            move, row = external.choose()
            action = next((a for a in legal if uci(a) == move), None)
        else:
            action, row = search_move(state, compiled, policy, limits,
                                      provider=provider, ordering=ordering, use_tt=use_tt, dynamic=dynamic,
                                      tuning=tuning, _history_witnesses=tuple(witnesses))
        row['ply'] = state.ply_count
        row['side'] = state.position.side_to_move
        row['completed'] = (action in legal and (row['reason'] == 'uci_bestmove' or reason_complete(row, limits)))
        row['legal'] = action in legal
        moves.append(row)
        if action not in legal:
            result['end'] = 'execution_failure'
            break
        # Fallback choices are playable but recorded separately from completed searches.
        state = apply_action(state, action, compiled)
        witnesses.append(state.position)
        if external:
            external.push(uci(action), state)
        if state.terminal_status != terminal_result(state, compiled):
            raise ValueError('stale terminal after played move')
        if save_move:
            save_move(result)
    if state.terminal_status.is_terminal:
        result.update(end=state.terminal_status.status.value, winner=state.terminal_status.winner, finished=True)
    result['final_state'] = record_value(state)
    result['plies_attempted'] = len(moves)
    result['plies_played'] = sum(r['legal'] for r in moves)
    result['incomplete_searches'] = sum(not r['completed'] for r in moves)
    return result


def reason_complete(row, limits):
    return (row['reason'] == 'completed_depth'
            and row['statistics']['completed_depth'] == limits.max_depth
            and not row['statistics']['root_scan_used_fallback'])


class UciOpponent:
    """Mechanical local UCI transport, no model or account worker."""
    def __init__(self, engine, fen, nodes):
        import chess, chess.engine
        self.engine = engine
        self.board = chess.Board(fen)
        self.limit = chess.engine.Limit(nodes=nodes, time=1)
        self.game = object()  # fresh game/hash per game, retained within it

    def choose(self):
        from chess.engine import INFO_ALL
        wall, cpu = perf_counter(), process_time()
        result = self.engine.play(self.board, self.limit, game=self.game, info=INFO_ALL)
        move = result.move.uci() if result.move else None
        return move, dict(policy='uci_reference', move=move, reason='uci_bestmove', score=None,
            wall_seconds=perf_counter()-wall, controller_cpu_seconds=process_time()-cpu,
            opponent_nodes=result.info.get('nodes'), opponent_depth=result.info.get('depth'),
            pv=[m.uci() for m in result.info.get('pv', ())],
            statistics={})

    def push(self, move, local):
        self.board.push_uci(move)
        import chess
        if self.board.turn != (local.position.side_to_move == 0):
            raise ValueError('external/local actor mismatch')
        observed = {i: (p.current_type_id, p.owner) for i, p in enumerate(local.position.board) if p}
        expected = {i: (chess.piece_symbol(p.piece_type).upper(), 0 if p.color else 1)
                    for i, p in self.board.piece_map().items()}
        if observed != expected:
            raise ValueError('external/local played board mismatch')
        # Same canonical Western slot order as position_from_fen. Compare raw
        # EP, including targets with no eligible capture, rather than FEN's
        # optional legal-only EP serialization.
        names = sorted(('b_ks', 'b_qs', 'ep_target', 'w_ks', 'w_qs'))
        aux = dict(local.position.aux_state)
        for name, color, kingside in (
                ('w_ks', True, True), ('w_qs', True, False),
                ('b_ks', False, True), ('b_qs', False, False)):
            observed_right = bool(aux.get((names.index(name), -1), 1))
            expected_right = (self.board.has_kingside_castling_rights(color) if kingside
                              else self.board.has_queenside_castling_rights(color))
            if observed_right != expected_right:
                raise ValueError(f'external/local {name} mismatch')
        ep = aux.get((names.index('ep_target'), -1))
        local_ep = None if ep is None else ep[1]*8+ep[0]
        if local_ep != self.board.ep_square:
            raise ValueError('external/local EP mismatch')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=('compare', 'play', 'play-uci', 'reference'))
    p.add_argument('--suite', type=Path, required=True, help='declared JSON cases with FEN and existing answers')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--depth', type=int, default=2)
    p.add_argument('--nodes', type=int, default=2048)
    p.add_argument('--seconds', type=float, default=1)
    p.add_argument('--qdepth', type=int, default=0)
    p.add_argument('--qhard', type=int, default=8, help='separate check-evasion hard limit')
    p.add_argument('--native-legality', action='store_true', help='use the existing production native provider')
    p.add_argument('--ordering', action='store_true', help='existing orderer with shared frozen capture prices')
    p.add_argument('--tt', action='store_true', help='fresh per-search production TT, same capacity65536 for all methods')
    p.add_argument('--dynamic', action='store_true', help='shared existing mobility/anchor terms; no coefficient fitting')
    p.add_argument('--pvs', action='store_true', help='existing principal variation search; explicit common search ablation')
    p.add_argument('--engine', type=Path, help='optional existing local UCI executable for play-uci')
    p.add_argument('--uci-python', type=Path, help='optional local python-chess import root; otherwise use installed package')
    p.add_argument('--opponent-nodes', type=int, default=50000)
    p.add_argument('--comparison', type=Path, help='saved compare report for optional independent reference')
    p.add_argument('--reference-cache', type=Path, help='reuse identical pinned engine/condition/FEN child references')
    p.add_argument('--max-plies', type=int, default=40)
    args = p.parse_args(argv)
    if args.depth < 1 or args.nodes < 1 or args.qdepth < 0 or args.qhard < args.qdepth or not 0 < args.seconds <= 60 or not 1 <= args.max_plies <= 200:
        p.error('finite positive search conditions required; <=60 sec/move, <=200 plies')
    if args.output.exists():
        p.error('output exists; preserve prior results and select another path')
    if args.mode in ('play-uci', 'reference') and (args.engine is None or args.opponent_nodes <= 0):
        p.error('UCI modes require an engine and positive opponent node limit')
    if args.mode == 'reference' and args.comparison is None:
        p.error('reference requires a saved comparison')
    suite_bytes = args.suite.read_bytes()
    suite = json.loads(suite_bytes)
    if not suite['cases'] or len({c['id'] for c in suite['cases']}) != len(suite['cases']):
        p.error('nonempty uniquely identified suite required')
    limits = SearchLimits(max_depth=args.depth, max_nodes=args.nodes, max_time_seconds=args.seconds,
                          quiescence_max_depth=args.qdepth, quiescence_hard_max_depth=args.qhard,
                          quiescence_max_nodes=args.nodes, deterministic=True)
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    tuning = SearchTuning(use_root_tactical=False, use_pvs=args.pvs)
    provider = None
    if args.native_legality:
        from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
        provider = NativeSemanticLegalityProvider.try_create(compiled, strict=True)
        if provider is None:
            p.error('native provider unavailable; build the supported extension or omit --native-legality')
    report = dict(mode=args.mode, complete=False, suite_sha256=hashlib.sha256(suite_bytes).hexdigest(),
                  producer_sha256={path: hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
                      for path in ('scripts/chess_development.py', 'scripts/chess_approx_static_inventory.py',
                                   'scripts/chess_exact_contact_family.py', 'scripts/research_record.py',
                                   'generic_chess/ai/alphabeta/search.py', 'generic_chess/ai/alphabeta/quiescence.py')},
                  suite_source=suite.get('source'), scope=suite['scope'], limits=asdict(limits),
                  tuning=asdict(tuning), use_tt=args.tt, use_ordering=args.ordering,
                  ruleset_fingerprint=compiled.ruleset_fingerprint, cases=[], games=[])
    report['history_handoff'] = ('retained Core-produced played positions' if args.mode in ('play','play-uci')
                                else 'existing fresh-root search import')
    report['legality_backend'] = 'production_native' if provider is not None else 'python_reference'
    report['ordering_weights'] = evaluator('unit').order_values if args.ordering else None
    report['evaluation_terms'] = ('material + shared existing mobility2/anchor5; residual x100; no promotion bonus'
                                  if args.dynamic else 'material only')
    if provider is not None:
        from generic_chess.native import native_version
        import generic_chess._native_core as extension
        report['native'] = dict(version=native_version(), compile_seconds=provider.compile_seconds,
                                binary_sha256=hashlib.sha256(Path(extension.__file__).read_bytes()).hexdigest())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_record(args.output, report)
    try:
        if args.mode == 'compare':
            for case in suite['cases']:
                report['cases'].append(compare_case(case, compiled, limits, provider=provider,
                                                   ordering=args.ordering, use_tt=args.tt, dynamic=args.dynamic, tuning=tuning))
                report['summary'] = comparison_summary(report['cases'])
                write_record(args.output, report)
                print(case['id'], report['summary']['paired'], flush=True)
        elif args.mode == 'play':
            for case in suite['cases']:
                for other in ('unit', 'linear_mixture'):
                    for white, black in (('geometric_half', other), (other, 'geometric_half')):
                        def save(game):
                            report['active_game'] = dict(id=case['id'], **game)
                            write_record(args.output, report)
                        game = play_game(case['fen'], compiled, white, black, limits, args.max_plies, save,
                                         provider=provider, ordering=args.ordering, use_tt=args.tt, dynamic=args.dynamic, tuning=tuning)
                        report.pop('active_game', None)
                        report['games'].append(dict(id=case['id'], **game))
                        write_record(args.output, report)
                        print(case['id'], white, black, game['end'], game['plies_played'], flush=True)
        elif args.mode == 'play-uci':
            if args.uci_python:
                sys.path.insert(0, str(args.uci_python.resolve()))
            import chess.engine
            with chess.engine.SimpleEngine.popen_uci(str(args.engine.resolve()), timeout=10) as engine:
                engine.configure({'Threads': 1, 'Hash': 16, 'UCI_LimitStrength': True, 'UCI_Elo': 1320})
                report['opponent'] = dict(id=engine.id, threads=1, hash_mib=16, configured_elo=1320,
                    nodes=args.opponent_nodes, seconds_fuse=1,
                    binary_sha256=hashlib.sha256(args.engine.read_bytes()).hexdigest(),
                    scope='limited-strength setting with bounded search, not a calibrated rating claim')
                for case in suite['cases']:
                    for policy in POLICIES:
                        for white, black in ((policy, 'uci_reference'), ('uci_reference', policy)):
                            def save(game):
                                report['active_game'] = dict(id=case['id'], **game)
                                write_record(args.output, report)
                            external = UciOpponent(engine, case['fen'], args.opponent_nodes)
                            game = play_game(case['fen'], compiled, white, black, limits, args.max_plies, save,
                                provider=provider, ordering=args.ordering, use_tt=args.tt,
                                dynamic=args.dynamic, external=external, tuning=tuning)
                            report.pop('active_game', None)
                            report['games'].append(dict(id=case['id'], **game))
                            write_record(args.output, report)
                            print(policy, white, black, game['end'], game['plies_played'], flush=True)
        else:
            if args.uci_python:
                sys.path.insert(0, str(args.uci_python.resolve()))
            import chess, chess.engine
            inputs = args.comparison.read_bytes()
            comparison = json.loads(inputs)
            if len(comparison['cases']) != len(suite['cases']):
                raise ValueError('reference comparison/suite case count differs')
            if [(c['id'], c['fen'], c['accepted_uci']) for c in comparison['cases']] != [
                    (c['id'], c['fen'], sorted(c['accepted_uci'])) for c in suite['cases']]:
                raise ValueError('reference comparison/suite cases or answers differ')
            binary_hash = hashlib.sha256(args.engine.read_bytes()).hexdigest()
            conditions = dict(threads=1, hash_mib=16, nodes_per_child=args.opponent_nodes, fresh_game_each_child=True)
            cache = {}
            if args.reference_cache:
                cached = json.loads(args.reference_cache.read_bytes())
                cached_hash = cached.get('acquisition', {}).get('binary_sha256', cached.get('binary_sha256'))
                if cached_hash != binary_hash or cached['conditions'] != conditions:
                    raise ValueError('reference cache engine/conditions mismatch')
                cache = {c['fen']: c['references'] for c in cached['cases']}
                report['reference_cache_sha256'] = hashlib.sha256(args.reference_cache.read_bytes()).hexdigest()
            report.update(comparison_sha256=hashlib.sha256(inputs).hexdigest(), binary_sha256=binary_hash,
                          conditions=conditions, new_analyses=0, cached_analyses=0,
                          reference_scope='limited standard-Chess child scores, not exact regret/WDL/Elo or local-goal equivalence')
            with chess.engine.SimpleEngine.popen_uci(str(args.engine.resolve()), timeout=10) as engine:
                engine.configure({'Threads':1, 'Hash':16})
                report['engine_id'] = engine.id
                for case in comparison['cases']:
                    board = chess.Board(case['fen'])
                    keys = sorted(set(case['accepted_uci']) | {r['move'] for r in case['rows'] if r['completed']})
                    row = dict(id=case['id'], fen=case['fen'], accepted_uci=case['accepted_uci'], references={})
                    report['cases'].append(row)
                    for move in keys:
                        if move in cache.get(case['fen'], {}):
                            row['references'][move] = dict(cache[case['fen']][move], cached=True)
                            report['cached_analyses'] += 1
                        else:
                            child = board.copy(stack=True)
                            child.push_uci(move)
                            info = engine.analyse(child, chess.engine.Limit(nodes=args.opponent_nodes), game=object())
                            score = info['score'].pov(board.turn)
                            row['references'][move] = dict(cp=score.score(), mate=score.mate(), score=str(score),
                                nodes=info.get('nodes'), depth=info.get('depth'), seconds=info.get('time'),
                                pv=[m.uci() for m in info.get('pv', [])], cached=False)
                            report['new_analyses'] += 1
                        write_record(args.output, report)
                    print(case['id'], report['new_analyses'], report['cached_analyses'], flush=True)
        report['complete'] = True
    except (Exception, KeyboardInterrupt) as exc:
        report['error'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        write_record(args.output, report)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
