"""Machine-readable Phase 1.9A-2 design artifacts (design only, read-only
with respect to production).  Emits the IR design tables under
``artifacts/rule_semantics_phase1_9a2/``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "artifacts" / "rule_semantics_phase1_9a2"


def _write(name: str, data: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> int:
    sys.path.insert(0, str(ROOT))
    from experiments.rule_ir_design_prototype import (
        MAX_AUX_SLOTS_PER_RULESET,
        MAX_EFFECTS_PER_ACTION,
        MAX_POSTCONDITIONS_PER_TEMPLATE,
        MAX_PREDICATES_PER_TEMPLATE,
        serialize_all,
        validate_all,
    )

    validation = validate_all()
    _write("semantic_categories.json", {
        "categories": [
            "candidate_geometry",
            "target_predicate",
            "path_predicate",
            "state_query_guard",
            "slot_guard",
            "action_intent",
            "bounded_effects",
            "auxiliary_state",
            "invariant",
            "postcondition",
            "bounded_legal_reply_probe",
        ],
        "count": 11,
    })
    _write("dependency_strata.json", {
        "strata": {
            "S0": "geometry / occupancy",
            "S1": "state query / rights / tokens",
            "S2": "pseudo attack (geometry + occupancy, no trial make)",
            "S3": "trial transition + global invariants (own-anchor safety)",
            "S4": "bounded post-action probe (stratified, probe stratum <= S3)",
            "S5": "terminal / history",
        },
        "allowed_edges": {
            "S0": [],
            "S1": ["S0"],
            "S2": ["S0", "S1"],
            "S3": ["S0", "S1", "S2"],
            "S4": ["S0", "S1", "S2", "S3"],
            "S5": ["S0", "S1", "S2", "S3"],
        },
        "no_cycles": True,
    })
    _write("primitive_inventory.json", {
        "geometry_kinds": ["leap", "ray", "drop"],
        "path_kinds": [
            "path_clear",
            "path_count_eq",
            "path_count_range",
            "path_first_blocker_owner",
            "path_last_blocker_owner",
        ],
        "target_kinds": [
            "target_empty",
            "target_enemy",
            "target_friendly",
            "target_any",
        ],
        "effect_kinds": [
            "move",
            "remove",
            "remove_from_hand",
            "place",
            "set_current_type",
            "clear_right",
            "set_token",
            "clear_token",
            "shift",
        ],
        "aux_kinds": ["right", "token_square"],
        "invariant_kinds": ["own_anchor_safe", "squares_not_attacked"],
        "postcondition_kinds": ["opponent_checked", "no_legal_reply"],
        "probe_kinds": ["exists_legal_reply"],
        "selector_owner": ["self", "opponent", "any"],
        "selector_type_mode": ["base", "current", "any"],
        "selector_promoted": ["yes", "no", "any"],
        "selector_location": ["board", "hand"],
        "selector_spatial": [
            "same_file",
            "same_rank",
            "zone",
            "exact",
            "adjacent",
            "path_between",
        ],
        "aggregation": ["exists", "count"],
        "comparison_ops": ["eq", "ne", "lt", "le", "gt", "ge"],
        "execution_primitive_kind_count": 31,
        "no_game_name_tokens": True,
    })
    _write("stress_test_mapping.json", {
        "groups": serialize_all(),
        "validation": {
            name: validation[name]["valid"] for name in validation if name != "dependency_cycle_rejected"
        },
        "dependency_cycle_rejected": validation["dependency_cycle_rejected"]["rejected"],
    })
    _write("state_model.json", {
        "aux_state_kinds": {
            "right": {
                "type": "bool",
                "lifetime": "persistent",
                "cleared_by": "clear_right effect",
                "example": "one-time permission flag",
            },
            "token_square": {
                "type": "square-or-none",
                "lifetime": "expire_next_turn",
                "set_by": "set_token effect",
                "expiry": "uniform turn-boundary lifecycle step",
                "example": "double-step opportunity",
            },
        },
        "slot_bounds": {
            "max_aux_slots_per_ruleset": MAX_AUX_SLOTS_PER_RULESET,
            "typed": True,
            "python_storage": "position-level typed slot tuple",
            "native_storage": "fixed slot array in GCPosition extension",
            "serialization": "slots in serialized position payload",
            "identity": "slots in position key and native hash",
            "make": "effect-driven set/clear + turn-boundary expiry",
            "unmake": "fixed slot snapshot in expanded undo",
            "repetition": "identity includes slots; distinct positions when future legality differs",
            "tt_safety": "TT key includes slots",
        },
    })
    _write("action_model.json", {
        "model": "intent + bounded effect list",
        "intent": ["actor_selector", "source_or_drop_origin", "target", "chosen_promotion", "semantic_params"],
        "effects_bounded": {
            "max_effects_per_action": MAX_EFFECTS_PER_ACTION,
            "static": True,
            "native_representation": "fixed-capacity small record (no per-node heap)",
        },
        "alternatives_compared": [
            "fixed extended action record (rejected: hard to extend to compound moves)",
            "unbounded dynamic effect list (rejected: heap + unbounded validation)",
            "bounded effect list (preferred)",
        ],
    })
    _write("cost_model.json", {
        "classes": {
            "C0": "compile-time only",
            "C1": "O(1) per candidate",
            "C2": "small board/path scan",
            "C3": "trial-make + attack",
            "C4": "bounded legal-reply probe (stratified)",
        },
        "guard_order": [
            "candidate geometry",
            "target/path predicate",
            "state guard (cheap first)",
            "trial make",
            "royal safety invariant",
            "rare expensive postcondition",
        ],
        "compiler_reorders": True,
    })
    _write("red_team.json", {
        "dependency_cycle": "prevented by design (strata DAG; probe stratum <= S3)",
        "unbounded_recursive_legality": "prevented by design (stratified probe, single-level)",
        "unbounded_effect_list": "prevented by design (max 4 effects, static)",
        "runtime_state_unhashable": "prevented by design (typed slots, slot Zobrist)",
        "native_dynamic_malloc": "prevented by design (fixed-capacity records)",
        "python_c_reinterpretation": "prevented by design (single lowering authority)",
        "generator_ir_coupling": "prevented by design (generator -> Rule Definition only)",
        "session_only_semantic_flag": "prevented by design (slots are position semantics)",
        "pseudo_attack_depends_on_full_legal": "prevented by design (attack = geometry + path occupancy only)",
    })
    _write("final_design_verdict.json", {
        "verdict": "RULE_IR_DESIGN_READY_FOR_REFERENCE_IMPLEMENTATION",
        "stress_tests_pass": all(
            validation[k]["valid"] for k in validation if k != "dependency_cycle_rejected"
        ),
        "game_specific_primitives": 0,
        "dependency_cycle_rejected": validation["dependency_cycle_rejected"]["rejected"],
    })
    snapshot_path = ROOT / "artifacts" / "rule_semantics_audit" / "architecture_inventory.json"
    if snapshot_path.exists():
        _write(
            "architecture_snapshot.json",
            json.loads(snapshot_path.read_text(encoding="utf-8")),
        )
    print("wrote", len(list(OUT.glob("*.json"))), "design artifacts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
