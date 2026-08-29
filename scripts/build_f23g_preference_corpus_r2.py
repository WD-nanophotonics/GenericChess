"""Build the evaluator-free F23G deep generic preference corpus."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

from scripts import build_f23b_evaluator_corpus as f23b
from scripts import build_f23c_evaluator_corpus_r2 as f23c
from scripts.exact_generic_preference_solver import solve_root
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.rules.schema import (
    RuleActionEffect,
    RuleAuxState,
    RuleGeometrySpec,
    RuleInvariant,
    RuleReplaceSelector,
    RuleSemanticAction,
    RuleSlotGuard,
    RuleSquareRef,
)
from rule_semantics_ir_fixtures import _semantic_ruleset

V3 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v3.json"
SOLVER_VERSION = "f23g-exact-generic-preference-solver-v2"


def _rows(n: int, pieces: dict[tuple[int, int], str]) -> list[str]:
    board = [["."] * n for _ in range(n)]
    for square, piece in pieces.items():
        file, rank = square
        if board[rank][file] != ".":
            raise ValueError(f"overlap at {square}")
        board[rank][file] = piece
    return ["".join(board[rank]) for rank in range(n - 1, -1, -1)]


def _semantic_variant(m: dict[str, Any], variant: int):
    """A compact two-reply game with an evaluator-blind exact preference."""
    n = 5
    extra_a = (
        (1, 0),
        (0, 1),
        (0, -1),
        (1, 1),
        (-1, -1),
    )[variant]
    A = m["T"]("A", RayAtom((-1, 0)), RayAtom(extra_a))
    B = m["T"]("B")
    C = m["T"]("C", RayAtom((0, -1)))
    H = m["T"]("H", LeapAtom((-2, -2)))
    D = m["T"]("D")
    ref = lambda kind, **kw: RuleSquareRef(kind=kind, **kw)
    armed = RuleAuxState("armed", "bool", "global", "persistent", 0)
    staged = RuleAuxState("staged", "bool", "global", "persistent", 0)
    replied = RuleAuxState("replied", "bool", "global", "persistent", 0)
    started = RuleAuxState("started", "bool", "global", "persistent", 0)
    bad = RuleAuxState("bad", "bool", "global", "persistent", 0)
    own_safe = (RuleInvariant("own_anchor_safe"),)
    prepare = RuleSemanticAction(
        name="prepare", type_ids=("A",),
        geometry=RuleGeometrySpec(kind="leap", offset=(0, 1)),
        target_relation="empty", aux_state=(armed, started),
        effects=(RuleActionEffect("move", from_ref=ref("source"), to_ref=ref("target")),
                 RuleActionEffect("set_bool", slot_name="armed", value=1),
                 RuleActionEffect("set_bool", slot_name="started", value=1)),
        invariants=own_safe,
    )
    bad_move = RuleSemanticAction(
        name="bad_move", type_ids=("A",),
        geometry=RuleGeometrySpec(kind="leap", offset=(0, -1)),
        target_relation="empty", slot_guards=(RuleSlotGuard("bad", value=0),),
        aux_state=(bad,),
        effects=(RuleActionEffect("move", from_ref=ref("source"), to_ref=ref("target")),
                 RuleActionEffect("set_bool", slot_name="bad", value=1)),
        invariants=own_safe,
    )
    stage = RuleSemanticAction(
        name="stage", type_ids=("A",),
        geometry=RuleGeometrySpec(kind="leap", offset=(0, -1)),
        target_relation="empty", composition="replace_legacy",
        replace_selector=RuleReplaceSelector(
            type_ids=("A",), action_family="board", target_relation="empty",
            geometry_kind="ray", replace_all_matching=True,
        ),
        slot_guards=(RuleSlotGuard("armed", value=1), RuleSlotGuard("staged", value=0)), aux_state=(staged,),
        effects=(RuleActionEffect("move", from_ref=ref("source"), to_ref=ref("target")),
                 RuleActionEffect("set_bool", slot_name="staged", value=1)),
        invariants=own_safe,
    )
    suppress_capture = RuleSemanticAction(
        name="suppress_capture", type_ids=("A",),
        geometry=RuleGeometrySpec(kind="leap", offset=(1, 0)),
        target_relation="enemy", composition="replace_legacy",
        replace_selector=RuleReplaceSelector(
            type_ids=("A",), action_family="board", target_relation="enemy",
            geometry_kind="ray", replace_all_matching=True,
        ),
        slot_guards=(RuleSlotGuard("staged", value=1),),
        effects=(RuleActionEffect("move", from_ref=ref("source"), to_ref=ref("target")),),
        invariants=own_safe,
    )
    finish = RuleSemanticAction(
        name="finish", type_ids=("A",),
        geometry=RuleGeometrySpec(kind="leap", offset=(-1, 0)),
        target_relation="empty", slot_guards=(RuleSlotGuard("replied", value=1),),
        effects=(RuleActionEffect("move", from_ref=ref("source"), to_ref=ref("target")),),
        invariants=own_safe,
    )
    reply1 = RuleSemanticAction(
        name="reply1", type_ids=("B",),
        geometry=RuleGeometrySpec(kind="leap", offset=(-1, 0)),
        target_relation="empty", slot_guards=(RuleSlotGuard("armed", value=1), RuleSlotGuard("staged", value=0)),
        effects=(RuleActionEffect("move", from_ref=ref("source"), to_ref=ref("target")),),
        invariants=own_safe,
    )
    reply2 = RuleSemanticAction(
        name="reply2", type_ids=("B",),
        geometry=RuleGeometrySpec(kind="leap", offset=(0, -1)),
        target_relation="empty", slot_guards=(RuleSlotGuard("staged", value=1), RuleSlotGuard("replied", value=0)),
        aux_state=(replied,),
        effects=(RuleActionEffect("move", from_ref=ref("source"), to_ref=ref("target")),
                 RuleActionEffect("set_bool", slot_name="replied", value=1)),
        invariants=own_safe,
    )
    strike = RuleSemanticAction(
        name="strike", type_ids=("C",),
        geometry=RuleGeometrySpec(kind="leap", offset=(0, -2)),
        target_relation="empty", composition="replace_legacy",
        replace_selector=RuleReplaceSelector(
            type_ids=("C",), action_family="board", target_relation="empty",
            geometry_kind="ray", replace_all_matching=True,
        ),
        slot_guards=(RuleSlotGuard("bad", value=1),),
        effects=(RuleActionEffect("move", from_ref=ref("source"), to_ref=ref("target")),),
        invariants=own_safe,
    )
    h_guarded = RuleSemanticAction(
        name="h_guarded", type_ids=("H",),
        geometry=RuleGeometrySpec(kind="leap", offset=(-2, -2)),
        target_relation="empty", composition="replace_legacy",
        replace_selector=RuleReplaceSelector(type_ids=("H",), action_family="board", target_relation="empty", geometry_kind="leap", replace_all_matching=True),
        slot_guards=(RuleSlotGuard("replied", value=0), RuleSlotGuard("started", value=0)),
        effects=(RuleActionEffect("move", from_ref=ref("source"), to_ref=ref("target")),), invariants=own_safe,
    )
    h_guarded_capture = RuleSemanticAction(
        name="h_guarded_capture", type_ids=("H",),
        geometry=RuleGeometrySpec(kind="leap", offset=(-2, -2)),
        target_relation="enemy", composition="replace_legacy",
        replace_selector=RuleReplaceSelector(type_ids=("H",), action_family="board", target_relation="enemy", geometry_kind="leap", replace_all_matching=True),
        slot_guards=(RuleSlotGuard("replied", value=0), RuleSlotGuard("started", value=0)),
        effects=(RuleActionEffect("move", from_ref=ref("source"), to_ref=ref("target")),), invariants=own_safe,
    )
    actions = (prepare, bad_move, stage, suppress_capture, finish, reply1, reply2, strike, h_guarded, h_guarded_capture)
    rules = replace(
        _semantic_ruleset((m["king"](), A, B, C, H, D), actions, n=n),
        max_ply=6, repetition_limit=2,
    )
    compiled = m["compile_semantic_ruleset"](rules)
    pieces = {
        (0, 0): "k", (4, 4): "K", (1, 3): "A", (2, 2): "b", (4, 0): "c",
        (0, 1): "d", (1, 0): "d", (1, 1): "d", (4, 1): "d", (2, 1): "h",
        (3, 3): "D", (3, 4): "D",
    }
    return compiled, pieces


def _identity(ruleset_id: str, state: dict[str, Any], label_kind: str) -> str:
    payload = {"ruleset_id": ruleset_id, "state": state, "label_kind": label_kind}
    return hashlib.sha256(f23c._imports()["canonical_json"](payload).encode()).hexdigest()


def _cases(m: dict[str, Any]) -> list[dict[str, Any]]:
    cases = []
    for variant in range(5):
        compiled, base_pieces = _semantic_variant(m, variant)
        for sample in range(6):
            pieces = dict(base_pieces)
            # Dead D inventory changes the exact state identity without adding
            # a legal move: D is intentionally not droppable in this ruleset.
            hands = (([("D", sample % 3)] if sample % 3 else []),
                     ([ ("D", sample // 3)] if sample // 3 else []))
            rows = _rows(5, pieces)
            state = m["make_state"](compiled, rows, hands=hands)
            result = solve_root(compiled, state, max_nodes=30000, max_depth=6)
            if not result.strong:
                raise RuntimeError(f"REFERENCE_SOLVE_UNRESOLVED:{variant}:{sample}:{result.unresolved_reason}")
            action_values = list(result.action_values)
            optimal_depths = [item["proof_depth"] for item in action_values if item["value"] == result.root_value]
            if not optimal_depths or min(optimal_depths) < 2:
                raise RuntimeError(f"IMMEDIATE_OPTIMAL_ROOT:{variant}:{sample}")
            ruleset_id = f"f23g-reply-chain-geometry-{variant}"
            state_spec = f23b.state_spec(state, m)
            identity = _identity(ruleset_id, state_spec, "exact_game_theoretic_optimal_set_deep")
            proof_class = "MULTIPLY_DEPENDENT" if min(optimal_depths) >= 3 else "REPLY_DEPENDENT"
            cases.append({
                "id": f"generic-deep-{variant}-{sample}",
                "ruleset_id": ruleset_id,
                "family": "exact_game_theoretic_preference_deep",
                "label_kind": "exact_game_theoretic_optimal_set_deep",
                "reference_authority": "complete bounded exact GenericChess game-theoretic solver",
                "reference_authority_class": "exact terminal minimax with history-aware cycle refusal",
                "source": "fixture:f23g-two-reply-auxiliary-chain",
                "solver": {"kind": "exact_root_wdl", "version": SOLVER_VERSION, "max_nodes": 30000, "max_depth": 6},
                "state": state_spec,
                "state_identity_sha256": identity,
                "split": "HOLDOUT" if int(identity[:8], 16) % 4 == 0 else "DEVELOPMENT",
                "supervision_class": "PREFERENCE_STRONG",
                "preference_authority": {
                    "root_actor": state_spec["side_to_move"],
                    "root_value": result.root_value,
                    "legal_root_action_count": len(action_values),
                    "optimal_root_actions": list(result.optimal_actions),
                    "all_root_action_values": action_values,
                    "optimal_proof_depths": optimal_depths,
                    "proof_depth_class": proof_class,
                    "max_ply_dependence": result.max_proof_ply >= 6,
                    "minimum_distinguishing_ply": min(optimal_depths),
                    "states_expanded": result.stats["states_expanded"],
                    "terminal_leaves": result.stats["terminal_leaves"],
                    "cycle_edges": result.stats["cycle_edges"],
                    "repetition_adjudications": result.stats["repetition_adjudications"],
                    "cap_hits": result.stats["cap_hits"],
                    "unresolved": result.stats["unresolved"],
                    "solver_version": SOLVER_VERSION,
                },
                "label": {"reference_actions": list(result.optimal_actions), "diagnostic_reference_action": result.optimal_actions[0]},
            })
    return cases


def build_corpus() -> dict[str, Any]:
    v3_bytes = V3.read_bytes()
    v3 = json.loads(v3_bytes)
    m = f23c._imports()
    deep = _cases(m)
    generic = copy.deepcopy(v3["generic_exact"]) + deep
    identities = [entry["state_identity_sha256"] for entry in generic]
    if len(identities) != len(set(identities)):
        raise RuntimeError("F23G_CANONICAL_DUPLICATE")
    deep_dev = [e for e in deep if e["split"] == "DEVELOPMENT"]
    deep_holdout = [e for e in deep if e["split"] == "HOLDOUT"]
    by_ruleset = Counter(e["ruleset_id"] for e in deep_dev)
    differing = sum(len({item["value"] for item in e["preference_authority"]["all_root_action_values"]}) > 1 for e in deep_dev)
    if len(deep) < 20 or len(deep_dev) < 16 or len(deep_holdout) < 4:
        raise RuntimeError("F23G_DEEP_SPLIT_MINIMUM_NOT_MET")
    if len(by_ruleset) < 5 or max(by_ruleset.values()) > len(deep_dev) * 0.35:
        raise RuntimeError("F23G_RULESET_DIVERSITY_GATE")
    if sum(e["preference_authority"]["proof_depth_class"] == "MULTIPLY_DEPENDENT" for e in deep_dev) < 8:
        raise RuntimeError("F23G_MULTIPLY_GATE")
    if differing * 2 <= len(deep_dev):
        raise RuntimeError("F23G_ACTION_VALUE_DIVERSITY_GATE")
    return {
        "schema_version": 4,
        "corpus_id": "evaluator-v2-corpus-v4",
        "source_v3_fixture": str(V3.relative_to(ROOT)).replace("\\", "/"),
        "source_v3_sha256": hashlib.sha256(v3_bytes).hexdigest(),
        "frozen_legacy_f22": copy.deepcopy(v3["frozen_legacy_f22"]),
        "generic_exact": generic,
        "supervision_classes": {e["id"]: e.get("supervision_class", "STRUCTURAL_ONLY") for e in generic},
        "sampling": {
            "feature_blind": True,
            "algorithm": "copy V3; add deterministic five-geometry two-reply auxiliary chains; exact W/D/L certification before split",
            "solver_excludes": ["Evaluator", "material", "feature", "AlphaSho", "F23F candidate"],
            "deduplication": "sha256(canonical ruleset_id/state/label_kind)",
            "orbit_and_near_duplicate_guard": "canonical identity plus five distinct movement geometries and dead-inventory state perturbations",
        },
        "split": {
            "algorithm": v3["split"]["algorithm"], "frozen_before_fitting": True,
            "development_count": sum(e["split"] == "DEVELOPMENT" for e in generic),
            "holdout_count": sum(e["split"] == "HOLDOUT" for e in generic),
        },
        "strata": {
            "historical_v1_v2_v3_prefix": len(v3["generic_exact"]),
            "strong_deep_f23g": len(deep),
            "deep_development": len(deep_dev),
            "deep_holdout": len(deep_holdout),
            "deep_rulesets": sorted({e["ruleset_id"] for e in deep}),
            "deep_multiply_dependent_development": sum(e["preference_authority"]["proof_depth_class"] == "MULTIPLY_DEPENDENT" for e in deep_dev),
            "deep_differing_action_value_development": differing,
            "deep_max_ply_dependent": sum(e["preference_authority"]["max_ply_dependence"] for e in deep),
        },
        "coverage": {
            "generic_positions_v3": len(v3["generic_exact"]),
            "generic_positions_added_v4": len(deep),
            "generic_positions": len(generic),
            "strong_development": sum(e["split"] == "DEVELOPMENT" for e in deep),
            "strong_holdout": sum(e["split"] == "HOLDOUT" for e in deep),
            "strong_rulesets": sorted({e["ruleset_id"] for e in deep}),
            "strong_ruleset_count": len({e["ruleset_id"] for e in deep}),
        },
        "production_changed": False,
        "alpha_sho_changed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    corpus = build_corpus()
    args.output.write_text(json.dumps(corpus, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "added": corpus["coverage"]["generic_positions_added_v4"], "deep_dev": corpus["strata"]["deep_development"], "deep_holdout": corpus["strata"]["deep_holdout"], "rulesets": corpus["coverage"]["strong_ruleset_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
