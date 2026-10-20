"""Finite unpruned witnesses for training/deployment search compatibility.

Training AlphaBeta uses a traversal RNG; deployment TrainingSearch uses a
path-hashed RNG. Verify the first complete saved query per seed/endpoint/actor
against an exhaustive D2 value/action-set oracle. Tied choices are not gains.
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path
import time

from results.dev_aux.task2392.reader import SharedDeleteStopReader
from results.dev_aux.task2492.learning import AlphaBeta, Model, MATE
from results.dev_aux.task2565.train import restore
from tools.local_agent.environment import require_identity

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "results/dev_aux/task2620"
OUT = TASK / "search-boundary"


def dump(name, value):
    with (OUT / name).open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def verify():
    require_identity()
    if OUT.exists():
        raise FileExistsError("search-boundary verifier is one-shot")
    selection = json.loads((TASK / "query-replay/registration.json").read_text())
    replay = json.loads((TASK / "query-replay/result.json").read_text())
    if replay["status"] != "PASS":
        raise ValueError("verify the saved deployment queries first")
    samples = [sample for sample in selection["samples"] if sample["query"]["complete"]]
    if len(samples) != 32:
        raise ValueError("expected all32 seed/endpoint/actor complete-query witnesses")
    OUT.mkdir()
    dump("registration.json", dict(registered_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        sample_rule="All32 first-complete saved queries in the existing pre-verification sample; no outcome selection",
        source_prefix_sha256=selection["source_prefix_sha256"], hard_seconds=180,
        exhaustive_node_cap=1000000, hypothesis="Same complete D2 minimax value and legal optimal-action set despite different ordering/tie choices",
        decision_if_fail="Diagnose concrete training/deployment search discrepancy before new learner comparisons",
        decision_if_pass="Retain finite semantic compatibility; report ordering-policy shift and do not call tie changes benefits",
        new_evaluation_labels=0))
    began = time.perf_counter()
    stop = SharedDeleteStopReader(ROOT)
    exhaustive_nodes = 0
    search_nodes = 0
    witnesses = []

    def cancel():
        stop()
        if time.perf_counter() - began >= 180:
            raise TimeoutError("search-boundary verifier reached its180-second cap")

    def minimax(env, model, depth):
        nonlocal exhaustive_nodes
        exhaustive_nodes += 1
        if exhaustive_nodes > 1000000:
            raise TimeoutError("exhaustive witness cap reached")
        cancel()
        terminal = env.terminal()
        if terminal is not None:
            return MATE * terminal
        if depth == 0:
            return model.raw(env.features())
        values = []
        for action in env.actions():
            env.push(action)
            try:
                values.append(minimax(env, model, depth - 1))
            finally:
                env.pop()
        return max(values) if env.player() == 0 else min(values)

    status, failure = "PASS", None
    try:
        for sample in samples:
            cancel()
            q = sample["query"]
            env = restore(0, None, q["record_before"])
            model = Model(q["weights"])
            values = {}
            own = env.player() == 0
            for action in env.actions():
                env.push(action)
                try:
                    values[action.uci()] = minimax(env, model, 1)
                finally:
                    env.pop()
            best = max(values.values()) if own else min(values.values())
            optimal = sorted(action for action, value in values.items() if value == best)
            if q["value"] != best or q["action"] not in optimal:
                raise ValueError("deployment complete query differs from exhaustive D2 witness")
            receipt = AlphaBeta(2, 0).search(env, model, nodes=q["effective_nodes"],
                seconds=q["effective_seconds"], seed=q["ordering_seed"], cancel=cancel)
            search_nodes += receipt.nodes
            if not receipt.complete:
                raise TimeoutError("training search resource limit differs; preserve unresolved witness")
            if receipt.value != best or receipt.action.uci() not in optimal:
                raise ValueError("training complete query differs from exhaustive D2 witness")
            if env.record() != q["record_before"]:
                raise ValueError("search-boundary verifier mutated input history")
            witnesses.append(dict(source_line=sample["line_number"], seed_index=q["slot"][0],
                endpoint=q["endpoint"], actor=q["actor"], value=best, optimal_actions=optimal,
                deployment_action=q["action"], training_action=receipt.action.uci(),
                different_tied_choices=receipt.action.uci() != q["action"]))
    except TimeoutError as error:
        status, failure = "UNRESOLVED_CAPPED_OR_TIME_DEPENDENT", str(error)
    except Exception as error:
        status, failure = "FAIL", type(error).__name__ + ": " + str(error)
    result = dict(status=status, failure=failure, witnesses=witnesses,
        completed=len(witnesses), different_tied_choices=sum(w["different_tied_choices"] for w in witnesses),
        exhaustive_nodes=exhaustive_nodes, training_search_verifier_nodes=search_nodes,
        seconds=time.perf_counter()-began, new_evaluation_labels=0,
        limitation="Finite complete-query semantic witnesses only. Training/deployment ordering policies differ; no all-state equivalence or strength claim.")
    dump("result.json", result)
    return result


if __name__ == "__main__":
    result = verify()
    print(json.dumps({key: value for key, value in result.items() if key != "witnesses"}, indent=2))
