"""Replay every Generic cost-scan action and reconstruct TD updates from logs."""
from __future__ import annotations
from collections import Counter
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from scripts.generic_session_win_proof import SessionChoice
from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv, unchanged_model, unchanged_learner

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "results/dev_aux/task2621/cost-scan"


def rows(path):
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def audit():
    output = RUN / "audit.json"
    if output.exists():
        raise FileExistsError("cost audit is write-once")
    result = json.loads((RUN / "result.json").read_text())
    if result["status"] != "COST_ONLY_COMPLETE":
        raise ValueError("preserve partial cost scan before defining a partial audit")
    roots = json.loads((RUN.parent / "active-feature-probe/root-manifest.json").read_text())["roots"]
    models = {arm["rule"]: unchanged_model(arm["initial_weights"]) for arm in result["arms"]}
    foes = {rule: unchanged_model([1.] * len(model.weights)) for rule, model in models.items()}
    compiled = {rule: compile_ruleset_for_execution(ruleset_from_dict(json.loads(
        (ROOT / f"results/dev_aux/task2525/rules-{rule}.json").read_text()))) for rule in models}
    games = {(row["rule"], row["episode"]): row for row in rows(RUN / "episodes.jsonl")}
    counters = {rule: Counter() for rule in models}
    active = None
    env = td = None

    def close_game(key):
        if key is None:
            return
        rule, _index = key
        game = games[key]
        actual = env.terminal()
        stats = td.finish(models[rule], actual)
        if (env.record() != game["final_record"] or actual != game["actual_outcome"]
                or stats != game["stats"] or models[rule].weights != game["final_weights"]):
            raise ValueError("Generic final history/outcome/TD update mismatch")
        env.replay()
        counters[rule]["episodes"] += 1
        counters[rule]["actual_terminal" if actual is not None else "UNKNOWN"] += 1

    for q in rows(RUN / "queries.jsonl"):
        key = q["rule"], q["episode"]
        rule, index = key
        if key != active:
            close_game(active)
            active = key
            root = [row for row in roots if row["rule"] == rule][index % 2]
            env = FixedScaleSessionEnv(GameSession.replay(compiled[rule],
                deserialize_game_record(json.dumps(root["record"]))))
            td = unchanged_learner()
        actor = env.player()
        if actor != q["actor"] or env.record() != q["record_before"]:
            raise ValueError("Generic query actor/history mismatch")
        current = models[rule] if actor == q["learner_color"] else foes[rule]
        if current.weights != q["weights_before_search"]:
            raise ValueError("Generic frozen query weight mismatch")
        if q["requested_nodes"] != min(2048, 80000-counters[rule]["nodes"]):
            raise ValueError("Generic combined budget request mismatch")
        if type(q["nodes"]) is not int or not 0 <= q["nodes"] <= q["requested_nodes"]:
            raise ValueError("Generic query node allowance exceeded")
        counters[rule]["nodes"] += q["nodes"]
        counters[rule]["candidate_nodes" if actor == q["learner_color"] else "foe_nodes"] += q["nodes"]
        counters[rule]["queries"] += 1
        if q["complete"]:
            if actor == q["learner_color"]:
                td.observe(models[rule], SimpleNamespace(complete=True, value=q["value"],
                    pv_terminal=q["pv_terminal"], pv_phi=q["pv_phi"]))
            record = deserialize_game_record(json.dumps(q["record_after"]))
            if len(record.actions) != len(env.session.to_record().actions) + 1:
                raise ValueError("query did not append exactly one actual action")
            env.push(SessionChoice("ACTION", action=record.actions[-1]))
        if env.record() != q["record_after"]:
            raise ValueError("Generic action result/complete-history mismatch")
    close_game(active)
    for arm in result["arms"]:
        rule = arm["rule"]
        if models[rule].weights != arm["final_weights"]:
            raise ValueError("Generic final model mismatch")
        for key in ("nodes", "candidate_nodes", "foe_nodes", "queries", "episodes", "actual_terminal", "UNKNOWN"):
            if counters[rule][key] != arm["counts"].get(key, 0):
                raise ValueError("Generic cost total mismatch: " + key)
    audited = dict(status="PASS", queries=sum(c["queries"] for c in counters.values()),
        episodes=len(games), paid_nodes=sum(c["nodes"] for c in counters.values()),
        action_full_history_replay=True, both_sides_node_accounting=True,
        td_updates_reconstructed_from_logged_receipts=True,
        result_sha256=hashlib.sha256((RUN / "result.json").read_bytes()).hexdigest(),
        scope="Cost-scan record/update audit, not independent recomputation of every search target or a strength evaluation")
    with output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(audited, indent=2, sort_keys=True) + "\n")
    return audited


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2, sort_keys=True))
