"""Partial-result checks for the frozen task2636 evaluation panel.

Structural helpers validate slot identity/complements, endpoint labels, rewards
and caps. ``replay_slot_history`` separately replays a supplied frozen root and
one slot's query chain. Candidate-source/run binding and integration over a
complete result file remain caller responsibilities.
"""
from __future__ import annotations

from collections import defaultdict
import json
import hashlib
import math
import re
import random
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
PLAN_PATH = ROOT / "results/dev_aux/task2636/one-init-study-plan.json"
FROZEN_PLAN_SHA256 = "a3af462f9db4018118619aea9d79374e7e876f83735559d8269a80b506c73c40"
REPLAY_RUNTIME_PINS = {
    "generic_chess/core/movegen.py": "05db961e128965bf7a9ab35e2f797401ae051d7e4c46ce0e9adf6968de27df6a",
    "generic_chess/core/position.py": "dcf28eed63e9ef755e9e6c4da326ff775a5c189f26ad1ff654760f305a420115",
    "generic_chess/core/semantic_executor.py": "119ac83dcd1578245b784d3d5fddd56f2947b7566e291d84fe88fdfab2acb896",
    "generic_chess/core/terminal.py": "55dec55905d51122023efdb1222923dd5b5191c398e7326d7441a77f5efb037e",
    "generic_chess/core/transition.py": "80a01f61bac9db9907326017425da9ac4beec03efa6359a1066492d0f60dd7a8",
    "generic_chess/rules/compiler.py": "9ef2c28c78af75a8642543ef2306645295b10ea55e512d00a35a28b799cb6937",
    "generic_chess/rules/schema.py": "3933bd2ae6289a60fe58e6b349f53733c7bbe11e3766b99485a6c32e91c6c799",
    "generic_chess/session/result.py": "b22aa18484656490d1b8351ff63bc1f70c9c64b74c42adc0cb496d9da8c624c6",
    "generic_chess/session/serialization.py": "159c5e39861d0faba9420ad61c002a3be10c0326bb11aff4a9576825da7c5c50",
    "generic_chess/session/session.py": "1070e555619d244b357a0b3c72c2280b4c0276311ccab02280eae4e2e4c42c4b",
    "results/dev_aux/task2492/adapters.py": "9d91ecd69308d79ff2a257a4addb79c7c6b91f67ec72e5e4173bbf02b4c7955f",
    "results/dev_aux/task2511/generic.py": "ab5f0e58d50bc2c6adb55af438639396dcd3dbf3ad082959852cca89c2389d7e",
    "results/dev_aux/task2621/fixed_scale.py": "c50d5f7fa2e0db755a33ef5c9e4c480ecfb6a99fac3009b13e443800ac251571",
    "scripts/generic_session_win_proof.py": "87d883aaa39505d6f024d5b30b782714003116efa4f57436b0129a7fbfa2b5c3",
}

SlotKey = tuple[int, int, int, str]  # candidate index, family, learner color, endpoint
UNKNOWN_ENDINGS = {
    "HORIZON_UNKNOWN", "NON_SCORING_UNKNOWN", "NODE_CAP_UNKNOWN",
    "TIME_CAP_UNKNOWN", "SEARCH_RESOURCE_UNKNOWN", "STOPPED_USER_UNKNOWN",
}


