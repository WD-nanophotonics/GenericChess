"""Bounded SAME Model/TDLeafEpisode Generic interface smoke, no strength test."""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
import random
import time

from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from results.dev_aux.task2392.reader import SharedDeleteStopReader
from results.dev_aux.task2492.learning import AlphaBeta, Model
from results.dev_aux.task2492.episode import TDLeafEpisode
from results.dev_aux.task2511.generic import NonScoringTerminal
from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv, unchanged_model, unchanged_learner
from tools.local_agent.environment import require_identity

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "results/dev_aux/task2621/contract-smoke"


def write(name, value):
    with (OUT / name).open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def run():
    require_identity()
    if OUT.exists():
        raise FileExistsError("feasibility is one-shot; no retry/top-up")
    rule_paths = [ROOT / f"results/dev_aux/task2525/rules-{seed}.json" for seed in range(271001, 271005)]
    source_paths = [
        "results/dev_aux/task2621/fixed_scale.py", "results/dev_aux/task2621/feasibility.py",
        "results/dev_aux/task2492/learning.py", "results/dev_aux/task2492/episode.py",
        "results/dev_aux/task2492/adapters.py", "results/dev_aux/task2511/generic.py",
        "generic_chess/session/serialization.py", "generic_chess/session/session.py"]
    OUT.mkdir()
    write("registration.json", dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        question="Can the exact fixed-coordinate Chess Model and TDLeafEpisode execute bounded Generic typed-history searches without FreeModel or hard-coded feature width?",
        rule_selection="All four existing task2525 rules271001-271004, development fixtures; not new or held-out rules",
        rule_sha256={p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in rule_paths},
        source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in source_paths},
        initial_seed=1407393461, initialization="Uniform[0.5,1.5], fixed coordinate0=1, exactly the Chess recipe",
        same_model_class="task2492.learning.Model", same_learner_class="task2492.episode.TDLeafEpisode",
        fixed_scale=10., eta=.05, lam=.95, unit="board P; generator-native type name, no assumed movement/material prior",
        max_queries=16, nodes_per_query=512, max_total_nodes=8192,
        seconds_per_query=2., whole_run_hard_seconds=90,
        strength_evaluation=False, new_training_comparison=False,
        exclusions="Only four legacy generated rules and one short trajectory each; no proof of full generated-domain capability or learned strength"))
    stop = SharedDeleteStopReader(ROOT)
    began = time.perf_counter()
    nodes = 0
    cases = []

    def cancel():
        stop()
        if time.perf_counter() - began >= 90:
            raise TimeoutError("Generic contract smoke reached90-second cap")

    with (OUT / "queries.jsonl").open("x", encoding="utf-8") as stream:
        for index, path in enumerate(rule_paths):
            cancel()
            compiled = compile_ruleset_for_execution(ruleset_from_dict(json.loads(path.read_text())))
            env = FixedScaleSessionEnv(GameSession(compiled))
            rng = random.Random(1407393461)
            initial = [1.] + [rng.uniform(.5, 1.5) for _ in env.names[1:]]
            model, foe, td = unchanged_model(initial), unchanged_model([1.] * len(env.names)), unchanged_learner()
            assert type(model) is Model and type(td) is TDLeafEpisode
            observations = queries = commits = 0
            color = index % 2
            ending = "SMOKE_HORIZON_UNKNOWN"
            initial_record = env.record()
            for ply in range(4):
                cancel()
                if env.terminal() is not None:
                    ending = "ACTUAL_TERMINAL"
                    break
                current = model if env.player() == color else foe
                before, state = env.record(), env.session.state
                weights = list(current.weights)
                receipt = AlphaBeta(2, 0).search(env, current, nodes=512, seconds=2.,
                    seed=2621000 + index * 100 + ply, cancel=cancel)
                nodes += receipt.nodes
                if nodes > 8192 or env.record() != before or env.session.state != state:
                    raise AssertionError("search changed the bound state or exceeded total nodes")
                env.replay()
                if receipt.complete:
                    if env.player() == color:
                        td.observe(model, receipt)
                        observations += 1
                    env.push(receipt.action)
                    commits += 1
                    env.replay()
                else:
                    ending = "SEARCH_RESOURCE_UNKNOWN"
                queries += 1
                stream.write(json.dumps(dict(rule=path.stem, ply=ply, channels=env.names,
                    learner_color=color, weights_before_search=weights, record_before=before,
                    record_after=env.record(), complete=receipt.complete, nodes=receipt.nodes,
                    value=receipt.value, pv_phi=receipt.pv_phi, pv_terminal=receipt.pv_terminal,
                    action=repr(receipt.action) if receipt.complete else None), sort_keys=True) + "\n")
                stream.flush()
                if not receipt.complete:
                    break
            actual = env.terminal()
            stats = td.finish(model, actual)
            assert model.fixed == 0 and model.weights[0] == 1. and model.scale == 10.
            assert stats["censored"] == (actual is None)
            cases.append(dict(rule=path.stem, channels=env.names, initial_weights=initial,
                final_weights=list(model.weights), fixed_coordinate=model.fixed, scale=model.scale,
                initial_record=initial_record, final_record=env.record(), actual_outcome=actual,
                ending="ACTUAL_TERMINAL" if actual is not None else ending,
                observed_candidate_receipts=observations, queries=queries, commits=commits,
                td_stats=stats, full_history_replay=True))
    result = dict(status="FINITE_INTERFACE_FEASIBILITY_ONLY", cases=cases,
        rules=len(cases), nodes=nodes, seconds=time.perf_counter()-began,
        exact_model_and_learner_classes=True, fixed_coordinate_preserved=True,
        strength_evaluation=False, population_or_full_domain_claim=False,
        scope="Same learning procedure with newly initialized per-rule parameters, not transfer of learned Chess weights. Four development rules and finite semantic contract witnesses only.")
    write("result.json", result)
    return result


if __name__ == "__main__":
    result = run()
    print(json.dumps({k: v for k, v in result.items() if k != "cases"}, indent=2))
