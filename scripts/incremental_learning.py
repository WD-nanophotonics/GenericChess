"""Small exploratory Generic TDLeaf pilot; outputs belong under artifacts/.

No registration, source-pin auditor, solver, product defaults or extra worker.
This entry tests separate learning on one ruleset, not cross-rule knowledge
transfer or population strength. Reusing a fixture never creates a holdout.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path
import random
import subprocess
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.learning.incremental import (
    BudgetEnd, FixedScaleSessionEnv, NonScoringTerminal,
    play_episode, TDLeafEpisode, unchanged_model,
)
from generic_chess.core.actions import action_to_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession


def _model_snapshot(model):
    return dict(weights=list(model.weights), fixed=model.fixed, scale=model.scale)


def _choice_record(choice):
    if choice is None:
        return None
    return dict(kind=choice.kind,
                action=None if choice.action is None else action_to_dict(choice.action),
                declaration_id=choice.declaration_id)


def _require_total_wall_budget(seconds):
    if not 0 < seconds < float('inf'):
        raise ValueError('seconds must be finite and positive')


def run(args):
    _require_total_wall_budget(args.seconds)
    compiled = compile_ruleset_for_execution(ruleset_from_dict(json.loads(args.rules.read_text(encoding='utf-8-sig'))))
    args.output.mkdir(parents=True, exist_ok=False)
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    began = perf_counter()
    deadline = began + args.seconds
    coupled = getattr(args, 'compare_lambda', None) is not None
    train_allowance = getattr(args, 'train_seconds', None) or args.seconds / 2
    train_deadline = began + train_allowance
    dimension = len(FixedScaleSessionEnv(GameSession(compiled), unit_type=args.unit).names)
    rng = random.Random(args.seed)
    initial = [1.] + [rng.uniform(.5, 1.5) for _ in range(dimension - 1)]
    lambdas = {'trained': getattr(args, 'td_lambda', .95)} if not coupled else {
        'lambda_a': args.td_lambda, 'lambda_b': args.compare_lambda}
    models = {name: unchanged_model(initial) for name in lambdas}
    foe = unchanged_model([1.] * dimension)
    config = {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()}
    config.update(revision=revision, initial_weights=initial,
                  scope='Exploratory single-rule pilot; exposed fixture/random-opening roots, not an independent holdout.')
    (args.output / 'config.json').write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')

    def stop():
        for name in ('rollout', 'advisor', 'slack'):
            flags = json.loads((ROOT / '.local_agent' / (name + '.json')).read_bytes())
            if flags.get('user_paused') or flags.get('stopped'):
                raise BudgetEnd('STOPPED_USER')
        if perf_counter() >= deadline:
            raise BudgetEnd('GLOBAL_TIME_CAP')

    def train_stop():
        stop()
        if perf_counter() >= train_deadline:
            raise BudgetEnd('TRAIN_TIME_CAP')

    def root(seed, guard=stop):
        env = FixedScaleSessionEnv(GameSession(compiled), unit_type=args.unit)
        randomizer = random.Random(seed)
        for _ in range(randomizer.randrange(2, 9)):
            guard()
            try:
                terminal = env.terminal()
            except NonScoringTerminal:
                break
            if terminal is not None:
                break
            choices = env.actions()
            if not choices:
                break
            env.push(randomizer.choice(choices))
        guard()
        replayed = env.replay()
        guard()
        return replayed

    training, evaluation = [], []
    costs = Counter()
    profile_seconds = Counter()
    exposure = Counter()
    active = {}
    def bucket(phase, profile):
        return phase + ('_' + profile if coupled else '') + '_nodes'

    eval_deadline = deadline
    def eval_stop():
        stop()
        if perf_counter() >= eval_deadline:
            raise BudgetEnd('PROFILE_TIME_CAP')
    with (args.output / 'queries.jsonl').open('x', encoding='utf-8') as trace, \
         (args.output / 'episodes.jsonl').open('x', encoding='utf-8') as episodes:
        def on_query(ply, actor, receipt):
            costs[bucket(active['phase'], active['profile'])] += receipt.nodes
            if receipt.complete and receipt.pv_phi is not None:
                for name, quantity in zip(active['env'].names, receipt.pv_phi):
                    exposure[str(name)] += quantity != 0
            row = {k: v for k, v in active.items()
                   if k not in ('env', 'candidate_model', 'opponent_model')}
            row['acting_model'] = active['candidate_model'] if actor == row['color'] else active['opponent_model']
            # A returned choice can still be discarded by the episode guard;
            # only final_record establishes what was actually played.
            row['choice'] = _choice_record(receipt.action)
            row.update(ply=ply, actor=actor, nodes=receipt.nodes, complete=receipt.complete,
                       value=receipt.value, pv_phi=receipt.pv_phi, pv_terminal=receipt.pv_terminal,
                       reason=receipt.reason)
            row.update(completed_depth=receipt.completed_depth,
                       attempted_depth=receipt.attempted_depth,
                       attempts=[asdict(a) for a in receipt.attempts])
            trace.write(json.dumps(row, allow_nan=False) + '\n')
            trace.flush()

        def episode(env, candidate, *, phase, index, color, profile, remaining, seconds, guard=stop):
            before = _model_snapshot(candidate)
            active.update(phase=phase, index=index, color=color, profile=profile, env=env,
                          candidate_model=before, opponent_model=_model_snapshot(foe))
            start_record = env.record()
            result = play_episode(env, candidate, opponent=foe,
                learner=TDLeafEpisode(eta=.05, lam=lambdas[profile]) if phase == 'train' else None,
                learner_color=color, horizon=args.horizon, depth=args.depth,
                query_nodes=args.query_nodes, max_nodes=min(args.game_nodes, remaining),
                seconds=seconds, seed=args.seed * 1_000_000 + (0 if phase == 'train' else 1_000_000_000) + index * args.horizon,
                cancel=guard, on_query=on_query,
                iterative=getattr(args, 'iterative', False),
                opponent_depth=getattr(args, 'opponent_depth', None),
                opponent_iterative=getattr(args, 'opponent_iterative', None),
                search_backend=getattr(args, 'search_backend', 'mainline'))
            env.replay()  # Actual full history/result, not a state-only check.
            row = dict(phase=phase, index=index, color=color, profile=profile,
                       start_record=start_record, final_record=env.record(),
                       before_weights=before['weights'], weights=list(candidate.weights), **asdict(result))
            episodes.write(json.dumps(row, allow_nan=False) + '\n')
            episodes.flush()
            return row

        training_phase_seconds = None
        try:
            for profile, model in models.items():
                arm_began = perf_counter()
                train_deadline = min(deadline, arm_began + train_allowance)
                for index in range(args.train_episodes):
                    stop()
                    remaining = args.train_nodes - costs[bucket('train', profile)]
                    seconds = train_deadline - perf_counter()
                    if remaining <= 0 or seconds <= 0:
                        break
                    try:
                        env = root(args.seed * 10_000 + index, guard=train_stop)
                    except BudgetEnd as error:
                        if str(error) == 'TRAIN_TIME_CAP':
                            break
                        raise
                    seconds = train_deadline - perf_counter()
                    if seconds <= 0:
                        break
                    row = episode(env, model, phase='train', index=index, color=index % 2,
                                  profile=profile, remaining=remaining, seconds=seconds, guard=train_stop)
                    training.append(row)
                    if 'STOPPED_USER' in row['ending']:
                        raise BudgetEnd('STOPPED_USER')
                    if (index + 1) % 8 == 0:
                        print(json.dumps(dict(phase='train', profile=profile, episodes=index + 1,
                            nodes=costs[bucket('train', profile)], seconds=perf_counter() - began)), flush=True)
                profile_seconds['train_' + profile] = perf_counter() - arm_began
            training_phase_seconds = perf_counter() - began
            frozen = {name: list(model.weights) for name, model in models.items()}
            frozen['initial'] = initial
            for family in range(args.eval_pairs):
                for color in (0, 1):
                    profiles = list(frozen)
                    # Rotate the first profile, then reverse alternate families.
                    # All profiles receive identical root/search seeds.
                    if coupled:
                        profiles = profiles[family % len(profiles):] + profiles[:family % len(profiles)]
                        if family % 2:
                            profiles.reverse()
                    elif family % 2:
                        profiles.reverse()
                    for profile in profiles:
                        stop()
                        remaining = args.eval_nodes - costs[bucket('eval', profile)]
                        allowance = getattr(args, 'eval_seconds', None) if coupled else None
                        seconds = min(deadline - perf_counter(),
                            allowance - profile_seconds['eval_' + profile] if allowance else float('inf'))
                        if remaining <= 0 or seconds <= 0:
                            if coupled:
                                continue  # Retain every absent slot in the fixed denominator.
                            raise BudgetEnd('EVALUATION_CAP')
                        own_began = perf_counter()
                        eval_deadline = own_began + seconds
                        try:
                            env = root(args.seed * 10_000 + 1_000_000 + family, guard=eval_stop)
                            eval_stop()
                            row = episode(env, unchanged_model(frozen[profile]),
                                          phase='eval', index=2 * family + color, color=color,
                                          profile=profile, remaining=remaining,
                                          seconds=max(1e-9, eval_deadline - perf_counter()), guard=eval_stop)
                        except BudgetEnd as error:
                            if str(error) != 'PROFILE_TIME_CAP' or not coupled:
                                raise
                            continue
                        finally:
                            profile_seconds['eval_' + profile] += perf_counter() - own_began
                        evaluation.append(row)
                        if 'STOPPED_USER' in row['ending']:
                            raise BudgetEnd('STOPPED_USER')
                if (family + 1) % 4 == 0:
                    print(json.dumps(dict(phase='eval', families=family + 1, costs=dict(costs), seconds=perf_counter() - began)), flush=True)
            status = 'PLANNED_EPISODES_COMPLETE'
        except BudgetEnd as error:
            if training_phase_seconds is None:
                training_phase_seconds = perf_counter() - began
            status = str(error)
    paired = {(r['index'], r['profile']): r for r in evaluation}
    profiles = list(models) + ['initial']
    if status == 'PLANNED_EPISODES_COMPLETE' and len(evaluation) < args.eval_pairs * 2 * len(profiles):
        status = 'PROFILE_CAPS_WITH_MISSING'
    def contrast(candidate, baseline):
        lower = upper = 0
        for index in range(args.eval_pairs * 2):
            values = []
            for profile in (candidate, baseline):
                row = paired.get((index, profile))
                outcome = row['outcome'] if row else None
                values.append(None if outcome is None else outcome * (1 if index % 2 == 0 else -1))
            a, b = values
            lower += (a if a is not None else -1) - (b if b is not None else 1)
            upper += (a if a is not None else 1) - (b if b is not None else -1)
        return [lower / (args.eval_pairs * 2), upper / (args.eval_pairs * 2)]
    contrasts = {name + '-initial': contrast(name, 'initial') for name in models}
    if coupled:
        # The ONE shared baseline cancels exactly, even when its result is UNKNOWN.
        contrasts['lambda_b-lambda_a'] = contrast('lambda_b', 'lambda_a')
    summary = dict(status=status, revision=revision, seconds=perf_counter() - began,
        training_phase_seconds=training_phase_seconds,
        config=config, final_weights=list(models[profiles[0]].weights), costs=dict(costs),
        final_weights_by_profile={name: list(m.weights) for name, m in models.items()},
        profile_seconds=dict(profile_seconds),
        training_episodes=len(training), training_updates=sum(bool(r['update']['changed']) for r in training),
        evaluation_slots=len(evaluation), expected_evaluation_slots=args.eval_pairs * 2 * len(profiles),
        missing_evaluation_slots=args.eval_pairs * 2 * len(profiles) - len(evaluation),
        evaluation_actual_terminal=sum(r['outcome'] is not None for r in evaluation),
        evaluation_UNKNOWN=sum(r['outcome'] is None for r in evaluation),
        evaluation_outcomes_by_profile={p: dict(Counter(str(r['outcome'] * (1 if r['color'] == 0 else -1))
            if r['outcome'] is not None else 'UNKNOWN' for r in evaluation if r['profile'] == p)) for p in profiles},
        paired_reward_completion_bound=next(iter(contrasts.values())),
        contrasts=contrasts,
        bound_is_not_a_confidence_interval=True, pv_channel_exposure=dict(exposure),
        pv_channel_exposure_scope='All returned complete nonterminal query PVs across phases and actors, before post-query guard; not accepted TD observations or played decisions.')
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2), flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rules', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--unit', default='P')
    parser.add_argument('--seed', type=int, default=8173)
    parser.add_argument('--train-episodes', type=int, default=128)
    parser.add_argument('--eval-pairs', type=int, default=32)
    parser.add_argument('--train-nodes', type=int, default=1_000_000)
    parser.add_argument('--eval-nodes', type=int, default=1_000_000)
    parser.add_argument('--seconds', type=float, default=1200.,
                        help='positive finite total wall allowance in seconds')
    parser.add_argument('--horizon', type=int, default=128)
    parser.add_argument('--depth', type=int, default=2)
    parser.add_argument('--td-lambda', type=float, default=.95,
                        help='classical frozen-episode TDLeaf trace decay in [0,1]')
    parser.add_argument('--compare-lambda', type=float,
                        help='optional second trace decay; common initialization/roots and ONE initial control')
    parser.add_argument('--train-seconds', type=float,
                        help='per-training-arm allowance, including opening/play/replay')
    parser.add_argument('--eval-seconds', type=float,
                        help='per-evaluation-profile active allowance; required for coupled comparison')
    parser.add_argument('--iterative', action='store_true',
                        help='reference backend: pay D1 through depth under one shared query budget')
    parser.add_argument('--search-backend', choices=('mainline', 'reference'), default='mainline',
                        help='public mainline iterative q0(default), or frozen randomized reference')
    parser.add_argument('--opponent-depth', type=int)
    parser.add_argument('--opponent-iterative', action=argparse.BooleanOptionalAction,
                        default=None)
    parser.add_argument('--query-nodes', type=int, default=8192)
    parser.add_argument('--game-nodes', type=int, default=100_000)
    args = parser.parse_args()
    try:
        _require_total_wall_budget(args.seconds)
    except ValueError as error:
        parser.error(str(error))
    if not 0 <= args.td_lambda <= 1:
        parser.error('td-lambda must be finite and in [0,1]')
    if args.compare_lambda is not None and (not 0 <= args.compare_lambda <= 1 or
            not args.eval_seconds or not 0 < args.eval_seconds < float('inf')):
        parser.error('compare-lambda requires finite decay in [0,1] and positive finite eval-seconds')
    if args.train_seconds is not None and not 0 < args.train_seconds < float('inf'):
        parser.error('train-seconds must be finite and positive')
    if min(args.train_episodes, args.eval_pairs, args.train_nodes, args.eval_nodes,
           args.seconds, args.horizon, args.depth, args.query_nodes, args.game_nodes) <= 0:
        parser.error('all counts and budgets must be positive')
    run(args)


if __name__ == '__main__':
    main()
