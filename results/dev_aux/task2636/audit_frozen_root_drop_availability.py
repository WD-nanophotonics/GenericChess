from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv
from results.dev_aux.task2636.partial_evaluation_audit import REPLAY_RUNTIME_PINS
from scripts.generic_session_win_proof import choices


PLAN = ROOT / "results/dev_aux/task2636/one-init-study-plan.json"
OUTPUT = ROOT / "results/dev_aux/task2636/frozen-root-drop-availability.json"


class NoStop:
    def poll(self) -> None:
        return None


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    plan_bytes = PLAN.read_bytes()
    plan = json.loads(plan_bytes)
    lineage = plan["source_lineage"]
    pool_path = ROOT / lineage["root_pool"]
    index_path = ROOT / lineage["candidate_index"]
    if sha256(pool_path) != lineage["root_pool_sha256"]:
        raise ValueError("frozen root pool hash mismatch")
    if sha256(index_path) != lineage["candidate_index_sha256"]:
        raise ValueError("frozen candidate index hash mismatch")
    runtime_source_hashes = {}
    for relative, expected_sha in REPLAY_RUNTIME_PINS.items():
        actual_sha = sha256(ROOT / relative)
        if actual_sha != expected_sha:
            raise ValueError(f"replay runtime source hash mismatch: {relative}")
        runtime_source_hashes[relative] = actual_sha
    if (
        runtime_source_hashes["results/dev_aux/task2621/fixed_scale.py"]
        != lineage["task2621_fixed_scale_adapter_sha256"]
    ):
        raise ValueError("fixed-scale feature adapter differs from the root-plan pin")
    pool = json.loads(pool_path.read_text(encoding="utf8"))
    index = json.loads(index_path.read_text(encoding="utf8"))

    compiled = []
    rule_hashes = []
    capabilities = []
    serialized_rule_fields: set[str] = set()
    for candidate in index["rows"]:
        rule_path = ROOT / candidate["source_file"]
        rule_hash = sha256(rule_path)
        if rule_hash != candidate["ruleset_sha256"]:
            raise ValueError("candidate rule hash mismatch")
        rules = json.loads(rule_path.read_text(encoding="utf8"))
        serialized_rule_fields.update(rules)
        compiled_rule = compile_ruleset_for_execution(ruleset_from_dict(rules))
        compiled.append(compiled_rule)
        rule_hashes.append(rule_hash)
        capabilities.append({
            "candidate_index": len(capabilities),
            "piece_type_count": len(rules["piece_types"]),
            "drop_mask_type_count": len(rules.get("drop_allowed", {})),
            "allowed_drop_squares": sum(
                sum(row) for masks in rules.get("drop_allowed", {}).values()
                for row in masks),
            "promotion_mask_type_count": len(rules.get("promotion_allowed", {})),
            "nonempty_promotion_masks": sum(
                bool(mask) for masks in rules.get("promotion_allowed", {}).values()
                for mask in masks),
            "semantic_actions": len(rules.get("semantic_actions", [])),
            "declarations": len(rules.get("declarations", [])),
            "automatic_adjudications": len(rules.get("automatic_adjudications", [])),
            "consecutive_action_adjudications": len(
                rules.get("consecutive_action_adjudications", [])),
            "initial_setup_options": len(rules.get("initial_setup_options", [])),
            "repeated_cycle_target_conditions": len(
                rules.get("repeated_cycle_target_conditions", [])),
            "no_progress_draw": rules.get("no_progress_draw"),
            "pass_enabled": rules.get("pass_enabled", False),
            "effective_repetition_policy": compiled_rule.repetition_policy,
            "effective_capture_disposition": compiled_rule.capture_disposition,
        })

    summaries = {}
    for phase in ("training_roots", "evaluation_roots"):
        per_candidate = defaultdict(lambda: {
            "roots": 0, "roots_with_hand_feature": 0,
            "roots_with_legal_drop": 0, "legal_drop_actions": 0,
            "roots_with_legal_promotion": 0, "legal_promotion_actions": 0,
        })
        for root in pool[phase]:
            candidate_index = root["candidate_index"]
            counts = per_candidate[candidate_index]
            counts["roots"] += 1
            counts["roots_with_hand_feature"] += int(any(root["features"][5:]))
            session = GameSession.replay(
                compiled[candidate_index],
                deserialize_game_record(json.dumps(root["record"])))
            features = list(FixedScaleSessionEnv(session).features())
            if features != root["features"]:
                raise ValueError("replayed root feature vector differs from frozen pool")
            legal = choices(session, NoStop())
            drop_count = sum(type(choice.action).__name__ == "DropMove"
                             for choice in legal)
            promotion_count = sum(
                getattr(choice.action, "promotion_target_id", None) is not None
                for choice in legal)
            counts["legal_drop_actions"] += drop_count
            counts["roots_with_legal_drop"] += int(drop_count > 0)
            counts["legal_promotion_actions"] += promotion_count
            counts["roots_with_legal_promotion"] += int(promotion_count > 0)
        summaries[phase] = {
            "root_count": len(pool[phase]),
            "roots_with_any_hand_feature": sum(
                item["roots_with_hand_feature"] for item in per_candidate.values()),
            "roots_with_legal_drop": sum(
                item["roots_with_legal_drop"] for item in per_candidate.values()),
            "legal_drop_actions": sum(
                item["legal_drop_actions"] for item in per_candidate.values()),
            "roots_with_legal_promotion": sum(
                item["roots_with_legal_promotion"] for item in per_candidate.values()),
            "legal_promotion_actions": sum(
                item["legal_promotion_actions"] for item in per_candidate.values()),
            "candidates_with_any_legal_drop_root": sum(
                item["roots_with_legal_drop"] > 0 for item in per_candidate.values()),
            "per_candidate": {str(key): per_candidate[key]
                              for key in sorted(per_candidate)},
        }

    result = {
        "status": "PASS_FROZEN_ROOT_LEGAL_DROP_AVAILABILITY",
        "plan_sha256": hashlib.sha256(plan_bytes).hexdigest(),
        "root_pool_sha256": lineage["root_pool_sha256"],
        "candidate_index_sha256": lineage["candidate_index_sha256"],
        "candidate_rule_sha256": rule_hashes,
        "candidate_serialized_rule_fields": sorted(serialized_rule_fields),
        "candidate_rule_capabilities": capabilities,
        "runtime_source_sha256": runtime_source_hashes,
        "outcomes_or_search_values_used": False,
        "search_or_training_started": False,
        "roots_changed": False,
        "scope": "Replayed frozen training/evaluation roots and enumerated current legal actions only; drop availability is not evidence of executed drops, TD exposure, strength, or population coverage.",
        "phases": summaries,
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
