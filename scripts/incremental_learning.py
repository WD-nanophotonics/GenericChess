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
    play_episode, unchanged_learner, unchanged_model,
)
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession


def run(args):
    compiled = compile_ruleset_for_execution(ruleset_from_dict(json.loads(args.rules.read_text(encoding='utf-8-sig'))))
    args.output.mkdir(parents=True, exist_ok=False)
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    began = perf_counter()
    deadline = began + args.seconds
    train_deadline = began + args.seconds / 2
    dimension = len(FixedScaleSessionEnv(GameSession(compiled), unit_type=args.unit).names)
    rng = random.Random(args.seed)
    initial = [1.] + [rng.uniform(.5, 1.5) for _ in range(dimension - 1)]
    model, foe = unchanged_model(initial), unchanged_model([1.] * dimension)
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
    exposure = Counter()
    active = {}
    with (args.output / 'queries.jsonl').open('x', encoding='utf-8') as trace, \
         (args.output / 'episodes.jsonl').open('x', encoding='utf-8') as episodes:
        def on_query(ply, actor, receipt):
            costs[active['phase'] + '_nodes'] += receipt.nodes
            if receipt.complete and receipt.pv_phi is not None:
                for name, quantity in zip(active['env'].names, receipt.pv_phi):
                    exposure[str(name)] += quantity != 0
            row = {k: v for k, v in active.items() if k != 'env'}
            row.update(ply=ply, actor=actor, nodes=receipt.nodes, complete=receipt.complete,
                       value=receipt.value, pv_phi=receipt.pv_phi, pv_terminal=receipt.pv_terminal,
                       reason=receipt.reason)
            trace.write(json.dumps(row, allow_nan=False) + '\n')
            trace.flush()

        def episode(env, candidate, *, phase, index, color, profile, remaining, seconds, guard=stop):
            active.update(phase=phase, index=index, color=color, profile=profile, env=env)
            start_record = env.record()
            result = play_episode(env, candidate, opponent=foe,
                learner=unchanged_learner() if phase == 'train' else None,
                learner_color=color, horizon=args.horizon, depth=args.depth,
                query_nodes=args.query_nodes, max_nodes=min(args.game_nodes, remaining),
                seconds=seconds, seed=args.seed * 1_000_000 + (0 if phase == 'train' else 1_000_000_000) + index * args.horizon,
                cancel=guard, on_query=on_query)
            env.replay()  # Actual full history/result, not a state-only check.
            row = dict(phase=phase, index=index, color=color, profile=profile,
                       start_record=start_record, final_record=env.record(),
                       weights=list(candidate.weights), **asdict(result))
            episodes.write(json.dumps(row, allow_nan=False) + '\n')
            episodes.flush()
            return row

        training_phase_seconds = None
        try:
            for index in range(args.train_episodes):
                stop()
                remaining = args.train_nodes - costs['train_nodes']
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
                              profile='trained', remaining=remaining, seconds=seconds, guard=train_stop)
                training.append(row)
                if 'STOPPED_USER' in row['ending']:
                    raise BudgetEnd('STOPPED_USER')
                if len(training) % 8 == 0:
                    print(json.dumps(dict(phase='train', episodes=len(training), nodes=costs['train_nodes'], seconds=perf_counter() - began)), flush=True)
            training_phase_seconds = perf_counter() - began
            final = list(model.weights)
            for family in range(args.eval_pairs):
                for color in (0, 1):
                    for profile in (('trained', 'initial') if family % 2 == 0 else ('initial', 'trained')):
                        stop()
                        remaining = args.eval_nodes - costs['eval_nodes']
                        seconds = deadline - perf_counter()
                        if remaining <= 0 or seconds <= 0:
                            raise BudgetEnd('EVALUATION_CAP')
                        env = root(args.seed * 10_000 + 1_000_000 + family)
                        seconds = deadline - perf_counter()
                        if seconds <= 0:
                            raise BudgetEnd('GLOBAL_TIME_CAP')
                        row = episode(env, unchanged_model(final if profile == 'trained' else initial),
                                      phase='eval', index=2 * family + color, color=color,
                                      profile=profile, remaining=remaining, seconds=seconds)
                        evaluation.append(row)
                        if 'STOPPED_USER' in row['ending']:
                            raise BudgetEnd('STOPPED_USER')
                if (family + 1) % 4 == 0:
                    print(json.dumps(dict(phase='eval', families=family + 1, nodes=costs['eval_nodes'], seconds=perf_counter() - began)), flush=True)
            status = 'PLANNED_EPISODES_COMPLETE'
        except BudgetEnd as error:
            if training_phase_seconds is None:
                training_phase_seconds = perf_counter() - began
            status = str(error)
    paired = {(r['index'], r['profile']): r for r in evaluation}
    lower = upper = 0
    for index in range(args.eval_pairs * 2):
        values = []
        for profile in ('trained', 'initial'):
            row = paired.get((index, profile))
            outcome = row['outcome'] if row else None
            values.append(None if outcome is None else outcome * (1 if index % 2 == 0 else -1))
        candidate, baseline = values
        lower += (candidate if candidate is not None else -1) - (baseline if baseline is not None else 1)
        upper += (candidate if candidate is not None else 1) - (baseline if baseline is not None else -1)
    summary = dict(status=status, revision=revision, seconds=perf_counter() - began,
        training_phase_seconds=training_phase_seconds,
        config=config, final_weights=list(model.weights), costs=dict(costs),
        training_episodes=len(training), training_updates=sum(bool(r['update']['changed']) for r in training),
        evaluation_slots=len(evaluation), expected_evaluation_slots=args.eval_pairs * 4,
        missing_evaluation_slots=args.eval_pairs * 4 - len(evaluation),
        evaluation_actual_terminal=sum(r['outcome'] is not None for r in evaluation),
        evaluation_UNKNOWN=sum(r['outcome'] is None for r in evaluation),
        evaluation_outcomes_by_profile={p: dict(Counter(str(r['outcome'] * (1 if r['color'] == 0 else -1))
            if r['outcome'] is not None else 'UNKNOWN' for r in evaluation if r['profile'] == p)) for p in ('trained', 'initial')},
        paired_reward_completion_bound=[lower / (args.eval_pairs * 2), upper / (args.eval_pairs * 2)],
        bound_is_not_a_confidence_interval=True, pv_channel_exposure=dict(exposure))
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
    parser.add_argument('--seconds', type=float, default=1200.)
    parser.add_argument('--horizon', type=int, default=128)
    parser.add_argument('--depth', type=int, default=2)
    parser.add_argument('--query-nodes', type=int, default=8192)
    parser.add_argument('--game-nodes', type=int, default=100_000)
    args = parser.parse_args()
    if min(args.train_episodes, args.eval_pairs, args.train_nodes, args.eval_nodes,
           args.seconds, args.horizon, args.depth, args.query_nodes, args.game_nodes) <= 0:
        parser.error('all counts and budgets must be positive')
    run(args)


if __name__ == '__main__':
    main()
