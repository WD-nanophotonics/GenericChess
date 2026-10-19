"""Bounded probe: declaration-order-sensitive semantic-action tie breaking."""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.movegen import legal_actions
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.schema import (
    RuleActionEffect,
    RuleGeometrySpec,
    RuleInvariant,
    RuleSemanticAction,
    RuleSquareRef,
    compute_fingerprint,
)
from generic_chess.session.session import GameSession
from rule_semantics_ir_fixtures import _semantic_ruleset


class FlatEvaluator:
    """Deliberately tie every leaf; this tests ordering, not playing strength."""

    def evaluate(self, state) -> int:
        return 0


def _rows(n: int, entries: list[tuple[int, int, Piece]]) -> tuple:
    rows = [[None] * n for _ in range(n)]
    for file, rank, piece in entries:
        rows[rank][file] = piece
    return tuple(tuple(row) for row in rows)


def _action(name: str, df: int) -> RuleSemanticAction:
    return RuleSemanticAction(
        name=name,
        type_ids=("A",),
        geometry=RuleGeometrySpec(kind="leap", offset=(df, 0)),
        target_relation="empty",
        composition="augment",
        effects=(RuleActionEffect(
            "move",
            from_ref=RuleSquareRef("source"),
            to_ref=RuleSquareRef("target"),
        ),),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )


def run() -> dict:
    n = 5
    # Immobile anchors remove irrelevant king branches. A has no legacy atoms:
    # its entire legal move set comes from the two compiled semantic actions.
    kings = PieceType("K", "K", (), is_anchor=True)
    mover = PieceType("A", "A", ())
    actions = (_action("east", 1), _action("west", -1))
    ruleset = _semantic_ruleset(
        (kings, mover),
        actions,
        n=n,
        rows=_rows(n, [
            (0, 0, Piece(0, "K", "K")),
            (4, 4, Piece(1, "K", "K")),
            (2, 2, Piece(0, "A", "A")),
            (0, 2, Piece(0, "A", "A")),
            (4, 2, Piece(1, "A", "A")),
        ]),
    )
    variants = (
        ruleset,
        replace(ruleset, semantic_actions=tuple(reversed(actions))),
    )
    compiled = [compile_semantic_ruleset(item) for item in variants]
    fingerprints = [compute_fingerprint(item) for item in variants]
    budgets = (
        {"max_depth": 2, "max_nodes": 11},
        {"max_depth": 3, "max_nodes": 16},
    )
    results = []
    for budget in budgets:
        arms = []
        for item in compiled:
            session = GameSession(item)
            visible_legal = sorted(
                str(action).split(":")[-1]
                for action in legal_actions(session.state, item)
                if getattr(action, "actor_type_id", None) == "A"
            )
            player = AlphaBetaPlayer(
                item,
                evaluator_override=FlatEvaluator(),
                use_disk_cache=False,
                use_tt=False,
                use_ordering=True,
                use_native_semantic_legality=False,
                tuning=SearchTuning(use_root_tactical=False),
            )
            decision = player.choose_action(
                session,
                SearchLimits(**budget, quiescence_max_depth=0),
            )
            arms.append({
                "visible_legal_actions_by_A": visible_legal,
                "selected_action": str(decision.action),
                "selected_visible_action": str(decision.action).split(":")[-1],
                "score": decision.score,
                "completed_depth": decision.completed_depth,
                "nodes": decision.nodes,
                "termination_reason": decision.termination_reason,
            })
        results.append({"budget": budget, "arms": arms})
    assert fingerprints[0] != fingerprints[1]
    for result in results:
        first, reversed_order = result["arms"]
        assert first["visible_legal_actions_by_A"] == reversed_order["visible_legal_actions_by_A"]
        assert first["score"] == reversed_order["score"] == 0
        assert first["completed_depth"] == reversed_order["completed_depth"] == 2
        assert first["nodes"] == reversed_order["nodes"]
        assert first["selected_visible_action"] != reversed_order["selected_visible_action"]
    return {
        "question": "Does reversing behavior-equivalent semantic action declarations alter completed-search output beyond an exact tie?",
        "scope": "Synthetic 5x5 semantic-only fixture; flat leaf evaluator; same visible action set; no utility claim.",
        "fingerprints": fingerprints,
        "budgets": [{**item, "quiescence_max_depth": 0} for item in budgets],
        "results_by_budget": results,
        "interpretation": "Only the selected visible move among exactly tied score-0 actions changed. The declaration sequence changes the ruleset fingerprint, so this does not violate an established cross-encoding contract.",
    }


if __name__ == "__main__":
    output = run()
    print(json.dumps(output, ensure_ascii=False, indent=2))