def expected_slots(plan: dict[str, Any], pool: dict[str, Any]) -> dict[SlotKey, dict[str, int]]:
    """Build the frozen slot universe and bind each slot to seed and node cap."""
    if pool.get("root_pool_registered") or pool.get("learner_or_search_started"):
        raise ValueError("structural audit requires the frozen, unregistered root pool")
    evaluation = plan["evaluation"]
    endpoints = tuple(evaluation["endpoints"])
    colors = tuple(evaluation["learner_colors"])
    roots_per_candidate = evaluation["roots_per_rule"]
    candidate_count = plan["training"]["arms"]
    cap_spec = evaluation["node_cap_assignment"]
    if len(endpoints) != 2 or len(colors) != 2:
        raise ValueError("expected exactly two paired endpoints and two learner colors")
    if not all(token in cap_spec for token in ("20000", "40000", "first eight", "remaining eight")):
        raise ValueError("frozen evaluation cap assignment changed")

    by_candidate: dict[int, list[dict[str, Any]]] = {}
    seed_by_candidate: dict[int, int] = {}
    for root in pool["evaluation_roots"]:
        candidate = root["candidate_index"]
        seed = root["candidate_seed"]
        if candidate in seed_by_candidate and seed_by_candidate[candidate] != seed:
            raise ValueError("candidate seed differs within its evaluation roots")
        seed_by_candidate[candidate] = seed
        by_candidate.setdefault(candidate, []).append(root)
    if set(by_candidate) != set(range(candidate_count)):
        raise ValueError("candidate-index universe differs from the plan")

    result: dict[SlotKey, dict[str, int]] = {}
    for candidate in range(candidate_count):
        roots = by_candidate[candidate]
        if len(roots) != roots_per_candidate:
            raise ValueError(f"candidate {candidate}: evaluation root count mismatch")
        families = [root["family"] for root in roots]
        if len(set(families)) != roots_per_candidate:
            raise ValueError(f"candidate {candidate}: duplicate evaluation family")
        candidate_seed = seed_by_candidate[candidate]
        shuffled = families.copy()
        random.Random(977422 + candidate_seed).shuffle(shuffled)
        caps = {family: (20000 if index < 8 else 40000)
                for index, family in enumerate(shuffled)}
        for family in families:
            for color in colors:
                for endpoint in endpoints:
                    key = (candidate, family, color, endpoint)
                    if key in result:
                        raise ValueError("duplicate frozen evaluation slot")
                    result[key] = {"candidate_seed": candidate_seed, "node_cap": caps[family]}
    if len(result) != evaluation["slots"]:
        raise ValueError("planned slot count differs from frozen plan")
    if len(result) != evaluation["paired_root_color_contrasts"] * len(endpoints):
        raise ValueError("planned pair-to-slot denominator mismatch")
    return result


def _slot_key(row: dict[str, Any]) -> SlotKey:
    slot = row.get("slot")
    if not isinstance(slot, dict):
        raise ValueError("slot must be a named object")
    candidate = slot.get("candidate_index")
    family = slot.get("family")
    color = slot.get("learner_color")
    endpoint = slot.get("endpoint")
    if type(candidate) is not int or type(family) is not int or type(color) is not int:
        raise ValueError("slot numeric key fields must be integers")
    if not isinstance(endpoint, str):
        raise ValueError("slot endpoint must be text")
    return candidate, family, color, endpoint


