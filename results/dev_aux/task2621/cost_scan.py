"""Small cost-only scan of the exact fixed-scale Generic learner.

Four development rules, one fixed initialization each,80k combined candidate/
foe nodes per arm. These repeated development roots are not a strength test or
a holdout. The320k-node/300-second batch is a cost checkpoint, not a new route.
"""
from __future__ import annotations

from collections import Counter
import datetime
import hashlib
import json
from pathlib import Path
import random
import time

from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from results.dev_aux.task2392.reader import SharedDeleteStopReader
from results.dev_aux.task2492.learning import AlphaBeta, BudgetEnd
from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv, unchanged_model, unchanged_learner
from tools.local_agent.environment import require_identity

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "results/dev_aux/task2621/cost-scan"


def dump(name, value):
    with (OUT / name).open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def run():
    require_identity()
    if OUT.exists():
        raise FileExistsError("cost scan is one-shot; no retry/top-up")
    root_path = OUT.parent / "active-feature-probe/root-manifest.json"
    roots_raw = root_path.read_bytes()
    roots = json.loads(roots_raw)["roots"]
    OUT.mkdir()
    dump("registration.json", dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        question="What are actual full-history search/update/record costs beyond the tiny active-feature smoke?",
        root_manifest_sha256=hashlib.sha256(roots_raw).hexdigest(),
        roots="All eight already exposed development roots; cycle the two per rule without outcome selection",
        rule_ids=list(range(271001, 271005)), initial_seed=1407393461,
        exact_model="task2492.learning.Model fixed0 scale10", exact_learner="TDLeafEpisode eta.05 lambda.95",
        nodes_per_arm_candidate_plus_foe=80000, expected_arms=4, hard_nodes=320000,
        hard_seconds=300, seconds_per_query=2., max_nodes_per_query=2048,
        max_episodes_per_arm=256, max_plies_per_episode=512,
        strength_comparison=False, no_heldout_claim=True,
        cost_decision="Source-bound feasibility for a future preregistered SAME fixed-scale learner comparison; do not select weights or infer learning benefit"))
    stop = SharedDeleteStopReader(ROOT)
    began = time.perf_counter()
    arms = []

    def cancel():
        stop()
        if time.perf_counter() - began >= 300:
            raise BudgetEnd("cost-scan whole-run cap")

    with (OUT / "queries.jsonl").open("x", encoding="utf-8") as query_out, \
         (OUT / "episodes.jsonl").open("x", encoding="utf-8") as episode_out:
        for rule_id in range(271001, 271005):
            if time.perf_counter() - began >= 300:
                break
            compiled = compile_ruleset_for_execution(ruleset_from_dict(json.loads(
                (ROOT / f"results/dev_aux/task2525/rules-{rule_id}.json").read_text())))
            panel = [root for root in roots if root["rule"] == rule_id]
            rng = random.Random(1407393461)
            dimension = len(panel[0]["channels"])
            model = unchanged_model([1.] + [rng.uniform(.5, 1.5) for _ in range(dimension-1)])
            initial = list(model.weights)
            foe = unchanged_model([1.] * dimension)
            counts = Counter()
            arm_began = time.perf_counter()
            for index in range(256):
                if counts["nodes"] >= 80000 or time.perf_counter()-began >= 300:
                    break
                root = panel[index % 2]
                color = index % 2
                env = FixedScaleSessionEnv(GameSession.replay(compiled,
                    deserialize_game_record(json.dumps(root["record"]))))
                td = unchanged_learner()
                episode_queries = 0
                episode_began = time.perf_counter()
                for ply in range(512):
                    if env.terminal() is not None or counts["nodes"] >= 80000 or time.perf_counter()-began >= 300:
                        break
                    actor = env.player()
                    current = model if actor == color else foe
                    before, state = env.record(), env.session.state
                    weights = list(current.weights)
                    request = min(2048, 80000-counts["nodes"])
                    receipt = AlphaBeta(2, 0).search(env, current, nodes=request,
                        seconds=min(2., max(.000001, 300-(time.perf_counter()-began))),
                        seed=2621200 + rule_id*1000000 + index*1000 + ply, cancel=cancel)
                    if env.record() != before or env.session.state != state:
                        raise AssertionError("cost scan search mutated its full input history")
                    counts["nodes"] += receipt.nodes
                    counts["candidate_nodes" if actor == color else "foe_nodes"] += receipt.nodes
                    counts["queries"] += 1
                    episode_queries += 1
                    if receipt.complete:
                        if actor == color:
                            td.observe(model, receipt)
                        env.push(receipt.action)
                    query_out.write(json.dumps(dict(rule=rule_id, episode=index, ply=ply,
                        actor=actor, learner_color=color, weights_before_search=weights,
                        record_before=before, record_after=env.record(), complete=receipt.complete,
                        nodes=receipt.nodes, requested_nodes=request, seconds=receipt.seconds,
                        value=receipt.value, pv_phi=receipt.pv_phi, pv_terminal=receipt.pv_terminal),
                        sort_keys=True) + "\n")
                    query_out.flush()
                    if not receipt.complete:
                        counts["incomplete_searches"] += 1
                        break
                actual = env.terminal()
                env.replay()
                stats = td.finish(model, actual)
                counts["episodes"] += 1
                counts["actual_terminal" if actual is not None else "UNKNOWN"] += 1
                counts["nonzero_updates"] += bool(stats["changed"])
                episode_out.write(json.dumps(dict(rule=rule_id, episode=index,
                    actual_outcome=actual, stats=stats, final_record=env.record(),
                    final_weights=model.weights, queries=episode_queries,
                    seconds=time.perf_counter()-episode_began), sort_keys=True) + "\n")
                episode_out.flush()
            arms.append(dict(rule=rule_id, counts=dict(counts), seconds=time.perf_counter()-arm_began,
                initial_weights=initial, final_weights=model.weights,
                status="NODE_CAP" if counts["nodes"] == 80000 else "TIME_CAP" if time.perf_counter()-began >= 300 else "EPISODE_CAP"))
            if model.weights[0] != 1. or model.scale != 10. or counts["nodes"] > 80000:
                raise AssertionError("fixed scale/node accounting failed")
    result = dict(status="COST_ONLY_COMPLETE" if len(arms)==4 and all(a["status"]=="NODE_CAP" for a in arms) else "COST_ONLY_PARTIAL",
        arms=arms, nodes=sum(a["counts"]["nodes"] for a in arms), seconds=time.perf_counter()-began,
        expected_arms=4, strength_comparison=False, no_heldout_claim=True,
        limitation="Small cost-only repeated development-root workload; not a long-run runtime guarantee, learning benefit, or full-domain validation")
    dump("result.json", result)
    return result


if __name__ == "__main__":
    result = run()
    print(json.dumps({k: v for k, v in result.items() if k != "arms"}, indent=2))
