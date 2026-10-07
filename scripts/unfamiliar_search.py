"""Small generated-rule search diagnostic; no learning or strength claim."""
from __future__ import annotations

import argparse
import hashlib
import time
from pathlib import Path

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.search import reference_minimax
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.cache import EvaluationProfileCache
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.rules.schema import ruleset_to_dict
from generic_chess.session.session import GameSession
from scripts.research_record import record_value, write_record


class ReferenceLimit(RuntimeError):
    pass


class CountedEvaluator:
    """A declared reference cost fuse, never a partial score certificate."""
    def __init__(self, evaluator, seconds=5, evaluations=4096):
        self.evaluator = evaluator
        self.deadline = time.perf_counter() + seconds
        self.maximum = evaluations
        self.calls = 0

    def evaluate(self, state):
        self.calls += 1
        if self.calls > self.maximum or time.perf_counter() > self.deadline:
            raise ReferenceLimit('reference cost fuse')
        return self.evaluator.evaluate(state)


def validate_pv(session, decision):
    state = session.state
    for action in decision.principal_variation:
        if action not in legal_actions(state, session.compiled):
            raise AssertionError('illegal principal variation')
        state = apply_action(state, action, session.compiled)
    if decision.action is not None and decision.action not in session.legal_actions():
        raise AssertionError('illegal selected action')


def run(output: Path, *, depth=2, shared_profile=False):
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    declaration = dict(
        question='Does the existing public search remain legal and stable on generated unfamiliar rules, and where is its cost?',
        tier='3: existing generator random movement/promotion/drop rules with existing playability filters; not all proposed recombined semantics',
        configs=[dict(seed=seed, board_size=size, setup_preset='bilateral_random', allow_hybrid=True)
                 for size in (4, 6) for seed in (7, 21)],
        search=dict(depth=depth, nodes=4096, seconds=5, quiescence_depth=0,
                    root_tactical=False, repeats=2),
        shared_profile_cache=shared_profile,
        controls='Python legality/plain alpha-beta without TT or ordering versus public default native-legality/TT/ordering bundle; fresh TT per repeat, same profile/evaluator/root/depth/budgets.',
        reference='Existing plain minimax at declared depth, <=4096 leaf evaluations and5sec checked at evaluation; aborted result is unknown. Reference is not a resource-matched speed comparator.',
        decision='Any legality, repeat or completed-score discrepancy requires localization before expansion. Complete parity permits deeper cost profiling; speed claims require completed equal-depth cells.',
        limitations='Four seeds/configs at initial roots, exposed development; no game-strength/general coverage proof. Generic-v1 heuristic evaluator is held fixed, not the contact prior or learned model.',
        producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )
    report = dict(complete=False, declaration=declaration, cases=[])
    write_record(output, report)
    for config in declaration['configs']:
        start = time.perf_counter()
        game = generate_game(GeneratorConfig(**config))
        generation_seconds = time.perf_counter() - start
        compiled = game.compiled_ruleset
        start = time.perf_counter()
        cache = EvaluationProfileCache(use_disk=False) if shared_profile else None
        profile = cache.get_or_build(compiled, EvaluationConfig())[0] if cache else build_ruleset_profile(compiled, EvaluationConfig())
        profile_seconds = time.perf_counter() - start
        evaluator = Evaluator(compiled, profile, EvaluationConfig())
        session = GameSession(compiled)
        counted = CountedEvaluator(evaluator)
        start = time.perf_counter()
        try:
            score, action = reference_minimax(session.state, depth, counted, compiled)
            reference = dict(complete=True, score=score, action=record_value(action))
        except ReferenceLimit:
            reference = dict(complete=False, score=None, action=None)
        reference.update(wall_seconds=time.perf_counter()-start, leaf_evaluations=counted.calls)
        case = dict(config=config, fingerprint=compiled.ruleset_fingerprint,
                    ruleset=ruleset_to_dict(game.ruleset), filters=record_value(game.generation_report),
                    generation_seconds=generation_seconds, profile_seconds=profile_seconds,
                    opening_legal_actions=len(session.legal_actions()), reference=reference, searches=[])
        for optimized in (False, True):
            signatures = []
            for repeat in range(2):
                start = time.perf_counter()
                player = AlphaBetaPlayer(compiled, use_disk_cache=False,
                    profile_cache=cache,
                    use_native_semantic_legality=optimized, use_tt=optimized, use_ordering=optimized,
                    evaluator_override=evaluator, tt_max_entries=4096,
                    tuning=SearchTuning(use_root_tactical=False))
                setup_seconds = time.perf_counter()-start
                start = time.perf_counter()
                decision = player.choose_action(session, SearchLimits(max_depth=depth, max_nodes=4096,
                    max_time_seconds=5, quiescence_max_depth=0, quiescence_hard_max_depth=0))
                observed_search_seconds = time.perf_counter()-start
                validate_pv(session, decision)
                signatures.append((record_value(decision.action), decision.score, decision.completed_depth))
                complete = decision.completed_depth == depth
                case['searches'].append(dict(control='public_bundle' if optimized else 'python_plain',
                    repeat=repeat, setup_seconds=setup_seconds, observed_search_seconds=observed_search_seconds,
                    native_provider_present=player.native_legality_provider is not None,
                    complete=complete, reference_score_equal=(decision.score == reference['score']) if complete and reference['complete'] else None,
                    decision=record_value(decision)))
            case.setdefault('repeat_equal', {})['public_bundle' if optimized else 'python_plain'] = signatures[0] == signatures[1]
        report['cases'].append(case)
        write_record(output, report)
        print(config, 'legal',case['opening_legal_actions'],'reference',reference['complete'],
              'searches',[(s['control'],s['complete'],s['reference_score_equal'],s['decision']['nodes']) for s in case['searches']],flush=True)
    report['complete'] = True
    write_record(output, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--depth', type=int, choices=(2, 3), default=2)
    parser.add_argument('--shared-profile', action='store_true')
    args = parser.parse_args()
    run(args.output, depth=args.depth, shared_profile=args.shared_profile)


if __name__ == '__main__':
    main()
