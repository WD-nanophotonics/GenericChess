"""Independent full-history, actual-outcome and TD-update audit of training."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from collections import Counter
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from scripts.generic_session_win_proof import SessionChoice
from results.dev_aux.task2511.generic import NonScoringTerminal
from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv, unchanged_model, unchanged_learner

RUN = ROOT / "results/dev_aux/task2622/run"
RULES = (271001, 271002, 271003, 271004)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_rows(path: Path):
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def audit() -> dict:
    out = RUN / "training-audit.json"
    if out.exists():
        raise FileExistsError("training audit is write-once")
    plan_path, reg_path, result_path = RUN / "plan.json", RUN / "registration.json", RUN / "training-result.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if reg["state"] != "REGISTERED_BEFORE_TRAINING_OR_EVALUATION" or result["status"] != "COMPLETE":
        raise ValueError("only a complete registered training run can pass this audit")
    if sha(plan_path.read_bytes()) != reg["plan_sha256"]:
        raise ValueError("registered plan hash mismatch")
    for path, expected in reg["source_pins"].items():
        if sha((ROOT / path).read_bytes()) != expected:
            raise ValueError(f"registered source changed: {path}")

    pool = json.loads((ROOT / "results/dev_aux/task2622/root-pools-v2.json").read_text(encoding="utf-8"))
    roots = {rule: [r for r in pool["training_roots"] if r["rule"] == rule] for rule in RULES}
    compilers = {rule: compile_ruleset_for_execution(ruleset_from_dict(json.loads(
        (ROOT / f"results/dev_aux/task2525/rules-{rule}.json").read_text(encoding="utf-8")))) for rule in RULES}
    arms = {(a["rule"], a["seed"]): a for a in result["arms"]}
    expected_keys = {(rule, seed) for rule in RULES for seed in plan["seeds"]}
    if set(arms) != expected_keys or len(arms) != len(result["arms"]):
        raise ValueError("training arm set is not the exact registered rule/seed grid")
    models = {}
    counters = {key: Counter() for key in arms}
    for key, arm in arms.items():
        rule, seed = key
        if arm["initial_weights"] != plan["initialization"]["weights_by_rule_seed"][f"{rule}:{seed}"]:
            raise ValueError("training arm did not use its exact frozen initialization vector")
        model = unchanged_model(arm["initial_weights"])
        if model.fixed != 0 or model.scale != 10.0 or model.weights[0] != 1.0:
            raise ValueError("registered fixed-scale initialization changed")
        models[key] = model

    episodes = {(row["rule"], row["seed"], row["episode"]): row for row in read_rows(RUN / "episodes.jsonl")}
    if len(episodes) != result["episodes"]:
        raise ValueError("episode receipt count mismatch")
    active_key = None
    env = td = None
    active_query_nodes = 0

    def close_episode(key):
        nonlocal env, td, active_query_nodes
        if key is None:
            return
        rule, seed, episode_id = key
        episode = episodes[key]
        try:
            actual = env.terminal()
        except NonScoringTerminal:
            actual = None
        stats = td.finish(models[(rule, seed)], actual)
        env.replay()
        if (env.record() != episode["final_record"] or actual != episode["actual_outcome"]
                or stats != episode["stats"] or models[(rule, seed)].weights != episode["final_weights"]
                or active_query_nodes != episode["nodes"]):
            raise ValueError("full-history/outcome/TD episode reconstruction mismatch")
        counters[(rule, seed)]["episodes"] += 1
        counters[(rule, seed)]["nodes"] += active_query_nodes
        counters[(rule, seed)]["actual_terminal" if actual is not None else "UNKNOWN"] += 1
        counters[(rule, seed)]["nonzero_updates"] += bool(stats["changed"])
        active_query_nodes = 0

    for q in read_rows(RUN / "queries.jsonl"):
        key = q["rule"], q["seed"], q["episode"]
        if key not in episodes:
            raise ValueError("query has no episode closure")
        if key != active_key:
            close_episode(active_key)
            active_key = key
            rule, seed, index = key
            episode = episodes[key]
            root = roots[rule][index % len(roots[rule])]
            if episode["root_family"] != root["family"] or episode["start_record"] != root["record"]:
                raise ValueError("training episode root selection/order mismatch")
            env = FixedScaleSessionEnv(GameSession.replay(compilers[rule],
                deserialize_game_record(json.dumps(root["record"]))))
            td = unchanged_learner()
        rule, seed, _ = key
        model = models[(rule, seed)]
        actor = env.player()
        learner_color = q["learner_color"]
        if q["actor"] != actor or q["learner_turn"] != (actor == learner_color):
            raise ValueError("actor/learner color mismatch")
        if env.record() != q["record_before"]:
            raise ValueError("query full-history pre-state mismatch")
        current = model if actor == learner_color else unchanged_model([1.0] * len(model.weights))
        if current.weights != q["weights_before_search"]:
            raise ValueError("query model/foe weights mismatch")
        if type(q["nodes"]) is not int or not 0 <= q["nodes"] <= q["requested_nodes"]:
            raise ValueError("query exceeded its requested search budget")
        arm_nodes = counters[(rule, seed)]["nodes"] + active_query_nodes
        remaining = plan["training"]["nodes_per_arm_candidate_plus_foe"] - arm_nodes
        if q["requested_nodes"] != min(plan["search"]["nodes_per_query"], remaining):
            raise ValueError("query request does not match registered arm remainder")
        active_query_nodes += q["nodes"]
        counters[(rule, seed)]["queries"] += 1
        if q["complete"]:
            if actor == learner_color:
                td.observe(model, SimpleNamespace(complete=True, value=q["value"],
                    pv_terminal=q["pv_terminal"], pv_phi=q["pv_phi"]))
            new_record = deserialize_game_record(json.dumps(q["record_after"]))
            if len(new_record.actions) != len(env.session.to_record().actions) + 1:
                raise ValueError("complete query did not append one legal history action")
            env.push(SessionChoice("ACTION", action=new_record.actions[-1]))
        if env.record() != q["record_after"]:
            raise ValueError("query full-history post-state mismatch")
    close_episode(active_key)

    for key, arm in arms.items():
        model = models[key]
        if model.weights != arm["final_weights"]:
            raise ValueError("final reconstructed model differs")
        counts = counters[key]
        if counts["nodes"] != arm["nodes"] or counts["episodes"] != arm["counts"]["episodes"]:
            raise ValueError("arm node/episode totals mismatch")
        if arm["nodes"] != plan["training"]["nodes_per_arm_candidate_plus_foe"]:
            raise ValueError("complete arm did not reach registered combined-node cap")
        if counts["nodes"] > plan["training"]["nodes_per_arm_candidate_plus_foe"]:
            raise ValueError("arm exceeded its registered node cap")
        if model.fixed != 0 or model.scale != 10.0 or model.weights[0] != 1.0:
            raise ValueError("reconstructed model violated fixed scale")

    audited = {"status": "PASS_FULL_HISTORY_ACTUAL_TERMINAL_NODE_CAP_AND_TD_UPDATE_REPLAY",
               "plan_sha256": sha(plan_path.read_bytes()),
               "training_result_sha256": sha(result_path.read_bytes()),
               "queries": result["queries"], "episodes": result["episodes"], "nodes": result["nodes"],
               "actual_terminal": result["actual_terminal"], "UNKNOWN": result["UNKNOWN"],
               "arms": len(arms), "all_arms_at_registered_cap": True,
               "td_updates_reconstructed_from_logged_search_receipts": True,
               "limitation": "Reconstructs learner updates from stored completed search receipts; does not independently rerun every search target or establish Generic population strength."}
    out.write_text(json.dumps(audited, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audited, indent=2, sort_keys=True))
    return audited


if __name__ == "__main__":
    audit()
