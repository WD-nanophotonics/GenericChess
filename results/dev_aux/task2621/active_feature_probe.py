"""One bounded, outcome-blind Generic active-feature/cost feasibility probe.

The earlier opening smoke's zero updates remain intact. Select first eligible
nonterminal8-ply histories with a nonzero non-fixed inventory channel, before
search/loss/outcome inspection. No strength comparison or hyperparameter fit.
"""
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
from results.dev_aux.task2492.learning import AlphaBeta
from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv, unchanged_model, unchanged_learner
from tools.local_agent.environment import require_identity

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "results/dev_aux/task2621/active-feature-probe"


def write(name, value):
    with (OUT / name).open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def run():
    require_identity()
    if OUT.exists():
        raise FileExistsError("active-feature probe is one-shot; no top-up/retry")
    OUT.mkdir()
    write("registration.json", dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        premise_change="The16-query opening smoke completed but all updates were zero; this probe changes only the outcome-blind history preparation",
        rule_ids=list(range(271001, 271005)), eligible_rule_scope="Same four development fixtures, not a new/held-out rule sample",
        root_selection="First two nonterminal8-ply histories per rule, families1800001..1800032; require any non-fixed inventory feature nonzero; no search/loss/terminal-reward selection",
        initialization_seed=1407393461, recipe="Uniform[.5,1.5], fixed boardP=1,scale10; exact Model/TDLeafEpisode eta.05 lambda.95",
        roots_expected=8, max_queries=32, nodes_per_query=2048, node_cap=65536,
        seconds_per_query=2., hard_seconds=120, prefix_limit_plies=8,
        strength_evaluation=False, original_opening_smoke_replaced=False,
        decision="Use measured full-history throughput and update incidence to plan a bounded strict SAME fixed-scale learner comparison; zero update remains a legitimate feasibility outcome"))
    stop = SharedDeleteStopReader(ROOT)
    began = time.perf_counter()

    def cancel():
        stop()
        if time.perf_counter() - began >= 120:
            raise TimeoutError("active-feature probe reached its120-second cap")

    selected = []
    compiled_by_id = {}
    for rule_id in range(271001, 271005):
        raw = (ROOT / f"results/dev_aux/task2525/rules-{rule_id}.json").read_bytes()
        compiled = compile_ruleset_for_execution(ruleset_from_dict(json.loads(raw)))
        compiled_by_id[rule_id] = compiled
        found = 0
        for family in range(1800001, 1800033):
            cancel()
            env = FixedScaleSessionEnv(GameSession(compiled))
            rng = random.Random(rule_id * 1000000 + family)
            for _ in range(8):
                if env.terminal() is not None:
                    break
                env.push(rng.choice(sorted(env.actions(), key=repr)))
            if env.terminal() is None and any(env.features()[1:]):
                env.replay()
                selected.append(dict(rule=rule_id, family=family, record=env.record(),
                                     features=env.features(), channels=env.names,
                                     rule_sha256=hashlib.sha256(raw).hexdigest(), learner_color=found))
                found += 1
                if found == 2:
                    break
    write("root-manifest.json", dict(roots=selected, search_or_outcomes_used=False))
    if len(selected) != 8:
        result = dict(status="PARTIAL_ROOT_FEASIBILITY", roots=len(selected),
                      missing_roots=8-len(selected), seconds=time.perf_counter()-began,
                      search_queries=0, no_retry_or_top_up=True)
        write("result.json", result)
        return result
    nodes = 0
    cases = []
    with (OUT / "queries.jsonl").open("x", encoding="utf-8") as stream:
        for index, root in enumerate(selected):
            from generic_chess.session.serialization import deserialize_game_record
            env = FixedScaleSessionEnv(GameSession.replay(compiled_by_id[root["rule"]],
                deserialize_game_record(json.dumps(root["record"]))))
            rng = random.Random(1407393461)
            initial = [1.] + [rng.uniform(.5, 1.5) for _ in env.names[1:]]
            model, foe, td = unchanged_model(initial), unchanged_model([1.] * len(env.names)), unchanged_learner()
            q_count = 0
            used = 0
            query_seconds = 0.
            ending = "FEASIBILITY_HORIZON_UNKNOWN"
            for ply in range(4):
                cancel()
                if env.terminal() is not None:
                    ending = "ACTUAL_TERMINAL"
                    break
                actor = env.player()
                current = model if actor == root["learner_color"] else foe
                before, state = env.record(), env.session.state
                weights = list(current.weights)
                receipt = AlphaBeta(2, 0).search(env, current, nodes=2048, seconds=2.,
                    seed=2621100 + index * 100 + ply, cancel=cancel)
                nodes += receipt.nodes
                used += receipt.nodes
                query_seconds += receipt.seconds
                if nodes > 65536 or env.record() != before or env.session.state != state:
                    raise AssertionError("probe exceeded its cap or mutated search history")
                if receipt.complete:
                    if actor == root["learner_color"]:
                        td.observe(model, receipt)
                    env.push(receipt.action)
                    env.replay()
                else:
                    ending = "SEARCH_RESOURCE_UNKNOWN"
                q_count += 1
                stream.write(json.dumps(dict(case=index, rule=root["rule"], family=root["family"],
                    ply=ply, actor=actor, weights_before_search=weights, record_before=before,
                    record_after=env.record(), complete=receipt.complete, value=receipt.value,
                    pv_phi=receipt.pv_phi, pv_terminal=receipt.pv_terminal,
                    nodes=receipt.nodes, seconds=receipt.seconds), sort_keys=True) + "\n")
                stream.flush()
                if not receipt.complete:
                    break
            actual = env.terminal()
            stats = td.finish(model, actual)
            if model.weights[0] != 1. or model.scale != 10.:
                raise AssertionError("fixed scale changed")
            cases.append(dict(rule=root["rule"], family=root["family"], learner_color=root["learner_color"],
                initial_features=root["features"], initial_weights=initial, final_weights=model.weights,
                queries=q_count, nodes=used, search_seconds=query_seconds, stats=stats,
                actual_outcome=actual, ending="ACTUAL_TERMINAL" if actual is not None else ending,
                full_history_replay=True))
    result = dict(status="FINITE_ACTIVE_FEATURE_FEASIBILITY_ONLY", roots=len(selected), cases=cases,
                  queries=sum(case["queries"] for case in cases), nodes=nodes,
                  seconds=time.perf_counter()-began,
                  nonzero_parameter_updates=sum(case["initial_weights"] != case["final_weights"] for case in cases),
                  strength_evaluation=False, original_opening_smoke_replaced=False,
                  scope="Development-only excitation/throughput witnesses; no method ranking, convergence, held-out or full-domain claim")
    write("result.json", result)
    return result


if __name__ == "__main__":
    result = run()
    print(json.dumps({key: value for key, value in result.items() if key != "cases"}, indent=2))
