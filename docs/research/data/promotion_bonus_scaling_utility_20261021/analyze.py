from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from statistics import median
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
BASE = Path(__file__).resolve().parent
RUN = BASE / "run"
PLAN = json.loads((BASE / "plan.json").read_text(encoding="utf-8"))

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.core.actions import action_to_dict
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.serialization import ruleset_to_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from scripts.research_record import record_value


def digest(value) -> str:
    payload = json.dumps(record_value(value), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest().upper()


def conservative_bounds(pairs):
    lo = hi = 0
    for current, scaled in pairs:
        a, b = current.get("reward"), scaled.get("reward")
        lo += (-1 if b is None else b) - (1 if a is None else a)
        hi += (1 if b is None else b) - (-1 if a is None else a)
    n = len(pairs)
    return {"lower_mean_scaled_minus_current": lo / n if n else None,
            "upper_mean_scaled_minus_current": hi / n if n else None,
            "pairs": n, "pairs_with_any_unknown": sum(
                a.get("reward") is None or b.get("reward") is None for a, b in pairs)}


def main():
    result = json.loads((RUN / "result.json").read_text(encoding="utf-8"))
    if result.get("status") != "COMPLETE":
        raise RuntimeError("RUN_NOT_COMPLETE")
    assert result["source_head"] == PLAN["source_head"]
    assert result["plan_sha256"] == hashlib.sha256((BASE / "plan.json").read_bytes()).hexdigest().upper()
    games = [json.loads(line) for line in (RUN / "games.jsonl").read_text(encoding="utf-8").splitlines() if line]
    roots = {row["root_id"]: row for row in json.loads((RUN / "roots.json").read_text(encoding="utf-8"))}
    assert len(games) == PLAN["controls"]["maximum_slots"] == 64
    assert len(roots) == 16
    setup, symmetry = PLAN["rules"]["setup_schedule"], PLAN["rules"]["symmetry_schedule"]
    compiled_by_seed = {}
    profiles_by_seed = {}
    for index, seed in enumerate(PLAN["rules"]["seeds"]):
        generated = generate_game(GeneratorConfig(
            seed=seed, board_size=PLAN["rules"]["board_size"],
            setup_preset=setup[index % len(setup)],
            movement_symmetry=symmetry[index % len(symmetry)],
            allow_hybrid=PLAN["rules"]["allow_hybrid"],
            require_promotable_type=PLAN["rules"]["require_promotable_type"],
            require_nonpromotable_type=PLAN["rules"]["require_nonpromotable_type"],
            max_generation_attempts=PLAN["rules"]["max_generation_attempts"],
            require_no_opening_win_in_one=PLAN["rules"]["require_no_opening_win_in_one"],
        ))
        rules = ruleset_to_dict(generated.ruleset)
        saved_rules = json.loads((RUN / f"rule-{seed}.json").read_text(encoding="utf-8"))
        assert rules == saved_rules, (seed, "RULE_REGENERATION_MISMATCH")
        compiled = compile_legacy_ruleset_for_semantic_execution(generated.ruleset)
        profile = build_ruleset_profile(compiled, EvaluationConfig())
        unit_hand = {pt.type_id: (0 if pt.is_anchor else 900) for pt in compiled.piece_types}
        saved_profile = json.loads((RUN / f"profile-{seed}.json").read_text(encoding="utf-8"))
        assert saved_profile["board_values"] == dict(profile.board_value_by_type)
        assert saved_profile["unit_hand_values"] == unit_hand
        assert saved_profile["promotion_gain_by_type"] == dict(profile.promotion_gain_by_type)
        compiled_by_seed[seed] = compiled
        profiles_by_seed[seed] = saved_profile

    for row in games:
        seed = int(row["root_id"].split("-")[0])
        compiled = compiled_by_seed[seed]
        record = deserialize_game_record(json.dumps(row["full_record"], sort_keys=True))
        assert record.ruleset_fingerprint == compiled.ruleset_fingerprint
        root = roots[row["root_id"]]
        opening_actions = tuple(record.actions[:len(root["opening"])])
        assert [record_value(a) for a in opening_actions] == root["opening"]
        prefix = GameSession(compiled)
        for action in opening_actions:
            prefix.submit(action)
        assert digest({"state": prefix.state, "history": prefix.history,
                       "witnesses": prefix._search_witnesses, "result": prefix.result}) == row["root_state_sha256"]
        assert row["root_state_sha256"] == root["root_state_sha256"]
        replay = GameSession.replay(compiled, record)
        assert digest({"state": replay.state, "history": replay.history,
                       "witnesses": replay._search_witnesses, "result": replay.result}) == row["final_state_sha256"]
        assert replay.result.status.value == row["terminal_status"]
        assert replay.result.winner == row["winner"]
        assert tuple(item.action for item in replay.history) == record.actions
        assert row["action_invalid_count"] == 0 and row["full_history_replay_equal"]
        if row["reward"] is None:
            assert "UNKNOWN" in row["terminal_reason"] or row["terminal_status"] == "no_contest"
        else:
            assert row["terminal_reason"] == "ACTUAL_TERMINAL"
            expected = 0 if replay.result.winner is None else (
                1 if replay.result.winner == row["candidate_owner"] else -1)
            assert row["reward"] == expected

    by_pair = defaultdict(dict)
    for row in games:
        by_pair[(row["root_id"], row["candidate_owner"])][row["variant"]] = row
    assert len(by_pair) == 32 and all(set(v) == {"candidate_current", "candidate_gain_scaled"} for v in by_pair.values())
    comparisons = []
    strata = defaultdict(list)
    candidate_state_matches = 0
    changed_actions = 0
    first_action_changes = 0
    for (root_id, owner), arms in sorted(by_pair.items()):
        current, scaled = arms["candidate_current"], arms["candidate_gain_scaled"]
        pair = (current, scaled)
        comparisons.append({"root_id": root_id, "candidate_owner": owner,
            "current_reward": current["reward"], "scaled_reward": scaled["reward"],
            "current_terminal_reason": current["terminal_reason"],
            "scaled_terminal_reason": scaled["terminal_reason"],
            "reward_delta": None if current["reward"] is None or scaled["reward"] is None
                else scaled["reward"] - current["reward"],
            "current_candidate_nodes": current["candidate_nodes"],
            "scaled_candidate_nodes": scaled["candidate_nodes"],
            "current_caller_seconds": current["caller_seconds"],
            "scaled_caller_seconds": scaled["caller_seconds"]})
        for label, condition in (("all", True), ("owner0", owner == 0), ("owner1", owner == 1),
                                 ("odd", int(root_id.split("-")[-1]) % 2 == 1),
                                 ("even", int(root_id.split("-")[-1]) % 2 == 0)):
            if condition:
                strata[label].append(pair)
        current_candidates = {m["state_before"]: json.dumps(m["action"], sort_keys=True, separators=(",", ":"))
            for m in current["moves"] if m["role"] == "candidate"}
        scaled_candidates = {m["state_before"]: json.dumps(m["action"], sort_keys=True, separators=(",", ":"))
            for m in scaled["moves"] if m["role"] == "candidate"}
        common = set(current_candidates) & set(scaled_candidates)
        candidate_state_matches += len(common)
        changed_actions += sum(current_candidates[state] != scaled_candidates[state] for state in common)
        current_first = next((m["action"] for m in current["moves"] if m["role"] == "candidate"), None)
        scaled_first = next((m["action"] for m in scaled["moves"] if m["role"] == "candidate"), None)
        first_action_changes += int(current_first != scaled_first)
    outcomes = {}
    for label, subset in (("current", [g for g in games if g["variant"] == "candidate_current"]),
                          ("gain_scaled", [g for g in games if g["variant"] == "candidate_gain_scaled"])):
        outcomes[label] = {"wins": sum(g["reward"] == 1 for g in subset),
                           "losses": sum(g["reward"] == -1 for g in subset),
                           "draws": sum(g["reward"] == 0 for g in subset)}
        outcomes[label]["unknown"] = sum(g["reward"] is None for g in subset)
    node_changes = [(p["candidate_current"]["candidate_nodes"] - p["candidate_gain_scaled"]["candidate_nodes"])
                    / p["candidate_current"]["candidate_nodes"]
                    for p in by_pair.values() if p["candidate_current"]["candidate_nodes"] > 0]
    analysis = {
        "status": "INDEPENDENT_AUDIT_PASS",
        "question": PLAN["question"],
        "scope_limit": PLAN["scope_limit"],
        "source_head": PLAN["source_head"],
        "plan_sha256": hashlib.sha256((BASE / "plan.json").read_bytes()).hexdigest().upper(),
        "games_sha256": hashlib.sha256((RUN / "games.jsonl").read_bytes()).hexdigest().upper(),
        "regenerated_rules": len(compiled_by_seed), "verified_profiles": len(profiles_by_seed),
        "full_histories_replayed": len(games), "paired_root_owner_contrasts": len(comparisons),
        "invalid_actions": sum(g["action_invalid_count"] for g in games),
        "producer_replay_mismatches": sum(not g["full_history_replay_equal"] for g in games),
        "outcomes": outcomes,
        "scaled_minus_current_conservative_reward_bounds": {
            label: conservative_bounds(values) for label, values in sorted(strata.items())},
        "paired_decision_sensitivity": {
            "candidate_root_owner_first_action_changes": first_action_changes,
            "same_full_history_candidate_states": candidate_state_matches,
            "candidate_actions_different_at_same_full_history": changed_actions,
        },
        "cost": {
            "median_candidate_node_reduction_fraction": median(node_changes) if node_changes else None,
            "aggregate_candidate_nodes_current": sum(g["candidate_nodes"] for g in games if g["variant"] == "candidate_current"),
            "aggregate_candidate_nodes_scaled": sum(g["candidate_nodes"] for g in games if g["variant"] == "candidate_gain_scaled"),
            "aggregate_candidate_seconds_current": sum(m["elapsed_seconds"] for g in games
                if g["variant"] == "candidate_current" for m in g["moves"] if m["role"] == "candidate"),
            "aggregate_candidate_seconds_scaled": sum(m["elapsed_seconds"] for g in games
                if g["variant"] == "candidate_gain_scaled" for m in g["moves"] if m["role"] == "candidate"),
            "aggregate_caller_seconds_current": sum(g["caller_seconds"] for g in games if g["variant"] == "candidate_current"),
            "aggregate_caller_seconds_scaled": sum(g["caller_seconds"] for g in games if g["variant"] == "candidate_gain_scaled"),
        },
        "per_pair": comparisons,
    }
    (RUN / "analysis.json").write_text(json.dumps(analysis, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    result.update({"independent_audit": analysis["status"], "games_sha256": analysis["games_sha256"],
                   "analyzed_at_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()})
    (RUN / "execution-closure.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: analysis[key] for key in (
        "status", "regenerated_rules", "full_histories_replayed", "outcomes",
        "scaled_minus_current_conservative_reward_bounds", "paired_decision_sensitivity", "cost")}, sort_keys=True))


if __name__ == "__main__":
    main()