def audit_completed_rows(rows: list[dict[str, Any]], plan: dict[str, Any],
                         pool: dict[str, Any]) -> dict[str, Any]:
    """Audit the structural contract for a subset of durably closed slots.

    Missing slots are derived as the exact complement of the frozen universe;
    a completed UNKNOWN slot must have its own closure row with no W/L/D label.
    """
    expected = expected_slots(plan, pool)
    endpoints = tuple(plan["evaluation"]["endpoints"])
    completed: dict[SlotKey, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("slot row must be an object")
        key = _slot_key(row)
        if key not in expected:
            raise ValueError(f"unexpected evaluation slot: {key}")
        if key in completed:
            raise ValueError(f"duplicate evaluation slot: {key}")
        frozen = expected[key]
        if row.get("candidate_seed") != frozen["candidate_seed"]:
            raise ValueError("slot candidate seed differs from frozen pool")
        if row.get("node_cap") != frozen["node_cap"]:
            raise ValueError("slot cap differs from frozen paired assignment")
        nodes, queries = row.get("nodes"), row.get("queries")
        if type(nodes) is not int or type(queries) is not int or nodes < 0 or queries < 0:
            raise ValueError("slot nodes/queries must be nonnegative integers")
        if nodes > frozen["node_cap"]:
            raise ValueError("slot exceeded its combined two-side node cap")
        if queries == 0 and nodes != 0:
            raise ValueError("a slot without search queries cannot have paid nodes")

        ending = row.get("ending")
        actual = row.get("actual_outcome")
        reward = row.get("reward")
        color = key[2]
        if not isinstance(ending, str) or not ending or ending == "MISSING":
            raise ValueError("a closed row must have a non-MISSING ending reason")
        if ending == "ACTUAL_TERMINAL":
            if type(actual) is not int or actual not in (-1, 0, 1):
                raise ValueError("actual terminal requires an actual W/L/D outcome")
            expected_reward = actual if color == 0 else -actual
            if type(reward) is not int or reward != expected_reward:
                raise ValueError("reward must match actual outcome from learner perspective")
        else:
            if ending not in UNKNOWN_ENDINGS:
                raise ValueError(f"unrecognized completed UNKNOWN ending: {ending}")
            if actual is not None or reward is not None:
                raise ValueError("completed UNKNOWN cannot carry an outcome or reward label")
        completed[key] = row

    missing = set(expected) - set(completed)
    pair_rows = []
    totals = {"ACTUAL_TERMINAL": 0, "UNKNOWN": 0, "MISSING": 0}
    endpoint_totals = {endpoint: {"ACTUAL_TERMINAL": 0, "UNKNOWN": 0, "MISSING": 0}
                       for endpoint in endpoints}
    low_sum = high_sum = 0
    candidate_count = plan["training"]["arms"]
    colors = tuple(plan["evaluation"]["learner_colors"])
    families_by_candidate: dict[int, set[int]] = {}
    for candidate, family, _color, _endpoint in expected:
        families_by_candidate.setdefault(candidate, set()).add(family)
    for candidate in range(candidate_count):
        for family in sorted(families_by_candidate[candidate]):
            for color in colors:
                pair = (candidate, family, color)
                values: dict[str, tuple[str, int | None]] = {}
                for endpoint in endpoints:
                    key = (candidate, family, color, endpoint)
                    row = completed.get(key)
                    if row is None:
                        state, reward = "MISSING", None
                    elif row["ending"] == "ACTUAL_TERMINAL":
                        state, reward = "ACTUAL_TERMINAL", row["reward"]
                    else:
                        state, reward = "UNKNOWN", None
                    totals[state] += 1
                    endpoint_totals[endpoint][state] += 1
                    values[endpoint] = (state, reward)
                td = values.get("TDLeaf")
                initial = values.get("initial")
                if td is None or initial is None:
                    raise ValueError("plan must pair initial and TDLeaf endpoints")
                from results.dev_aux.task2636.verify_partial_bound_semantics import difference_bounds
                bounds = difference_bounds(td, initial)
                low_sum += bounds[0]
                high_sum += bounds[1]
                pair_rows.append({"pair": list(pair), "TDLeaf": list(td),
                                  "initial": list(initial), "difference_bounds": list(bounds)})

    planned_pairs = plan["evaluation"]["paired_root_color_contrasts"]
    if len(pair_rows) != planned_pairs:
        raise ValueError("analysis dropped a predeclared pair")
    return {
        "status": "PASS_STRUCTURAL_PARTIAL_EVALUATION_AUDIT",
        "planned_slots": len(expected), "completed_slots": len(completed),
        "missing_slots": [list(key) for key in sorted(missing)],
        "unknown_slots": [list(key) for key, row in sorted(completed.items())
                          if row["ending"] != "ACTUAL_TERMINAL"],
        "slot_states": totals, "slot_states_by_endpoint": endpoint_totals,
        "pairs": pair_rows,
        "pair_count": len(pair_rows), "difference_sum_bounds": [low_sum, high_sum],
        "difference_mean_bounds": [low_sum / planned_pairs, high_sum / planned_pairs],
        "claim_scope": "Structural row/key/cap and completion-bound audit only; not game-history, query, source, or learner replay.",
    }


def audit_files(rows_path: Path) -> dict[str, Any]:
    plan_bytes = PLAN_PATH.read_bytes()
    if hashlib.sha256(plan_bytes).hexdigest() != FROZEN_PLAN_SHA256:
        raise ValueError("task2636 study plan differs from the audited frozen plan")
    plan = json.loads(plan_bytes)
    pool_path = ROOT / plan["source_lineage"]["root_pool"]
    if hashlib.sha256(pool_path.read_bytes()).hexdigest() != plan["source_lineage"]["root_pool_sha256"]:
        raise ValueError("frozen root pool hash mismatch")
    pool = json.loads(pool_path.read_text(encoding="utf8"))
    rows = []
    with rows_path.open(encoding="utf8") as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.endswith("\n"):
                raise ValueError(f"truncated non-newline slot row at line {line_no}")
            if line.strip():
                rows.append(json.loads(line))
    return audit_completed_rows(rows, plan, pool)


def validate_result_receipt(result: dict[str, Any], rows: list[dict[str, Any]],
                             query_rows: list[dict[str, Any]],
                             audit: dict[str, Any]) -> None:
    """Bind a graceful full/partial evaluation receipt to its closed rows.

    This checks receipt consistency only. It does not validate source hashes,
    legal query replay, actual terminal authority, or monotonic-time evidence.
    """
    status = result.get("status")
    if status == "NO_FINAL_RECEIPT":
        raise ValueError("hard interruption is recovery evidence, not a final result receipt")
    if status not in {"COMPLETE", "STOPPED_USER", "TIME_CAP"}:
        raise ValueError("unrecognized final evaluation status")
    hashes = ("plan_sha256", "registration_sha256", "training_result_sha256", "root_pool_sha256")
    for field in hashes:
        value = result.get(field)
        if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
            raise ValueError(f"final receipt requires a lowercase SHA-256 {field}")

    planned = audit["planned_slots"]
    for field in ("expected_slots", "completed_slots", "missing", "actual_terminal", "UNKNOWN", "nodes", "queries"):
        if type(result.get(field)) is not int or result[field] < 0:
            raise ValueError(f"final receipt {field} must be a nonnegative integer")
    completed_keys = {_slot_key(row) for row in rows}
    missing_keys = [tuple(key) for key in audit["missing_slots"]]
    result_missing = result.get("missing_slots")
    if not isinstance(result_missing, list) or [tuple(key) for key in result_missing] != missing_keys:
        raise ValueError("final receipt missing slots differ from the exact planned complement")
    if result.get("expected_slots") != planned or result.get("completed_slots") != len(rows):
        raise ValueError("final receipt slot totals differ from closed rows")
    if result.get("missing") != len(missing_keys):
        raise ValueError("final receipt missing count differs from its missing slot list")
    if status == "COMPLETE" and (len(rows) != planned or missing_keys):
        raise ValueError("COMPLETE requires every planned slot to be closed")
    states = audit["slot_states"]
    if result.get("actual_terminal") != states["ACTUAL_TERMINAL"] or result.get("UNKNOWN") != states["UNKNOWN"]:
        raise ValueError("final receipt outcome-state counts differ from closed rows")
    if result.get("nodes") != sum(row["nodes"] for row in rows):
        raise ValueError("final receipt node total differs from closed rows")
    if result.get("queries") != sum(row["queries"] for row in rows):
        raise ValueError("final receipt query total differs from closed rows")

    per_slot: dict[SlotKey, list[dict[str, Any]]] = defaultdict(list)
    for query in query_rows:
        key = _slot_key(query)
        if key not in completed_keys:
            raise ValueError("query row lacks a durable closed slot receipt")
        if type(query.get("ply")) is not int or query["ply"] < 0:
            raise ValueError("query ply must be a nonnegative integer")
        if type(query.get("nodes")) is not int or query["nodes"] < 0:
            raise ValueError("query nodes must be a nonnegative integer")
        if type(query.get("requested_nodes")) is not int or query["requested_nodes"] <= 0 or query["nodes"] > query["requested_nodes"]:
            raise ValueError("query nodes exceed the requested amount")
        if type(query.get("complete")) is not bool:
            raise ValueError("query completion flag must be boolean")
        per_slot[key].append(query)
    if result.get("queries") != len(query_rows):
        raise ValueError("final receipt query count differs from query rows")
    for row in rows:
        key = _slot_key(row)
        queries = per_slot.get(key, [])
        plies = [query["ply"] for query in queries]
        if plies != list(range(len(plies))):
            raise ValueError("query plies are not a contiguous per-slot prefix")
        if row["queries"] != len(queries) or row["nodes"] != sum(q["nodes"] for q in queries):
            raise ValueError("slot closure counts differ from its query rows")
        incomplete = [index for index, query in enumerate(queries) if not query["complete"]]
        if incomplete and (incomplete[-1] != len(queries) - 1 or row["ending"] == "ACTUAL_TERMINAL"):
            raise ValueError("incomplete search must be the final query of an UNKNOWN slot")


def replay_slot_history(root_record: dict[str, Any], slot_row: dict[str, Any],
                        query_rows: list[dict[str, Any]], compiled_ruleset: Any,
                        expected_weights: list[float], foe_weights: list[float],
                        expected_cap: int, nodes_per_query: int) -> dict[str, Any]:
    """Replay one closed slot's complete GameSession history and receipt chain.

    This helper validates action/history and terminal consistency. The caller
    must separately bind candidate source hashes, slot identity, weights and
    registration/run receipts before trusting its return value.
    """
    from generic_chess.session.serialization import deserialize_game_record
    from generic_chess.session.session import GameSession
    from scripts.generic_session_win_proof import SessionChoice
    from results.dev_aux.task2511.generic import NonScoringTerminal
    from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv

    slot_key = _slot_key(slot_row)
    learner_color = slot_key[2]
    endpoint_weights = expected_weights
    if type(slot_row.get("node_cap")) is not int or slot_row["node_cap"] != expected_cap:
        raise ValueError("slot node cap differs from the frozen assignment")
    env = FixedScaleSessionEnv(GameSession.replay(
        compiled_ruleset, deserialize_game_record(json.dumps(root_record))))
    if env.record() != root_record or slot_row.get("initial_record") != root_record:
        raise ValueError("slot initial history differs from the frozen root")
    expected_nodes = expected_queries = 0
    incomplete_seen = False
    for index, query in enumerate(query_rows):
        if _slot_key(query) != slot_key:
            raise ValueError("query belongs to a different slot")
        ply, actor = query.get("ply"), query.get("actor")
        if (type(ply) is not int or ply != index
                or type(actor) is not int or actor != env.player()):
            raise ValueError("query ply/actor differs from full-history replay")
        if query.get("record_before") != env.record():
            raise ValueError("query pre-state differs from replayed history")
        try:
            terminal = env.terminal()
        except NonScoringTerminal:
            raise ValueError("query exists after a non-scoring terminal")
        if terminal is not None:
            raise ValueError("query exists after an actual terminal")
        actor_weights = endpoint_weights if env.player() == learner_color else foe_weights
        query_weights = query.get("weights")
        if (not isinstance(query_weights, list)
                or any(type(value) not in (int, float) or not math.isfinite(value)
                       for value in query_weights)
                or query_weights != actor_weights):
            raise ValueError("query model weights differ from endpoint/foe binding")
        nodes, requested = query.get("nodes"), query.get("requested_nodes")
        if type(nodes) is not int or type(requested) is not int or requested <= 0 or not 0 <= nodes <= requested:
            raise ValueError("query node receipt is invalid")
        if requested != min(nodes_per_query, expected_cap - expected_nodes):
            raise ValueError("query request differs from remaining slot budget")
        if expected_nodes + nodes > expected_cap:
            raise ValueError("slot exceeded its combined two-side node cap")
        complete = query.get("complete")
        if type(complete) is not bool or incomplete_seen:
            raise ValueError("query completion state is invalid or follows an incomplete query")
        if complete:
            record_after = deserialize_game_record(json.dumps(query.get("record_after")))
            previous = env.session.to_record()
            if len(record_after.actions) != len(previous.actions) + 1:
                raise ValueError("complete search must append exactly one legal action")
            env.push(SessionChoice("ACTION", action=record_after.actions[-1]))
        else:
            incomplete_seen = True
            if query.get("record_after") != query.get("record_before"):
                raise ValueError("incomplete search must not append an action")
        if env.record() != query.get("record_after"):
            raise ValueError("query post-state differs from legal full-history replay")
        env.replay()
        expected_nodes += nodes
        expected_queries += 1

    if slot_row.get("queries") != expected_queries or slot_row.get("nodes") != expected_nodes:
        raise ValueError("slot closure totals differ from its query receipts")
    if slot_row.get("final_record") != env.record():
        raise ValueError("slot final history differs from replayed queries")
    if slot_row.get("node_cap") != expected_cap or expected_nodes > expected_cap:
        raise ValueError("slot cap receipt mismatch")
    try:
        actual = env.terminal()
    except NonScoringTerminal:
        actual = None
    expected_ending = "ACTUAL_TERMINAL" if actual is not None else None
    if expected_ending is not None:
        if slot_row.get("ending") != expected_ending or slot_row.get("actual_outcome") != actual:
            raise ValueError("slot terminal receipt differs from actual rule terminal")
        reward = actual if learner_color == 0 else -actual
        if slot_row.get("reward") != reward:
            raise ValueError("slot reward differs from learner perspective")
    else:
        if slot_row.get("ending") == "ACTUAL_TERMINAL" or slot_row.get("actual_outcome") is not None or slot_row.get("reward") is not None:
            raise ValueError("nonterminal/non-scoring slot cannot carry W/L/D")
    return {"nodes": expected_nodes, "queries": expected_queries,
            "actual_outcome": actual, "reward": slot_row.get("reward"),
            "ending": slot_row.get("ending"), "final_record": env.record()}


class FrozenSlotReplayContext:
    """Verified, reusable source context for many partial-result slots.

    Construct once per audit: the root pool is about 7 MB and each rule is
    compiled once per candidate, rather than once per slot. This remains a
    preparation primitive; callers still bind training/registration receipts.
    """
    def __init__(self) -> None:
        from generic_chess.rules.compiler import compile_ruleset_for_execution
        from generic_chess.rules.schema import ruleset_from_dict

        plan_bytes = PLAN_PATH.read_bytes()
        if hashlib.sha256(plan_bytes).hexdigest() != FROZEN_PLAN_SHA256:
            raise ValueError("task2636 study plan differs from the audited frozen plan")
        self.plan = json.loads(plan_bytes)
        self.lineage = self.plan["source_lineage"]
        self.runtime_source_hashes = {}
        for relative, expected_sha in REPLAY_RUNTIME_PINS.items():
            path = (ROOT / relative).resolve()
            if not path.is_relative_to(ROOT.resolve()):
                raise ValueError("replay runtime source path escapes the checkout")
            actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual_sha != expected_sha:
                raise ValueError(f"replay runtime source hash mismatch: {relative}")
            self.runtime_source_hashes[relative] = actual_sha

        def pinned_json(relative: str, expected_sha: str) -> dict[str, Any]:
            path = (ROOT / relative).resolve()
            if not path.is_relative_to(ROOT.resolve()):
                raise ValueError("pinned source path escapes the checkout")
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != expected_sha:
                raise ValueError(f"frozen source hash mismatch: {relative}")
            return json.loads(raw)

        self.pool = pinned_json(self.lineage["root_pool"],
                                self.lineage["root_pool_sha256"])
        self.candidate_index = pinned_json(
            self.lineage["candidate_index"], self.lineage["candidate_index_sha256"])
        if self.pool.get("candidate_index_sha256") != self.lineage["candidate_index_sha256"]:
            raise ValueError("root pool is not bound to the frozen candidate index")
        self.frozen = expected_slots(self.plan, self.pool)
        self.roots = {}
        for root in self.pool["evaluation_roots"]:
            key = (root.get("candidate_index"), root.get("family"))
            if key in self.roots:
                raise ValueError("duplicate candidate/family evaluation root")
            self.roots[key] = root
        self.compiled = {}
        self.rule_hashes = {}
        self._compile_ruleset = compile_ruleset_for_execution
        self._ruleset_from_dict = ruleset_from_dict

    def replay(self, slot_row: dict[str, Any], query_rows: list[dict[str, Any]],
               expected_weights: list[float],
               foe_weights: list[float]) -> dict[str, Any]:
        """Replay one slot using this already verified and cached source context."""
        key = _slot_key(slot_row)
        candidate_number, family, _learner_color, _endpoint = key
        for label, vector in (("endpoint", expected_weights), ("foe", foe_weights)):
            if (not isinstance(vector, list) or len(vector) != 10
                    or any(type(value) not in (int, float) or not math.isfinite(value)
                           for value in vector)):
                raise ValueError(f"{label} weights must be ten finite non-boolean numbers")
        if foe_weights != [1.0] * 10:
            raise ValueError("foe weights differ from the frozen all-ones model")
        if key[3] == "initial":
            initial_source = ROOT / "results/dev_aux/task2625/freeze_study.py"
            initial_sha = hashlib.sha256(initial_source.read_bytes()).hexdigest()
            if initial_sha != self.lineage["task2625_initial_vector_source_sha256"]:
                raise ValueError("initial-vector source differs from the frozen task2625 pin")
            from results.dev_aux.task2625.freeze_study import initial_vector
            if expected_weights != initial_vector(1977, dimension=10):
                raise ValueError("initial endpoint weights differ from the frozen seed-1977 vector")
        candidates = self.candidate_index.get("rows", [])
        if not 0 <= candidate_number < len(candidates):
            raise ValueError("slot candidate index is outside the frozen index")
        candidate = candidates[candidate_number]
        if candidate.get("status") != "GENERATED_AND_COMPILED":
            raise ValueError("candidate index row is not a compiled generated rule")
        if candidate_number not in self.compiled:
            rule_path = (ROOT / candidate["source_file"]).resolve()
            if not rule_path.is_relative_to(ROOT.resolve()):
                raise ValueError("candidate rule path escapes the checkout")
            rule_bytes = rule_path.read_bytes()
            rule_sha = hashlib.sha256(rule_bytes).hexdigest()
            if rule_sha != candidate.get("ruleset_sha256"):
                raise ValueError("candidate rule source hash differs from frozen index")
            self.compiled[candidate_number] = self._compile_ruleset(
                self._ruleset_from_dict(json.loads(rule_bytes.decode("utf8"))))
            self.rule_hashes[candidate_number] = rule_sha
        root = self.roots.get((candidate_number, family))
        if root is None:
            raise ValueError("slot does not bind to a frozen evaluation root")
        if (root.get("candidate_seed") != candidate.get("seed")
                or root.get("candidate_seed") != slot_row.get("candidate_seed")):
            raise ValueError("slot/root candidate seed differs from frozen index")
        if key not in self.frozen:
            raise ValueError("slot is outside the frozen evaluation universe")
        expected_cap = self.frozen[key]["node_cap"]
        replay = replay_slot_history(
            root["record"], slot_row, query_rows, self.compiled[candidate_number],
            expected_weights, foe_weights, expected_cap,
            self.plan["training"]["search"]["nodes_per_query"])
        return {**replay, "candidate_index": candidate_number,
                "candidate_seed": root["candidate_seed"],
                "candidate_ruleset_sha256": self.rule_hashes[candidate_number],
                "root_pool_sha256": self.lineage["root_pool_sha256"],
                "candidate_index_sha256": self.lineage["candidate_index_sha256"],
                "replay_runtime_source_hashes": self.runtime_source_hashes}


def replay_frozen_slot(slot_row: dict[str, Any], query_rows: list[dict[str, Any]],
                       expected_weights: list[float],
                       foe_weights: list[float]) -> dict[str, Any]:
    """Convenience wrapper; bulk audits should reuse ``FrozenSlotReplayContext``."""
    return FrozenSlotReplayContext().replay(slot_row, query_rows,
                                            expected_weights, foe_weights)
