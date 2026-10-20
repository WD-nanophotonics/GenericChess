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
RUN = BASE / "run"
PLAN = json.loads((BASE / "plan.json").read_text(encoding="utf-8"))

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


def digest(value) -> str:
    return hashlib.sha256(json.dumps(record_value(value), sort_keys=True,
        separators=(",", ":")).encode()).hexdigest().upper()


class GainScaledEvaluator(Evaluator):
    def _promotion_bonus(self, piece, idx: int) -> int:
        base = piece.base_type_id
        gain = self._profile.promotion_gain_by_type.get(base, 0)
        if piece.promoted or gain <= 0:
            return 0
        zone = self._zones.get((base, piece.owner))
        if zone is None:
            return 0
        zone_bonus = (self._config.promotion_potential_weight * gain + 500) // 1000
        if idx in zone:
            bonus = zone_bonus
        else:
            forward = self._promotion_forward[(base, piece.owner)][idx]
            bonus = zone_bonus // 2 if any(square in zone for square in forward) else 0
        return bonus if piece.owner == 0 else -bonus


def main() -> None:
    result = json.loads((RUN / "result.json").read_text(encoding="utf-8"))
    assert result["status"] == "COMPLETE"
    assert result["source_head"] == PLAN["source_head"]
    assert result["plan_sha256"] == hashlib.sha256((BASE / "plan.json").read_bytes()).hexdigest().upper()
    roots = {r["root_id"]: r for r in json.loads((RUN / "roots.json").read_text(encoding="utf-8"))}
    rows = [json.loads(line) for line in (RUN / "games.jsonl").read_text(encoding="utf-8").splitlines() if line]
    compiled_by_seed, evaluators_by_seed = {}, {}
    for i, seed in enumerate(PLAN["rules"]["seeds"]):
        generated = generate_game(GeneratorConfig(
            seed=seed, board_size=PLAN["rules"]["board_size"],
            setup_preset=PLAN["rules"]["setup_schedule"][i % len(PLAN["rules"]["setup_schedule"])],
            movement_symmetry=PLAN["rules"]["symmetry_schedule"][i % len(PLAN["rules"]["symmetry_schedule"])],
            allow_hybrid=PLAN["rules"]["allow_hybrid"],
            require_promotable_type=PLAN["rules"]["require_promotable_type"],
            require_nonpromotable_type=PLAN["rules"]["require_nonpromotable_type"],
            max_generation_attempts=PLAN["rules"]["max_generation_attempts"],
            require_no_opening_win_in_one=PLAN["rules"]["require_no_opening_win_in_one"],
        ))
        saved = json.loads((RUN / f"rule-{seed}.json").read_text(encoding="utf-8"))
        assert ruleset_to_dict(generated.ruleset) == saved
        compiled = compile_legacy_ruleset_for_semantic_execution(generated.ruleset)
        cfg = EvaluationConfig(promotion_potential_weight=3)
        profile = build_ruleset_profile(compiled, EvaluationConfig())
        profile = replace(profile, hand_value_by_base_type={
            pt.type_id: (0 if pt.is_anchor else 900) for pt in compiled.piece_types
        })
        evaluators_by_seed[seed] = (
            Evaluator(compiled, profile, cfg),
            GainScaledEvaluator(compiled, profile, cfg),
        )
        compiled_by_seed[seed] = compiled

    decision_values = {}
    check_count = 0
    for row in rows:
        seed = int(row["root_id"].split("-")[0])
        compiled = compiled_by_seed[seed]
        session = GameSession(compiled)
        opening = roots[row["root_id"]]["opening"]
        record = deserialize_game_record(json.dumps(row["full_record"], sort_keys=True))
        assert [record_value(a) for a in record.actions[:len(opening)]] == opening
        for action in record.actions[:len(opening)]:
            session.submit(action)
        current_eval, scaled_eval = evaluators_by_seed[seed]
        for offset, move in enumerate(row["moves"]):
            state_hash = digest({"state": session.state, "history": session.history,
                                 "witnesses": session._search_witnesses, "result": session.result})
            assert state_hash == move["state_before"]
            if move["role"] == "candidate":
                values = (current_eval.evaluate(session.state), scaled_eval.evaluate(session.state))
                old = decision_values.setdefault(state_hash, values)
                assert old == values
                check_count += 1
            action = record.actions[len(opening) + offset]
            assert record_value(action) == move["action"]
            if move["action"] is not None:
                session.submit(action)
        assert session.state == GameSession.replay(compiled, record).state

    arm_by_pair = defaultdict(dict)
    for row in rows:
        arm_by_pair[(row["root_id"], row["candidate_owner"])][row["variant"]] = row
    shared = set()
    per_pair_shared = 0
    for arms in arm_by_pair.values():
        current = {m["state_before"] for m in arms["candidate_current"]["moves"] if m["role"] == "candidate"}
        scaled = {m["state_before"] for m in arms["candidate_gain_scaled"]["moves"] if m["role"] == "candidate"}
        common = current & scaled
        per_pair_shared += len(common)
        shared.update(common)
    delta_by_state = {state: values[1] - values[0] for state, values in decision_values.items()}
    hist = Counter(delta_by_state.values())
    payload = {
        "status": "INDEPENDENT_PLAYED_PATH_EXPOSURE_AUDIT_PASS",
        "source_head": PLAN["source_head"],
        "plan_sha256": hashlib.sha256((BASE / "plan.json").read_bytes()).hexdigest().upper(),
        "games_sha256": hashlib.sha256((RUN / "games.jsonl").read_bytes()).hexdigest().upper(),
        "method": "Regenerate sealed rules; replay each saved full record from its exact opening; at each candidate decision evaluate the exact same GameState under current and gain-scaled evaluator; count only identical full-history hashes across paired arms.",
        "played_candidate_decision_visits": check_count,
        "unique_candidate_full_history_states": len(decision_values),
        "states_shared_across_paired_arms": len(shared),
        "paired_candidate_state_matches_counted_per_root_owner": per_pair_shared,
        "current_vs_scaled_score_delta_histogram_by_unique_candidate_state": dict(sorted(hist.items())),
        "unique_candidate_states_with_nonzero_score_delta": sum(v != 0 for v in delta_by_state.values()),
        "scope_limit": "Observed candidate played states only, not search leaves or a population exposure estimate; score changes are treatment-exposure evidence, not utility.",
    }
    out = RUN / "played-path-exposure.json"
    out.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("status", "played_candidate_decision_visits",
        "unique_candidate_full_history_states", "states_shared_across_paired_arms",
        "paired_candidate_state_matches_counted_per_root_owner",
        "current_vs_scaled_score_delta_histogram_by_unique_candidate_state",
        "unique_candidate_states_with_nonzero_score_delta")}, sort_keys=True))


if __name__ == "__main__":
    main()
