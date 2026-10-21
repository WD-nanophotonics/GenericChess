"""Reproducible public-AlphaBeta cost probe on generated rules in explicit IR.

Results go to an ignored artifact path. This is not the generator's default
legacy carrier, a strength test, or a changed product profile. All variants use
its actual default evaluator/TT/main ordering/root scan; ordered changes q order
only. Attack-backend overrides reuse the exact default price profile, but may
change evaluation semantics outside qualified cohorts. Terminal/censored roots
and incomplete searches remain in the output.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
import hashlib
import random
import time
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import ruleset_to_dict, ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from scripts.research_record import record_value, write_record
import json


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--input', type=Path, help='Existing probe JSON; replay its canonical roots instead of resampling')
    ap.add_argument('--seed-start', type=int, default=2026102121)
    ap.add_argument('--seed-count', type=int, default=8)
    ap.add_argument('--prefixes', type=int, nargs='+', default=[0, 12])
    ap.add_argument('--variants', choices=['legal', 'availability', 'check', 'all', 'ordered', 'ordered_evasions'],
                    nargs='+', default=['all', 'ordered'])
    ap.add_argument('--evaluation-backend', choices=['default', 'semantic_core', 'semantic_native'],
                    default='default', help='Existing attack evaluator with the exact default static profile; may change score semantics')
    ap.add_argument('--stop-after-root-win', action='store_true',
                    help='Existing opt-in any-completed-win objective; does not seek shortest mate/full depth')
    ap.add_argument('--allow-hybrid', action='store_true')
    ap.add_argument('--require-no-opening-win-in-one', action='store_true',
                    help='Existing optional generator preference; changes the accepted rule distribution')
    ap.add_argument('--rounds', type=int, default=1)
    ap.add_argument('--seconds', type=float, default=1.25)
    ap.add_argument('--nodes', type=int, default=5000)
    ap.add_argument('--depth', type=int, default=2)
    ap.add_argument('--qdepth', type=int, default=4)
    ap.add_argument('--total-seconds', type=float, default=100)
    args = ap.parse_args()
    if args.output.exists():
        raise FileExistsError('Refuse to overwrite a frozen probe')
    if args.seed_count < 1 or args.rounds < 1 or any(x < 0 for x in args.prefixes):
        ap.error('positive seed-count/rounds and nonnegative prefixes required')
    limits = SearchLimits(max_depth=args.depth, max_nodes=args.nodes,
                          max_time_seconds=args.seconds, quiescence_max_depth=args.qdepth)
    frozen = (json.loads(args.input.read_text(encoding='utf-8'))['worlds'][:args.seed_count]
              if args.input else None)
    seeds = ([w['seed'] for w in frozen] if frozen is not None else
             list(range(args.seed_start, args.seed_start + args.seed_count)))
    presets = ('classic_like', 'bilateral_random', 'free_random')
    plan = [(seed, prefix, rep, variant)
            for seed in seeds
            for prefix in sorted(set(args.prefixes)) for rep in range(args.rounds)
            for variant in args.variants]
    report = dict(question='Existing Native services and q ordering under actual default consumer',
                  scope=__doc__, protocol=vars(args) | {'output': str(args.output),
                  'input': str(args.input) if args.input else None,
                  'input_sha256': hashlib.sha256(args.input.read_bytes()).hexdigest() if args.input else None,
                  'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  'shuffle_seed': 2026102124, 'planned_queries': len(plan),
                  'walk': ('Frozen complete canonical input records; no sampling' if frozen is not None else
                           'Random(seed+1), uniform full semantic actions; physical multiplicities may differ from legacy'),
                  'query_limits': record_value(limits)}, worlds=[], rows=[])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_record(args.output, report)
    started = time.perf_counter()
    sequence = random.Random(2026102124)
    for index, seed in enumerate(seeds):
        if time.perf_counter() - started >= args.total_seconds:
            break
        cfg = GeneratorConfig(seed=seed, board_size=8, setup_preset=presets[index % 3],
                              max_generation_attempts=30, allow_hybrid=args.allow_hybrid,
                              require_no_opening_win_in_one=args.require_no_opening_win_in_one)
        world = dict(seed=seed, config=frozen[index].get('config', {}) if frozen is not None else asdict(cfg), roots=[])
        report['worlds'].append(world)
        setup_started = time.perf_counter()
        try:
            rule = (ruleset_from_dict(frozen[index]['rule']) if frozen is not None
                    else generate_game(cfg).ruleset)
            compiled = compile_legacy_ruleset_for_semantic_execution(rule)
        except Exception as exc:
            world['setup_failure'] = type(exc).__name__ + ':' + str(exc)
            world['rule_setup_seconds'] = time.perf_counter() - setup_started
            write_record(args.output, report)
            continue
        world['rule_setup_seconds'] = time.perf_counter() - setup_started
        world['rule'] = ruleset_to_dict(rule)
        session = GameSession(compiled)
        walker = random.Random(seed + 1)
        for prefix in sorted(set(args.prefixes)):
            if frozen is not None:
                root = next((r for r in frozen[index]['roots'] if r['target'] == prefix), None)
                if root is None:
                    continue
                session = GameSession.replay(compiled,
                    deserialize_game_record(json.dumps(root['record'])))
            while frozen is None and session.state.ply_count < prefix and not session.state.terminal_status.is_terminal:
                if time.perf_counter() - started >= args.total_seconds:
                    break
                session.submit(walker.choice(session.legal_actions()))
            world['roots'].append(dict(target=prefix, record=record_value(session.to_record()),
                                       terminal=record_value(session.state.terminal_status)))
            if session.state.ply_count != prefix or session.state.terminal_status.is_terminal:
                continue
            for rep in range(args.rounds):
                variants = list(args.variants)
                sequence.shuffle(variants)
                for variant in variants:
                    if time.perf_counter() - started >= args.total_seconds:
                        break
                    tick = time.perf_counter()
                    evaluator = None
                    if args.evaluation_backend != 'default':
                        from generic_chess.ai.evaluation.cache import EvaluationProfileCache
                        from generic_chess.ai.evaluation.config import EvaluationConfig
                        from generic_chess.ai.evaluation.semantic_attacks import SemanticAttackEvaluator
                        config = EvaluationConfig()
                        profile, _ = EvaluationProfileCache(use_disk=False).get_or_build(compiled, config)
                        evaluator = SemanticAttackEvaluator(compiled, profile, config,
                            backend=args.evaluation_backend.removeprefix('semantic_'))
                    player = AlphaBetaPlayer(compiled, use_disk_cache=False, evaluator_override=evaluator,
                        use_native_semantic_availability=variant in ('availability', 'all', 'ordered', 'ordered_evasions'),
                        use_native_semantic_check=variant in ('check', 'all', 'ordered', 'ordered_evasions'),
                        tuning=SearchTuning(use_ordered_qsearch=variant in ('ordered', 'ordered_evasions'),
                            use_ordered_qsearch_in_check=variant == 'ordered_evasions',
                            stop_after_root_win=args.stop_after_root_win))
                    setup = time.perf_counter() - tick
                    before = session.state
                    tick = time.perf_counter()
                    decision = player.choose_action(session, limits)
                    elapsed = time.perf_counter() - tick
                    row = dict(seed=seed, prefix=prefix, rep=rep, variant=variant,
                        player_setup_seconds=setup, query_seconds=elapsed,
                        provider_available=player.native_legality_provider is not None,
                        check_metrics=(player.native_legality_provider.check_metrics
                            if player.native_legality_provider else {}),
                        availability_metrics=(player.native_legality_provider.availability_metrics
                            if player.native_legality_provider else {}),
                        decision=record_value(decision))
                    report['rows'].append(row)
                    try:
                        assert session.state == before
                        record = record_value(session.to_record())
                        assert GameSession.replay(compiled, deserialize_game_record(json.dumps(record))).state == before
                    except Exception as exc:
                        # Retain the executed query even when its qualification
                        # fails; do not turn a caller error into a lost slot.
                        row['validation_failure'] = type(exc).__name__ + ':' + str(exc)
                        write_record(args.output, report)
                        raise
                    write_record(args.output, report)
                    print(seed, prefix, variant, decision.completed_depth,
                          decision.termination_reason, round(elapsed, 4), flush=True)
    observed = {(r['seed'], r['prefix'], r['rep'], r['variant']) for r in report['rows']}
    report['missing_slots'] = [slot for slot in plan if slot not in observed]
    report['wall_seconds'] = time.perf_counter() - started
    write_record(args.output, report)


if __name__ == '__main__':
    main()
