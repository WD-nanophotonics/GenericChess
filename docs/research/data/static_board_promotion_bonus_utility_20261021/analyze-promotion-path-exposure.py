from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
BASE = Path(__file__).resolve().parent
RUN = BASE / "promotion-bonus-run"
PLAN = json.loads((BASE / "promotion-bonus-plan.json").read_text(encoding="utf-8"))

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.serialization import ruleset_to_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from scripts.research_record import record_value


games = [json.loads(line) for line in (RUN / "games.jsonl").read_text(encoding="utf-8").splitlines() if line]
roots = {root["root_id"]: root for root in json.loads((RUN / "roots.json").read_text(encoding="utf-8"))}
setup = PLAN["rules"]["setup_schedule"]
symmetry = PLAN["rules"]["symmetry_schedule"]
compiled_by_seed = {}
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
    assert ruleset_to_dict(generated.ruleset) == json.loads((RUN / f"rule-{seed}.json").read_text(encoding="utf-8"))
    compiled_by_seed[seed] = compile_legacy_ruleset_for_semantic_execution(generated.ruleset)

group = defaultdict(Counter)
delta_hist = Counter()
state_rows = 0
decision_rows = 0
per_game = []
candidate_decision_maps = {}
for row in games:
    seed = int(row["root_id"].split("-")[0])
    compiled = compiled_by_seed[seed]
    record = deserialize_game_record(json.dumps(row["full_record"], sort_keys=True))
    assert record.ruleset_fingerprint == compiled.ruleset_fingerprint
    session = GameSession(compiled, initial_setup_key=record.initial_setup_key)
    root = roots[row["root_id"]]
    opening_actions = tuple(record.actions[:len(root["opening"])])
    assert [record_value(action) for action in opening_actions] == root["opening"]
    for action in opening_actions:
        session.submit(action)
    root_digest = hashlib.sha256(json.dumps(
        record_value({"state": session.state, "history": session.history,
                      "witnesses": session._search_witnesses, "result": session.result}),
        sort_keys=True, separators=(",", ":")).encode()).hexdigest().upper()
    assert root_digest == row["root_state_sha256"], (row["game_id"], "ROOT_REPLAY_MISMATCH")
    profile = build_ruleset_profile(compiled, EvaluationConfig())
    unit_hand = {pt.type_id: (0 if pt.is_anchor else 900) for pt in compiled.piece_types}
    profile = replace(profile, hand_value_by_base_type=unit_hand)
    saved_profile = json.loads((RUN / f"profile-{seed}.json").read_text(encoding="utf-8"))
    assert saved_profile["candidate_board_values"] == dict(profile.board_value_by_type)
    assert saved_profile["unit_hand_values"] == unit_hand
    assert saved_profile["promotion_gain_by_type"] == dict(profile.promotion_gain_by_type)
    off = Evaluator(compiled, profile, EvaluationConfig(promotion_potential_weight=0))
    on = Evaluator(compiled, profile, EvaluationConfig(promotion_potential_weight=3))
    owner = row["candidate_owner"]
    candidates = Counter()
    candidates_nonzero = Counter()
    candidates_delta = Counter()
    candidate_map = {}
    for ply, move in enumerate(row["moves"]):
        assert session.state.position.side_to_move == move["side"]
        delta = on.evaluate(session.state) - off.evaluate(session.state)
        state_rows += 1
        delta_hist[str(delta)] += 1
        side = "candidate" if move["side"] == owner else "foe"
        arm = row["variant"]
        key = f"{arm}/{side}"
        group[key]["states"] += 1
        group[key]["nonzero_states"] += int(delta != 0)
        group[key]["absolute_delta_sum"] += abs(delta)
        if side == "candidate":
            decision_rows += 1
            candidates["states"] += 1
            candidates_nonzero["states"] += int(delta != 0)
            candidates_delta[str(delta)] += 1
            group[key]["candidate_decisions"] += 1
            group[key]["candidate_nonzero"] += int(delta != 0)
            group[key]["candidate_abs_delta_sum"] += abs(delta)
            if move["state_before"] in candidate_map:
                raise AssertionError((row["game_id"], move["state_before"], "DUPLICATE_CANDIDATE_STATE"))
            candidate_map[move["state_before"]] = json.dumps(
                move["action"], sort_keys=True, separators=(",", ":"))
        # Match the recorded trajectory through the public Core submit path.
        session.submit(record.actions[len(opening_actions) + ply])
    assert len(record.actions) == len(opening_actions) + len(row["moves"])
    final_digest = hashlib.sha256(json.dumps(
        record_value({"state": session.state, "history": session.history,
                      "witnesses": session._search_witnesses, "result": session.result}),
        sort_keys=True, separators=(",", ":")).encode()).hexdigest().upper()
    assert final_digest == row["final_state_sha256"], (row["game_id"], "FINAL_REPLAY_MISMATCH")
    per_game.append({
        "game_id": row["game_id"], "root_id": row["root_id"],
        "candidate_owner": owner, "variant": row["variant"],
        "candidate_decisions": candidates["states"],
        "candidate_nonzero_decisions": candidates_nonzero["states"],
        "candidate_delta_histogram": dict(candidates_delta),
        "terminal_reason": row["terminal_reason"],
    })
    candidate_decision_maps[row["game_id"]] = candidate_map

