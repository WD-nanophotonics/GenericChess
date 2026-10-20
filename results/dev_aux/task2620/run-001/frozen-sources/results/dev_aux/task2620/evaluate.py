"""Independent fixed-model Chess evaluation; task2618 is immutable history."""
from __future__ import annotations
from collections import Counter
import datetime, hashlib, json, time
from pathlib import Path
import chess
from results.dev_aux.task2392.reader import SharedDeleteStopReader
from results.dev_aux.task2492.learning import Model
from results.dev_aux.task2504.search import TrainingSearch
from results.dev_aux.task2565.train import restore
from results.dev_aux.task2618.evaluate_learners import verify_training_result, learner_reward, finite_reward_bounds
from tools.local_agent.environment import require_identity
ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT/'results/dev_aux/task2620/run-001'


def sha(data): return hashlib.sha256(data).hexdigest()


def evaluate():
    require_identity()
    for name in ('evaluation-started.json','evaluation-games.jsonl','evaluation-queries.jsonl','evaluation-result.json'):
        if (RUN/name).exists(): raise FileExistsError('no rerun/top-up: '+name)
    plan_raw=(RUN/'plan.json').read_bytes();plan=json.loads(plan_raw)
    reg_raw=(RUN/'registration.json').read_bytes();registration=json.loads(reg_raw)
    if registration['status']!='REGISTERED_PRE_EVALUATION' or registration['plan_sha256']!=sha(plan_raw):
        raise ValueError('pre-search registration mismatch')
    for name,digest in plan['source_sha256'].items():
        if sha((ROOT/name).read_bytes())!=digest: raise ValueError('source changed: '+name)
    if chess.__version__!=plan['python_chess_version']: raise ValueError('runtime changed')
    training_raw=(RUN/'training-result.json').read_bytes();training=json.loads(training_raw)
    if sha(training_raw)!=plan['training_result_sha256']: raise ValueError('training result changed')
    original_raw=(ROOT/plan['training_plan_path']).read_bytes()
    if sha(original_raw)!=plan['training_plan_sha256']: raise ValueError('original training plan changed')
    arms=verify_training_result(json.loads(original_raw),training,sha(original_raw))
    initial_by_seed={int(arm['seed']):arm['initial_weights'] for arm in training['arms']}
    roots_raw=(RUN/'evaluation-root-manifest.json').read_bytes()
    if sha(roots_raw)!=plan['evaluation_root_manifest_sha256']: raise ValueError('roots changed')
    roots_doc=json.loads(roots_raw);root_by_family={row['family']:row['record'] for row in roots_doc['roots']}
    if len(root_by_family)!=plan['evaluation']['root_count']: raise ValueError('root count')
    slots=plan['evaluation']['ordered_slots']
    if len(slots)!=plan['evaluation']['expected_slots'] or len({tuple(s) for s in slots})!=len(slots):
        raise ValueError('incomplete/duplicate slot manifest')
    caps_by_family=plan['evaluation']['caps_by_family'];cap_values=set(plan['evaluation']['cap_values_nodes_both_sides'])
    if set(map(int,caps_by_family))!=set(root_by_family): raise ValueError('root cap mapping')
    session=json.loads((ROOT/'.local_agent/session.json').read_text(encoding='utf-8'))
    if session['state']!='active': raise ValueError('need an actual active research session at launch')
    stop=SharedDeleteStopReader(ROOT);stop()
    began=time.perf_counter()
    registered=datetime.datetime.fromisoformat(plan['preparation_started_at'])
    def remaining():
        total_left=plan['all_in_hard_cap_seconds']-(datetime.datetime.now(datetime.timezone.utc)-registered).total_seconds()
        return min(plan['evaluation']['hard_cap_seconds']-(time.perf_counter()-began),total_left)
    if remaining()<=0: raise ValueError('expired new experiment cap; preserve missing slots')
    started_record=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        plan_sha256=sha(plan_raw),registration_sha256=sha(reg_raw),
        training_result_sha256=sha(training_raw),source_sha256=plan['source_sha256'],
        registration_session_id=plan['session_id'],launch_session_id=session['id'])
    with (RUN/'evaluation-started.json').open('x',encoding='utf-8') as stream:
        stream.write(json.dumps(started_record,indent=2,sort_keys=True)+'\n')
    counters = Counter()
    games = []
    status = "COMPLETE"
    with (RUN / "evaluation-games.jsonl").open("x", encoding="utf-8") as games_out, \
         (RUN / "evaluation-queries.jsonl").open("x", encoding="utf-8") as queries_out:
        for slot_index, slot in enumerate(slots):
            stop()
            seed_index, seed, family, learner_color, endpoint = slot
            if remaining() <= 0:
                status = "PARTIAL_GLOBAL_CAP"
                break
            if endpoint == "initial":
                weights = initial_by_seed[seed]
            else:
                weights = arms[(seed_index, endpoint)]["final_weights"]
            learner = Model(weights)
            foe = Model(plan["fixed_foe_weights"])
            record = root_by_family[family]
            env = restore(0, None, record)
            if env.record() != record or env.terminal() is not None:
                raise ValueError(f"evaluation root failed exact replay: {family}")
            initial_record = env.record()
            nodes = searches = 0
            ending = "HORIZON_UNKNOWN"
            effective_slot_cap = caps_by_family[str(family)]
            if effective_slot_cap not in cap_values:
                raise ValueError(f"unregistered evaluation cap for family {family}")
            outcome = None
            for ply in range(plan["evaluation"]["max_plies_per_game"]):
                stop()
                outcome = env.terminal()
                if outcome is not None:
                    ending = "ACTUAL_TERMINAL"
                    break
                global_left = remaining()
                slot_left = effective_slot_cap - nodes
                if global_left <= 0:
                    status, ending = "PARTIAL_GLOBAL_CAP", "GLOBAL_CAP_UNKNOWN"
                    break
                if slot_left <= 0:
                    ending = "SLOT_NODE_CAP_UNKNOWN"
                    break
                actor = env.player()
                candidate_turn = actor == learner_color
                current = learner if candidate_turn else foe
                record_before = env.record()
                query_nodes = min(plan["evaluation"]["nodes_per_search"], slot_left)
                query_seconds = min(plan["evaluation"]["seconds_per_search"], global_left)
                ordering_seed = plan["evaluation"]["ordering_seed_base"] + seed * 1_000_000 + family * 1_000 + ply
                receipt = TrainingSearch(
                    plan["evaluation"]["depth"], quiet=False,
                    q_limit=plan["evaluation"]["q_limit"],
                ).search(env, current, nodes=query_nodes, seconds=query_seconds,
                         seed=ordering_seed, cancel=stop)
                if env.record() != record_before:
                    raise AssertionError("evaluation search mutated the board/history")
                if receipt.nodes < 0 or receipt.nodes > query_nodes:
                    raise AssertionError("evaluation search exceeded its requested node limit")
                nodes += receipt.nodes
                searches += 1
                if receipt.complete:
                    env.push(receipt.action)
                query = {
                    "slot_index": slot_index,
                    "slot": slot,
                    "family_cap_nodes_both_sides": effective_slot_cap,
                    "ply": ply,
                    "actor": actor,
                    "learner_color": learner_color,
                    "endpoint": endpoint,
                    "weights": list(current.weights),
                    "record_before": record_before,
                    "record_after": env.record(),
                    "complete": receipt.complete,
                    "action": None if not receipt.complete else receipt.action.uci(),
                    "value": receipt.value,
                    "nodes": receipt.nodes,
                    "total_slot_nodes_both_sides": nodes,
                    "seconds": receipt.seconds,
                    "effective_nodes": query_nodes,
                    "effective_seconds": query_seconds,
                    "ordering_seed": ordering_seed,
                    "search_stats": receipt.reason,
                }
                queries_out.write(json.dumps(query, sort_keys=True, allow_nan=False) + "\n")
                queries_out.flush()
                if not receipt.complete:
                    ending = "SEARCH_RESOURCE_UNKNOWN"
                    break
            outcome = env.terminal()
            if outcome is not None:
                ending = "ACTUAL_TERMINAL"
            replay = restore(0, None, env.record())
            if replay.record() != env.record() or replay.terminal() != outcome:
                raise AssertionError("evaluation game failed full-history Chess replay")
            row = {
                "slot_index": slot_index,
                "slot": slot,
                "family_cap_nodes_both_sides": effective_slot_cap,
                "endpoint": endpoint,
                "seed": seed,
                "seed_index": seed_index,
                "family": family,
                "learner_color": learner_color,
                "weights": list(weights),
                "initial_record": initial_record,
                "final_record": env.record(),
                "outcome_white_relative": outcome,
                "learner_reward": learner_reward(outcome, learner_color),
                "reward_bounds": list(finite_reward_bounds(outcome, learner_color)),
                "unknown_is_draw": False,
                "ending": ending,
                "nodes": nodes,
                "searches": searches,
            }
            games.append(row)
            games_out.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
            games_out.flush()
            counters.update(actual_terminal=outcome is not None, unknown=outcome is None, nodes=nodes, queries=searches)
            if status != "COMPLETE":
                break

    seen = {row["slot_index"] for row in games}
    missing = [index for index in range(len(slots)) if index not in seen]
    result = {
        "task": plan["task"],
        "status": status,
        "expected_slots": len(slots),
        "actual_slots": len(games),
        "missing_slots": missing,
        "actual_terminal": counters["actual_terminal"],
        "unknown": counters["unknown"],
        "nodes": counters["nodes"],
        "queries": counters["queries"],
        "seconds": time.perf_counter() - began,
        "unknown_is_draw": False,
        "all_slots_recorded_or_explicitly_missing": len(games) + len(missing) == len(slots),
        "training_result_sha256": sha(training_raw),
        "plan_sha256": sha(plan_raw),
        "interpretation": "Finite held-out-in-input exact-history Chess start panel against one fixed foe; terminal W/D/L only. Exact start disjointness does not establish descendant/transposition or population independence.",
    }
    with (RUN / "evaluation-result.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


if __name__=='__main__':
    print(json.dumps(evaluate(),indent=2,sort_keys=True))
