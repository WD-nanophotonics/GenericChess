"""Independent replay audit for task2623's interrupted, incomplete training stream."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from scripts.generic_session_win_proof import SessionChoice
from results.dev_aux.task2511.generic import NonScoringTerminal
from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv, unchanged_model, unchanged_learner

RUN = ROOT / "results/dev_aux/task2623/run"
RULES = (271001, 271002, 271003, 271004)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path: Path):
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if line.strip():
                try:
                    yield json.loads(line)
                except Exception as exc:
                    raise ValueError(f"{path.name}:{line_number}: invalid JSON row") from exc


def audit() -> dict:
    output = RUN / "partial-training-audit.json"
    if output.exists():
        raise FileExistsError("partial training audit is write-once")
    plan_path, reg_path = RUN / "plan.json", RUN / "registration.json"
    plan, reg = json.loads(plan_path.read_text(encoding="utf-8")), json.loads(reg_path.read_text(encoding="utf-8"))
    if sha(plan_path) != reg["plan_sha256"]:
        raise ValueError("frozen plan hash mismatch")
    for path, expected in reg["source_pins"].items():
        if sha(ROOT / path) != expected:
            raise ValueError(f"registered source changed: {path}")
    if (RUN / "eval-started.json").exists() or (RUN / "eval-result.json").exists():
        raise ValueError("partial training audit must not follow any evaluation")

    pool = json.loads((ROOT / "results/dev_aux/task2622/root-pools-v2.json").read_text(encoding="utf-8"))
    roots = {rule: [row for row in pool["training_roots"] if row["rule"] == rule] for rule in RULES}
    compilers = {rule: compile_ruleset_for_execution(ruleset_from_dict(json.loads(
        (ROOT / f"results/dev_aux/task2525/rules-{rule}.json").read_text(encoding="utf-8")))) for rule in RULES}
    episodes = {(row["rule"], row["seed"], row["episode"]): row for row in read_rows(RUN / "episodes.jsonl")}
    queries = list(read_rows(RUN / "queries.jsonl"))
    if len(episodes) != 1862 or len(queries) != 26176:
        raise ValueError("partial streams differ from the preserved interruption correction")
    if not (RUN / "training-interruption-correction.json").exists():
        raise ValueError("corrected interruption receipt is required")

    seen_arms = []
    for row in queries:
        key = (row["rule"], row["seed"])
        if key not in seen_arms:
            seen_arms.append(key)
    expected_order = [(rule, seed) for rule in RULES for seed in plan["seeds"]]
    if seen_arms != expected_order[:len(seen_arms)]:
        raise ValueError("partial arm order is not a prefix of the frozen rule/seed grid")
    models = {key: unchanged_model(plan["initialization"]["weights_by_rule_seed"][f"{key[0]}:{key[1]}"])
              for key in seen_arms}
    if any(model.fixed != 0 or model.scale != 10.0 or model.weights[0] != 1.0 for model in models.values()):
        raise ValueError("frozen fixed-scale initialization changed")
    counters = {key: Counter() for key in seen_arms}
    active_key = None
    env = td = None
    active_nodes = 0
    active_episode_queries = 0
    last_episode_by_arm = {key: -1 for key in seen_arms}

    def close_episode(key):
        nonlocal env, td, active_nodes, active_episode_queries
        if key is None:
            return
        episode = episodes[key]
        rule, seed, episode_id = key
        try:
            actual = env.terminal()
        except NonScoringTerminal:
            actual = None
        stats = td.finish(models[(rule, seed)], actual)
        env.replay()
        if (env.record() != episode["final_record"] or actual != episode["actual_outcome"]
                or stats != episode["stats"] or models[(rule, seed)].weights != episode["final_weights"]
                or active_nodes != episode["nodes"]):
            raise ValueError(f"episode replay/update mismatch: {key}")
        counts = counters[(rule, seed)]
        counts["closed_episodes"] += 1
        counts["closed_episode_nodes"] += active_nodes
        counts["actual_terminal" if actual is not None else "UNKNOWN"] += 1
        counts["nonzero_updates"] += bool(stats["changed"])
        counts["episode_queries"] += active_episode_queries
        last_episode_by_arm[(rule, seed)] = episode_id
        active_nodes = active_episode_queries = 0

    prior_key = None
    incomplete_seen = False
    trailing_key = (queries[-1]["rule"], queries[-1]["seed"], queries[-1]["episode"])
    if any((q["rule"], q["seed"], q["episode"]) not in episodes
           and (q["rule"], q["seed"], q["episode"]) != trailing_key for q in queries):
        raise ValueError("only the trailing open episode may lack a closure row")
    for q_index, q in enumerate(queries):
        key = (q["rule"], q["seed"], q["episode"])
        if key != active_key:
            if active_key is not None:
                if active_key not in episodes:
                    raise ValueError("an unclosed episode is followed by another episode")
                close_episode(active_key)
            rule, seed, episode_id = key
            expected_episode = last_episode_by_arm[(rule, seed)] + 1
            if episode_id != expected_episode:
                raise ValueError("episode IDs are not contiguous within the observed arm")
            root = roots[rule][episode_id % len(roots[rule])]
            if key in episodes:
                episode = episodes[key]
                if (episode["root_family"] != root["family"] or episode["start_record"] != root["record"]
                        or episode["initial_weights"] != plan["initialization"]["weights_by_rule_seed"][f"{rule}:{seed}"]):
                    raise ValueError("episode root/order/initialization differs from the frozen plan")
            env = FixedScaleSessionEnv(GameSession.replay(compilers[rule],
                deserialize_game_record(json.dumps(root["record"]))))
            if env.record() != root["record"]:
                raise ValueError("training root does not replay exactly")
            td = unchanged_learner()
            active_key, active_nodes, active_episode_queries = key, 0, 0
        rule, seed, episode_id = key
        learner_color = episode_id % 2
        actor = env.player()
        model = models[(rule, seed)]
        if q["learner_color"] != learner_color or q["actor"] != actor or q["learner_turn"] != (actor == learner_color):
            raise ValueError("actor/learner-color contract mismatch")
        if env.record() != q["record_before"]:
            raise ValueError("query full-history pre-state mismatch")
        current = model if actor == learner_color else unchanged_model([1.0] * len(model.weights))
        if current.weights != q["weights_before_search"]:
            raise ValueError("query learner/foe weights mismatch")
        limit = plan["training"]["nodes_per_arm_candidate_plus_foe"]
        arm_nodes_before = counters[(rule, seed)]["closed_episode_nodes"] + active_nodes
        remaining = limit - arm_nodes_before
        if (type(q["nodes"]) is not int or not 0 <= q["nodes"] <= q["requested_nodes"]
                or q["requested_nodes"] != min(plan["search"]["nodes_per_query"], remaining)):
            raise ValueError("query exceeded or misdeclared the frozen candidate-plus-foe budget")
        active_nodes += q["nodes"]
        active_episode_queries += 1
        counters[(rule, seed)]["queries"] += 1
        if not q["complete"]:
            incomplete_seen = True
            if q_index + 1 < len(queries):
                next_q = queries[q_index + 1]
                if (next_q["rule"], next_q["seed"], next_q["episode"]) == key:
                    raise ValueError("incomplete search is followed by another query in the same episode")
        else:
            if actor == learner_color:
                td.observe(model, type("Receipt", (), {"complete": True, "value": q["value"],
                    "pv_terminal": q["pv_terminal"], "pv_phi": q["pv_phi"]})())
            after = deserialize_game_record(json.dumps(q["record_after"]))
            expected_length = len(env.session.to_record().actions) + (1 if q["complete"] else 0)
            if len(after.actions) != expected_length:
                raise ValueError("query action-history length disagrees with completeness")
            if q["complete"]:
                env.push(SessionChoice("ACTION", action=after.actions[-1]))
        if env.record() != q["record_after"]:
            raise ValueError("query full-history post-state mismatch")
        prior_key = key

    if active_key in episodes:
        close_episode(active_key)
        open_episode = None
    else:
        open_episode = {"rule": active_key[0], "seed": active_key[1], "episode": active_key[2],
                        "queries": active_episode_queries, "nodes": active_nodes,
                        "final_record": env.record()}
        counters[(active_key[0], active_key[1])]["open_episode_queries"] += active_episode_queries
        counters[(active_key[0], active_key[1])]["open_episode_nodes"] += active_nodes

    arm_rows = []
    for key in seen_arms:
        counts = counters[key]
        arm_nodes = counts["closed_episode_nodes"] + counts["open_episode_nodes"]
        if arm_nodes > plan["training"]["nodes_per_arm_candidate_plus_foe"]:
            raise ValueError("partial arm exceeded its frozen combined-node cap")
        arm_rows.append({"rule": key[0], "seed": key[1], "nodes": arm_nodes,
                         "queries": counts["queries"], "closed_episodes": counts["closed_episodes"],
                         "actual_terminal": counts["actual_terminal"], "UNKNOWN": counts["UNKNOWN"],
                         "nonzero_updates": counts["nonzero_updates"],
                         "at_registered_cap": arm_nodes == plan["training"]["nodes_per_arm_candidate_plus_foe"]})

    audit = {"status": "PASS_PARTIAL_FULL_HISTORY_TD_UPDATE_AND_CAP_REPLAY",
             "plan_sha256": sha(plan_path), "registration_sha256": sha(reg_path),
             "interruption_correction_sha256": sha(RUN / "training-interruption-correction.json"),
             "queries": len(queries), "episodes": len(episodes),
             "nodes": sum(row["nodes"] for row in queries),
             "candidate_nodes": sum(row["nodes"] for row in queries if row["learner_turn"]),
             "foe_nodes": sum(row["nodes"] for row in queries if not row["learner_turn"]),
             "arms_observed": arm_rows, "open_episode": open_episode,
             "incomplete_search_logged": incomplete_seen,
             "training_complete": False, "evaluation_started": False,
             "scope": "Independent reconstruction of only persisted complete episodes and the trailing open episode; no completion imputation, no missing arms filled, no evaluation or strength conclusion."}
    output.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return audit


if __name__ == "__main__":
    audit()