summaries = {}
for key, counts in sorted(group.items()):
    states = counts["states"]
    candidate = counts["candidate_decisions"]
    summaries[key] = {
        "played_states": states,
        "played_states_with_nonzero_bonus": counts["nonzero_states"],
        "played_state_nonzero_rate": counts["nonzero_states"] / states if states else None,
        "played_state_absolute_bonus_sum": counts["absolute_delta_sum"],
        "candidate_decisions": candidate,
        "candidate_decisions_with_nonzero_bonus": counts["candidate_nonzero"],
        "candidate_decision_nonzero_rate": counts["candidate_nonzero"] / candidate if candidate else None,
        "candidate_decision_absolute_bonus_sum": counts["candidate_abs_delta_sum"],
    }

paired_candidates = defaultdict(dict)
for row in games:
    paired_candidates[(row["root_id"], row["candidate_owner"])][row["variant"]] = candidate_decision_maps[row["game_id"]]
matched_states = 0
changed_actions = 0
pair_summaries = []
for (root_id, owner), variants in sorted(paired_candidates.items()):
    off_map = variants["promotion_gain_off"]
    on_map = variants["rule_derived_promotion_gain_on"]
    common = sorted(set(off_map) & set(on_map))
    differences = [state for state in common if off_map[state] != on_map[state]]
    matched_states += len(common)
    changed_actions += len(differences)
    pair_summaries.append({
        "root_id": root_id, "candidate_owner": owner,
        "off_candidate_decisions": len(off_map), "on_candidate_decisions": len(on_map),
        "same_full_history_candidate_states": len(common),
        "actions_differing_at_same_state": len(differences),
        "example_differing_state_sha256": differences[0] if differences else None,
    })

output = {
    "status": "COMPLETE",
    "question": "How often did the static-v2 promotion-potential term actually change the production Evaluator score on the already-recorded played trajectories?",
    "method": "Regenerate the eight sealed rules; replay every recorded move through GameSession.submit; at each pre-move state compare the production Evaluator with promotion_potential_weight 0 and 3, holding the exact same default profile and all other EvaluationConfig fields fixed.",
    "scope_limit": "Observed played states only. This is not search-leaf exposure, a causal outcome estimate, WDL, or a new game/search run.",
    "source_head": PLAN["source_head"],
    "games_sha256": hashlib.sha256((RUN / "games.jsonl").read_bytes()).hexdigest().upper(),
    "regenerated_rules": len(compiled_by_seed),
    "full_games": len(games),
    "played_state_count": state_rows,
    "delta_histogram_all_plies": dict(sorted(delta_hist.items(), key=lambda item: int(item[0]))),
    "strata": summaries,
    "paired_candidate_decisions": {
        "root_owner_pairs": len(pair_summaries),
        "same_full_history_candidate_states": matched_states,
        "different_actions_at_same_state": changed_actions,
        "pairs": pair_summaries,
    },
    "per_game": per_game,
}
out = BASE / "promotion-bonus-run" / "played-path-exposure.json"
out.write_text(json.dumps(output, sort_keys=True, indent=2) + "\n", encoding="utf-8")
print(json.dumps({
    "status": output["status"], "regenerated_rules": output["regenerated_rules"],
    "full_games": output["full_games"], "played_state_count": state_rows,
    "strata": summaries, "delta_histogram_all_plies": output["delta_histogram_all_plies"],
    "paired_candidate_decisions": output["paired_candidate_decisions"],
    "games_sha256": output["games_sha256"],
}, sort_keys=True))
