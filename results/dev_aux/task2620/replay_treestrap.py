"""Independently reconstruct all frozen TreeStrap endpoints from source search.

This is a verifier of existing receipts, not training, a retry, new fitness,
or a replacement for any original row. The original source/plan/model remain
unchanged. A one-shot 1200-second/4M-node ceiling bounds added verification.
"""
from __future__ import annotations

from collections import Counter
import datetime
import hashlib
import json
from pathlib import Path
import time

from results.dev_aux.task2392.reader import SharedDeleteStopReader
from results.dev_aux.task2492.learning import AlphaBeta, Model, TreeStrap
from results.dev_aux.task2565.train import restore
from results.dev_aux.task2618.train_learners import bound_counts
from tools.local_agent.environment import require_identity

ROOT = Path(__file__).resolve().parents[3]
TRAIN = ROOT / "results/dev_aux/task2618/learner-comparison-v4"
OUT = ROOT / "results/dev_aux/task2620/treestrap-source-replay"


def dump(name, value):
    with (OUT / name).open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def rows(path):
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def replay():
    require_identity()
    if OUT.exists():
        raise FileExistsError("endpoint verifier is one-shot; no retry/top-up")
    plan = json.loads((TRAIN / "plan.json").read_text())
    training = json.loads((TRAIN / "training-result.json").read_text())
    for name, expected in plan["source_sha256"].items():
        if digest(ROOT / name) != expected:
            raise ValueError("immutable training source changed: " + name)
    OUT.mkdir()
    dump("registration.json", dict(
        registered_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        question="Does source replay recover all four existing TreeStrap endpoint models despite the post-update telemetry name?",
        decision_if_match="Endpoints have independent source-execution provenance; telemetry field still needs future correction",
        decision_if_mismatch="Do not treat the frozen TreeStrap endpoint as independently reconstructed; diagnose against exact source receipts",
        selection="All logged TreeStrap queries, all seeds, in their original order; no outcome/weight selection",
        hard_seconds=1200, estimated_seconds=900, hard_search_nodes=4000000,
        cheaper_alternative="Four first-changed queries already matched, but do not verify complete endpoint evolution",
        plan_sha256=digest(TRAIN / "plan.json"),
        training_result_sha256=digest(TRAIN / "training-result.json"),
        query_sha256=digest(TRAIN / "queries.jsonl"),
        game_sha256=digest(TRAIN / "games.jsonl"),
        new_evaluation_labels=0, not_a_training_retry=True))
    games = {(r["seed"], r["game_index"]): r for r in rows(TRAIN / "games.jsonl")
             if r["method"] == "TreeStrap" and not r.get("unstarted")}
    targets = {a["seed"]: a for a in training["arms"] if a["method"] == "TreeStrap"}
    models = {seed: Model(plan["candidate_initial_weights_by_seed"][str(seed)])
              for seed in plan["seeds"]}
    learner = TreeStrap(plan["learner_parameters"]["TreeStrap"]["eta"])
    foe = Model(plan["fixed_foe_weights"])
    stop = SharedDeleteStopReader(ROOT)
    began = time.perf_counter()
    total_nodes = 0
    counts = Counter()
    per_seed = {seed: Counter() for seed in plan["seeds"]}
    active = None
    env = None
    game_nodes = game_queries = 0
    status = "PASS"
    failure = None

    def cancel():
        stop()
        if time.perf_counter() - began >= 1200:
            raise TimeoutError("endpoint verifier reached its1200-second cap")

    def close_game(key):
        if key is None:
            return
        row = games[key]
        if (env.record() != row["final_record"] or env.terminal() != row["outcome_white_relative"]
                or models[key[0]].weights != row["weights_at_episode_end"]
                or game_nodes != row["episode_nodes"] or game_queries != row["searches"]):
            raise ValueError("TreeStrap episode final history/model/node mismatch: " + str(key))
        counts["games"] += 1
        per_seed[key[0]]["games"] += 1

    with (OUT / "progress.jsonl").open("x", encoding="utf-8") as progress:
        try:
            for q in rows(TRAIN / "queries.jsonl"):
                if q["method"] != "TreeStrap":
                    continue
                cancel()
                key = (q["seed"], q["game_index"])
                if key != active:
                    close_game(active)
                    active = key
                    game = games[key]
                    env = restore(0, None, game["initial_record"])
                    game_nodes = game_queries = 0
                    if models[key[0]].weights != game["weights_at_episode_start"]:
                        raise ValueError("episode starting model mismatch: " + str(key))
                if env.record() != q["record_before"] or env.player() != q["actor"]:
                    raise ValueError("query history/actor mismatch")
                model = models[key[0]] if q["candidate_turn"] else foe
                receipt = AlphaBeta(plan["search"]["depth"], plan["search"]["qdepth"]).search(
                    env, model, nodes=q["effective_nodes"], seconds=q["effective_seconds"],
                    seed=q["ordering_seed"], cancel=cancel)
                total_nodes += receipt.nodes
                if total_nodes > 4000000:
                    raise ValueError("source verifier exceeded its separate4M-node budget")
                if env.record() != q["record_before"]:
                    raise ValueError("search mutated full history")
                observed = (receipt.complete, receipt.nodes,
                            receipt.action.uci() if receipt.complete else None,
                            receipt.value, list(receipt.pv_phi) if receipt.pv_phi is not None else None,
                            receipt.pv_terminal, bound_counts(receipt))
                expected = (q["complete"], q["nodes"], q["action"], q["value"], q["pv_phi"],
                            q["pv_terminal"], q["search_bound_sample_counts"])
                if observed != expected:
                    time_sensitive = ((not receipt.complete and receipt.nodes < q["effective_nodes"])
                                      or (not q["complete"] and q["nodes"] < q["effective_nodes"]))
                    if time_sensitive:
                        raise TimeoutError("search timing differs; no retry or invented exact match")
                    raise ValueError("source search action/value/nodes/PV/bounds mismatch")
                stats = dict(samples=0, active=0, loss=None)
                if receipt.complete and q["candidate_turn"]:
                    stats = learner.update(model, receipt)
                # Historical field is post-update for TreeStrap candidate turns.
                if model.weights != q["weights_before_search"]:
                    raise ValueError("post-update model does not match historical telemetry")
                if (stats["samples"] != q["tree_samples"] or stats["active"] != q["tree_active_samples"]
                        or stats["loss"] != q["training_loss"]):
                    raise ValueError("TreeStrap sample/active/loss telemetry mismatch")
                if receipt.complete:
                    env.push(receipt.action)
                if env.record() != q["record_after"]:
                    raise ValueError("post-action history mismatch")
                game_nodes += receipt.nodes
                game_queries += 1
                counts["queries"] += 1
                per_seed[key[0]]["queries"] += 1
                per_seed[key[0]]["nodes"] += receipt.nodes
                if counts["queries"] % 1000 == 0:
                    progress.write(json.dumps(dict(queries=counts["queries"], nodes=total_nodes,
                                                   seconds=time.perf_counter()-began,
                                                   seed=key[0], game_index=key[1])) + "\n")
                    progress.flush()
            close_game(active)
            for seed, target in targets.items():
                if models[seed].weights != target["final_weights"]:
                    raise ValueError("frozen endpoint model mismatch: " + str(seed))
                if per_seed[seed]["nodes"] != target["nodes_total"]:
                    raise ValueError("frozen endpoint node accounting mismatch")
        except TimeoutError as error:
            status, failure = "UNRESOLVED_CAPPED_OR_TIME_DEPENDENT", str(error)
        except Exception as error:
            status, failure = "FAIL", type(error).__name__ + ": " + str(error)
    result = dict(status=status, failure=failure, queries_checked=counts["queries"],
                  games_checked=counts["games"], verifier_paid_nodes=total_nodes,
                  verifier_seconds=time.perf_counter()-began,
                  all_four_endpoints_reconstructed=status == "PASS",
                  per_seed={str(k): dict(v) for k, v in per_seed.items()},
                  frozen_models_changed=False, original_training_rows_replaced=0,
                  new_evaluation_labels=0,
                  limitation="Exact receipt reconstruction for these four seeds and this pinned source, not convergence or population strength evidence.")
    dump("result.json", result)
    return result


if __name__ == "__main__":
    print(json.dumps(replay(), indent=2, sort_keys=True))
