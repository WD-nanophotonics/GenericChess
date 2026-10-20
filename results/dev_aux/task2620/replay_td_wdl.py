"""Bounded independent source reconstruction of frozen TDLeaf and WDL arms.

All existing rows/seeds are verified, never replaced. No new training or
evaluation labels are emitted. Together with the TreeStrap verifier this checks
the complete12M-node comparison at a separately declared verification cost.
"""
from __future__ import annotations

from collections import Counter
import datetime
import hashlib
import json
from pathlib import Path
import time

from results.dev_aux.task2392.reader import SharedDeleteStopReader
from results.dev_aux.task2492.episode import TDLeafEpisode
from results.dev_aux.task2492.learning import AlphaBeta, Model
from results.dev_aux.task2565.train import restore
from results.dev_aux.task2618.train_learners import bound_counts
from results.dev_aux.task2618.wdl_receipt_adapter import EPISODE_ORDER, accept_proposal, propose
from tools.local_agent.environment import require_identity

ROOT = Path(__file__).resolve().parents[3]
TRAIN = ROOT / "results/dev_aux/task2618/learner-comparison-v4"
OUT = ROOT / "results/dev_aux/task2620/td-wdl-source-replay"


def rows(path):
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def dump(name, value):
    with (OUT / name).open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def replay():
    require_identity()
    if OUT.exists():
        raise FileExistsError("TD/WDL verifier is one-shot; no retry/top-up")
    tree_result = json.loads((OUT.parent / "treestrap-source-replay/result.json").read_text())
    if tree_result["status"] != "PASS":
        raise ValueError("finish and assess the first source verifier before more verification")
    plan = json.loads((TRAIN / "plan.json").read_text())
    for name, expected in plan["source_sha256"].items():
        if digest(ROOT / name) != expected:
            raise ValueError("immutable training source changed: " + name)
    training = json.loads((TRAIN / "training-result.json").read_text())
    targets = {(a["method"], a["seed"]): a for a in training["arms"] if a["method"] != "TreeStrap"}
    OUT.mkdir()
    dump("registration.json", dict(
        registered_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        question="Do the other two comparator packages reconstruct their frozen endpoints under the same source-level verification?",
        decision_if_match="All12 frozen arm endpoints have independently reproduced source-search and update provenance",
        decision_if_mismatch="Preserve and diagnose the mismatch before interpreting method-package strength",
        selection="All logged TDLeaf/WDL queries and started games, every seed, original order; no outcome selection",
        hard_seconds=2400, estimated_seconds=1300, hard_search_nodes=8000000,
        whole_three_method_verification_hard_seconds=3600,
        cheaper_alternative="Existing64-query sample and source inspection cannot establish complete TD/WDL endpoint evolution",
        plan_sha256=digest(TRAIN / "plan.json"), training_result_sha256=digest(TRAIN / "training-result.json"),
        queries_sha256=digest(TRAIN / "queries.jsonl"), games_sha256=digest(TRAIN / "games.jsonl"),
        new_training_or_evaluation_labels=0))
    games = {(r["method"], r["seed"], r["game_index"]): r for r in rows(TRAIN / "games.jsonl")
             if r["method"] != "TreeStrap" and not r.get("unstarted")}
    blocks = {(r["seed"], r["round"]): r for r in rows(TRAIN / "proposal-blocks.jsonl")}
    models = {(method, seed): Model(plan["candidate_initial_weights_by_seed"][str(seed)])
              for method, seed in targets}
    td_config = plan["learner_parameters"]["TDLeaf"]
    td = {seed: TDLeafEpisode(td_config["eta"], td_config["lambda"]) for seed in plan["seeds"]}
    pending = {seed: [] for seed in plan["seeds"]}
    proposal = {}
    foe = Model(plan["fixed_foe_weights"])
    stop = SharedDeleteStopReader(ROOT)
    began = time.perf_counter()
    total_nodes = 0
    counts = Counter()
    per_arm = {key: Counter() for key in targets}
    active = None
    env = candidate = None
    game_nodes = game_queries = 0

    def cancel():
        stop()
        if time.perf_counter() - began >= 2400:
            raise TimeoutError("source verifier reached its2400-second cap")

    def close_game(key):
        if key is None:
            return
        method, seed, game_index = key
        game = games[key]
        outcome = env.terminal()
        if (env.record() != game["final_record"] or outcome != game["outcome_white_relative"]
                or game_nodes != game["episode_nodes"] or game_queries != game["searches"]):
            raise ValueError("game final history/outcome/node mismatch: " + str(key))
        if method == "TDLeaf":
            stats = td[seed].finish(candidate, outcome)
            if stats != game["td_terminal_stats"]:
                raise ValueError("TD episode update/censoring telemetry mismatch")
        else:
            round_index, slot = divmod(game_index, 4)
            variant, color = EPISODE_ORDER[slot]
            if game["variant"] != variant or game["learner_color"] != color:
                raise ValueError("WDL paired episode order mismatch")
            root_key = hashlib.sha256(json.dumps(game["initial_record"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            pending[seed].append(dict(variant=variant, color=color, white_outcome=outcome, root_key=root_key))
            if slot == 3:
                accepted, interval = accept_proposal(pending[seed])
                block = blocks[(seed, round_index)]
                if (accepted != block["accepted"] or list(interval) != block["interval_proposal_minus_incumbent"]
                        or proposal[seed].weights != block["proposal_weights"]):
                    raise ValueError("WDL proposal/paired acceptance mismatch")
                if accepted:
                    models[(method, seed)] = Model(proposal[seed].weights)
                if models[(method, seed)].weights != block["incumbent_weights_after"]:
                    raise ValueError("WDL incumbent carry mismatch")
                pending[seed] = []
                counts["completed_wdl_blocks"] += 1
        if candidate.weights != game["weights_at_episode_end"]:
            raise ValueError("episode endpoint weights mismatch")
        counts["games"] += 1
        per_arm[(method, seed)]["games"] += 1

    status, failure = "PASS", None
    with (OUT / "progress.jsonl").open("x", encoding="utf-8") as progress:
        try:
            for q in rows(TRAIN / "queries.jsonl"):
                if q["method"] == "TreeStrap":
                    continue
                cancel()
                key = q["method"], q["seed"], q["game_index"]
                method, seed, game_index = key
                if key != active:
                    close_game(active)
                    active = key
                    game = games[key]
                    env = restore(0, None, game["initial_record"])
                    game_nodes = game_queries = 0
                    if method == "TDLeaf":
                        candidate = models[(method, seed)]
                        td[seed].reset()
                    else:
                        round_index, slot = divmod(game_index, 4)
                        if slot == 0:
                            if pending[seed]:
                                raise ValueError("WDL started a new round with unclosed slots")
                            proposal[seed] = Model(propose(models[(method, seed)].weights, seed, round_index))
                        candidate = (proposal[seed] if EPISODE_ORDER[slot][0] == "proposal"
                                     else models[(method, seed)])
                    if candidate.weights != game["weights_at_episode_start"]:
                        raise ValueError("episode starting model mismatch: " + str(key))
                if env.record() != q["record_before"] or env.player() != q["actor"]:
                    raise ValueError("query full-history/actor mismatch")
                model = candidate if q["candidate_turn"] else foe
                if model.weights != q["weights_before_search"]:
                    raise ValueError("logged TD/WDL pre-search model mismatch")
                receipt = AlphaBeta(plan["search"]["depth"], plan["search"]["qdepth"]).search(
                    env, model, nodes=q["effective_nodes"], seconds=q["effective_seconds"],
                    seed=q["ordering_seed"], cancel=cancel)
                total_nodes += receipt.nodes
                if total_nodes > 8000000:
                    raise ValueError("verifier exceeded its separate8M-node budget")
                observed = (receipt.complete, receipt.nodes, receipt.action.uci() if receipt.complete else None,
                            receipt.value, list(receipt.pv_phi) if receipt.pv_phi is not None else None,
                            receipt.pv_terminal, bound_counts(receipt))
                expected = (q["complete"], q["nodes"], q["action"], q["value"], q["pv_phi"],
                            q["pv_terminal"], q["search_bound_sample_counts"])
                if observed != expected:
                    time_sensitive = ((not receipt.complete and receipt.nodes < q["effective_nodes"])
                                      or (not q["complete"] and q["nodes"] < q["effective_nodes"]))
                    if time_sensitive:
                        raise TimeoutError("source search timing differs; no retry")
                    raise ValueError("source search action/value/nodes/PV/bounds mismatch")
                if method == "TDLeaf" and q["candidate_turn"] and receipt.complete:
                    td[seed].observe(candidate, receipt)
                if receipt.complete:
                    env.push(receipt.action)
                if env.record() != q["record_after"]:
                    raise ValueError("query post-action history mismatch")
                game_nodes += receipt.nodes
                game_queries += 1
                counts["queries"] += 1
                per_arm[(method, seed)]["queries"] += 1
                per_arm[(method, seed)]["nodes"] += receipt.nodes
                if counts["queries"] % 1000 == 0:
                    progress.write(json.dumps(dict(queries=counts["queries"], nodes=total_nodes,
                                                   seconds=time.perf_counter()-began,
                                                   method=method, seed=seed, game_index=game_index)) + "\n")
                    progress.flush()
            close_game(active)
            for seed, items in pending.items():
                if items:
                    last_index = max(index for method, seen_seed, index in games
                                     if method == "WDL" and seen_seed == seed)
                    block = blocks[(seed, last_index // 4)]
                    if (block["status"] != "INCOMPLETE_PAIRED_BLOCK_CENSORED"
                            or block["accepted"] is not False
                            or block["interval_proposal_minus_incumbent"] is not None
                            or block["started_slots"] != len(items)
                            or block["incumbent_weights_after"] != models[("WDL", seed)].weights):
                        raise ValueError("incomplete WDL block was not preserved as censored")
            for key, target in targets.items():
                if models[key].weights != target["final_weights"] or per_arm[key]["nodes"] != target["nodes_total"]:
                    raise ValueError("frozen endpoint model/node mismatch: " + str(key))
        except TimeoutError as error:
            status, failure = "UNRESOLVED_CAPPED_OR_TIME_DEPENDENT", str(error)
        except Exception as error:
            status, failure = "FAIL", type(error).__name__ + ": " + str(error)
    result = dict(status=status, failure=failure, queries_checked=counts["queries"],
                  games_checked=counts["games"], completed_wdl_blocks=counts["completed_wdl_blocks"],
                  verifier_paid_nodes=total_nodes, verifier_seconds=time.perf_counter()-began,
                  all_eight_endpoints_reconstructed=status == "PASS",
                  per_arm={f"{key[0]}:{key[1]}": dict(value) for key, value in per_arm.items()},
                  frozen_models_changed=False, original_training_rows_replaced=0,
                  new_training_or_evaluation_labels=0,
                  limitation="Exact source/receipt endpoint reconstruction for these seeds, not convergence or population strength evidence.")
    dump("result.json", result)
    return result


if __name__ == "__main__":
    print(json.dumps(replay(), indent=2, sort_keys=True))
