"""Generic low-budget Gumbel-root sequential-halving semantic MCTS."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import random
import time

import numpy as np

from ..native.adapter import pack_semantic_search_position
from ..native.semantic import (
    available_declarations,
    evaluate,
    make_checked,
    policy_logits,
    terminal_status,
)


class UnsupportedNeutralDeclaration(RuntimeError):
    """A declaration changes the decision set but is not a winning claim."""

    code = "GUMBEL_MCTS_UNSUPPORTED_NEUTRAL_DECLARATION"


@dataclass(slots=True)
class _Edge:
    action: int
    prior: float
    gumbel_log_prior: float = 0.0
    visits: int = 0
    total_value: float = 0.0
    child: "_Node | None" = None

    @property
    def q(self) -> float:
        return self.total_value / self.visits if self.visits else 0.0


@dataclass(slots=True)
class _Node:
    position: object
    side_to_move: int
    edges: dict[int, _Edge] = field(default_factory=dict)
    expanded: bool = False
    visits: int = 0
    terminal: dict | None = None


@dataclass(frozen=True, slots=True)
class GumbelSearchResult:
    action: int | None
    declaration_id: str | None
    root_actions: tuple[int, ...]
    root_logits: tuple[float, ...]
    root_priors: tuple[float, ...]
    root_gumbels: tuple[float, ...]
    root_visits: tuple[int, ...]
    root_q_values: tuple[float, ...]
    root_completed_q: tuple[float, ...]
    root_q_transform: tuple[float, ...]
    root_improvement_logits: tuple[float, ...]
    improved_policy: tuple[float, ...]
    visit_policy: tuple[float, ...]
    target_policy: tuple[float, ...]
    root_raw_value: float
    root_rounds: tuple[dict, ...]
    simulations: int
    expanded_nodes: int
    leaf_evaluations: int
    maximum_tree_depth: int
    declaration_encounters: int
    wall_seconds: float
    root_position_key: str


class SemanticGumbelMCTSV0:
    """A deliberately bounded, tree-only Gumbel-root MCTS backend.

    The backend depends on the Native semantic position interface and accepts
    ``policy=None`` for generic uniform-prior smoke tests.
    """

    def __init__(
        self,
        compiled,
        native_rules,
        *,
        checkpoint=None,
        policy=None,
        simulations: int = 64,
        root_candidates: int = 8,
        max_tree_depth: int = 64,
    ) -> None:
        if simulations not in (16, 64):
            raise ValueError(
                "F115 supports only 16-simulation smoke or 64-simulation production searches"
            )
        if root_candidates != 8:
            raise ValueError("F115 fixes the root candidate cap at 8")
        if max_tree_depth <= 0:
            raise ValueError("max_tree_depth must be positive")
        self.compiled = compiled
        self.native_rules = native_rules
        self.checkpoint = checkpoint
        self.policy = policy
        self.simulations = simulations
        self.root_candidates = root_candidates
        self.max_tree_depth = max_tree_depth
        self._expanded_nodes = 0
        self._leaf_evaluations = 0
        self._maximum_depth = 0
        self._declaration_encounters = 0

    def _declaration_value(self, position):
        assessments = available_declarations(self.native_rules, position)
        if not assessments:
            return None, None
        self._declaration_encounters += len(assessments)
        winning = [item for item in assessments if item.outcome == "WIN"]
        if winning:
            return 1.0, winning[0].declaration_id
        raise UnsupportedNeutralDeclaration(
            UnsupportedNeutralDeclaration.code
        )

    def _terminal_value(self, position):
        declaration_value, declaration_id = self._declaration_value(position)
        if declaration_value is not None:
            return declaration_value, declaration_id
        status = terminal_status(self.native_rules, position)
        if status["status"] == "ongoing":
            return None, None
        if status["status"] == "checkmate":
            return (1.0 if status["winner"] == self._side(position) else -1.0), None
        return 0.0, None

    @staticmethod
    def _side(position) -> int:
        # The Native snapshot is intentionally avoided in the hot path.  The
        # side is carried by each Node and this helper is only overridden by
        # the caller before terminal evaluation.
        raise RuntimeError("node side must be supplied to terminal evaluation")

    def _value(self, position, side_to_move: int) -> float:
        self._leaf_evaluations += 1
        if self.checkpoint is None:
            return 0.0
        score = evaluate(
            self.native_rules,
            position,
            board_values=self.checkpoint.semantic_quantized_board(self.native_rules.type_ids),
            hand_values=self.checkpoint.semantic_quantized_hand(self.native_rules.type_ids),
            dynamic_values=self.checkpoint.semantic_quantized_dynamic(),
            spatial_occupancy_values=self.checkpoint.semantic_quantized_spatial(self.native_rules.type_ids),
            localized_control_values=self.checkpoint.semantic_quantized_localized_control(),
            compact_values=self.checkpoint.compact_nonlinear,
            evaluator_scale=self.checkpoint.semantic_native_scale,
        )
        scale = float(self.checkpoint.semantic_native_scale * self.checkpoint.value_scale)
        return float(np.tanh(float(score) / scale))

    def _policy(self, position):
        if self.policy is None:
            # Uniform smoke mode still uses the complete checked action set.
            from ..native.semantic import guarded_actions

            actions = tuple(guarded_actions(self.native_rules, position))
            return actions, tuple(0.0 for _ in actions)
        raw = policy_logits(self.native_rules, position, self.policy)
        return tuple(raw["actions"]), tuple(raw["logits"])

    def _expand(self, node: _Node):
        if node.expanded:
            return
        terminal, declaration_id = self._terminal_for_node(node)
        if terminal is not None:
            node.terminal = {"value": terminal, "declaration_id": declaration_id}
            node.expanded = True
            return
        actions, logits = self._policy(node.position)
        if len(actions) != len(logits):
            raise RuntimeError("GUMBEL_MCTS_POLICY_LOGIT_LENGTH_MISMATCH")
        if not actions:
            node.terminal = {"value": 0.0, "declaration_id": None}
            node.expanded = True
            return
        probabilities = _softmax(logits)
        node.edges = {
            int(action): _Edge(int(action), float(prior))
            for action, prior in zip(actions, probabilities)
        }
        node.expanded = True
        self._expanded_nodes += 1

    def _terminal_for_node(self, node: _Node):
        assessments = available_declarations(self.native_rules, node.position)
        if assessments:
            self._declaration_encounters += len(assessments)
            winning = [item for item in assessments if item.outcome == "WIN"]
            if winning:
                return 1.0, winning[0].declaration_id
            raise UnsupportedNeutralDeclaration(
                UnsupportedNeutralDeclaration.code
            )
        status = terminal_status(self.native_rules, node.position)
        if status["status"] == "ongoing":
            return None, None
        if status["status"] == "checkmate":
            return (1.0 if status["winner"] == node.side_to_move else -1.0), None
        return 0.0, None

    def _child(self, node: _Node, edge: _Edge) -> _Node:
        if edge.child is None:
            child_position = make_checked(
                self.native_rules, node.position, edge.action
            )
            edge.child = _Node(child_position, 1 - node.side_to_move)
        return edge.child

    def _simulate(self, node: _Node, depth: int) -> float:
        self._maximum_depth = max(self._maximum_depth, depth)
        if depth >= self.max_tree_depth:
            return self._value(node.position, node.side_to_move)
        if not node.expanded:
            self._expand(node)
            if node.terminal is not None:
                return float(node.terminal["value"])
            return self._value(node.position, node.side_to_move)
        if node.terminal is not None:
            return float(node.terminal["value"])
        if not node.edges:
            return 0.0
        node.visits += 1
        edge = max(
            node.edges.values(),
            key=lambda item: (
                item.q + 1.5 * item.prior * math.sqrt(max(1, node.visits)) /
                (1 + item.visits),
                -item.action,
            ),
        )
        child_value = self._simulate(self._child(node, edge), depth + 1)
        parent_value = -child_value
        edge.visits += 1
        edge.total_value += parent_value
        return parent_value

    def search(self, session, *, search_seed: int) -> GumbelSearchResult:
        started = time.perf_counter()
        self._expanded_nodes = 0
        self._leaf_evaluations = 0
        self._maximum_depth = 0
        self._declaration_encounters = 0
        position = pack_semantic_search_position(
            self.compiled, self.native_rules, session
        )
        from ..native.semantic import position_key

        root_key = position_key(self.native_rules, position)
        root = _Node(position, int(session.state.position.side_to_move))
        root_declarations = available_declarations(self.native_rules, position)
        if root_declarations:
            self._declaration_encounters += len(root_declarations)
            winning = [item for item in root_declarations if item.outcome == "WIN"]
            if winning:
                return GumbelSearchResult(
                    action=None, declaration_id=winning[0].declaration_id,
                    root_actions=(), root_logits=(), root_priors=(),
                    root_gumbels=(), root_visits=(), root_q_values=(),
                    root_completed_q=(), root_q_transform=(),
                    root_improvement_logits=(), improved_policy=(),
                    visit_policy=(), target_policy=(), root_raw_value=1.0,
                    root_rounds=(), simulations=0, expanded_nodes=0,
                    leaf_evaluations=0, maximum_tree_depth=0,
                    declaration_encounters=self._declaration_encounters,
                    wall_seconds=time.perf_counter() - started,
                    root_position_key=root_key,
                )
            raise UnsupportedNeutralDeclaration(
                UnsupportedNeutralDeclaration.code
            )
        root_raw_value = self._value(position, root.side_to_move)
        self._expand(root)
        # Preserve the Native policy action order in the artifact, while every
        # tie-break and target index remains tied to the exact packed identity.
        ordered_actions = tuple(root.edges)
        logits = tuple(float(logit) for logit in (
            policy_logits(self.native_rules, position, self.policy)["logits"]
            if self.policy is not None else [0.0] * len(ordered_actions)
        ))
        if len(ordered_actions) != len(logits):
            raise RuntimeError("GUMBEL_MCTS_ROOT_POLICY_LENGTH_MISMATCH")
        priors = tuple(root.edges[action].prior for action in ordered_actions)
        rng = random.Random(int(search_seed))
        gumbels = []
        for action, logit in zip(ordered_actions, logits):
            gumbel = _gumbel(rng)
            gumbels.append(gumbel)
            edge = root.edges[action]
            edge.gumbel_log_prior = gumbel + float(logit)
        ranked = sorted(
            ordered_actions,
            key=lambda action: (-root.edges[action].gumbel_log_prior, action),
        )[: min(self.root_candidates, len(ordered_actions))]
        remaining = self.simulations
        candidates = list(ranked)
        rounds = []
        round_index = 0
        while len(candidates) > 1 and remaining > 0:
            remaining_rounds, base, allocations = _root_round_allocation(
                remaining, len(candidates)
            )
            consumed = sum(allocations)
            before_actions = tuple(candidates)
            before_visits = tuple(root.edges[action].visits for action in candidates)
            before_q = tuple(root.edges[action].q for action in candidates)
            before_nmax = max(before_visits, default=0)
            before_q_transform = tuple(_q_transform(q, before_nmax) for q in before_q)
            before_scores = tuple(
                root.edges[action].gumbel_log_prior + transformed
                for action, transformed in zip(candidates, before_q_transform)
            )
            for action, budget in zip(candidates, allocations):
                for _ in range(budget):
                    root.visits += 1
                    edge = root.edges[action]
                    value = self._simulate(self._child(root, edge), 1)
                    edge.visits += 1
                    edge.total_value += -value
            remaining -= consumed
            ranked_survivors = _rank_candidates(root, candidates)
            survivors = tuple(ranked_survivors[: math.ceil(len(ranked_survivors) / 2)])
            candidates = list(survivors)
            rounds.append({
                "round_index": round_index,
                "candidate_actions_before": before_actions,
                "candidate_count": len(before_visits),
                "remaining_before": remaining + consumed,
                "remaining_rounds": remaining_rounds,
                "base_allocation": base,
                "allocations": tuple(allocations),
                "visits_before": before_visits,
                "q_values_before": before_q,
                "nmax_before": before_nmax,
                "q_transform_before": before_q_transform,
                "improvement_scores_before": before_scores,
                "visits_after": tuple(root.edges[action].visits for action in survivors),
                "q_values_after": tuple(root.edges[action].q for action in survivors),
                "nmax_after": max((root.edges[action].visits for action in survivors), default=0),
                "q_transform_after": tuple(_q_transform(root.edges[action].q, max((root.edges[item].visits for item in survivors), default=0)) for action in survivors),
                "improvement_scores_after": tuple(_root_improvement_score(root, action) for action in survivors),
                "survivors": survivors,
                "simulations_consumed": consumed,
                "remaining_after": remaining,
            })
            round_index += 1
        if candidates and remaining > 0:
            edge = root.edges[candidates[0]]
            for _ in range(remaining):
                root.visits += 1
                value = self._simulate(self._child(root, edge), 1)
                edge.visits += 1
                edge.total_value += -value
            final_allocations = tuple(
                remaining // len(candidates) + (index < remaining % len(candidates))
                for index in range(len(candidates))
            )
            rounds.append({
                "round_index": round_index,
                "candidate_actions_before": tuple(candidates),
                "candidate_count": len(candidates),
                "remaining_before": remaining,
                "remaining_rounds": 1,
                "base_allocation": remaining // len(candidates),
                "allocations": final_allocations,
                "visits_before": tuple(root.edges[action].visits - final_allocations[index] for index, action in enumerate(candidates)),
                "q_values_before": (),
                "visits_after": tuple(root.edges[action].visits for action in candidates),
                "q_values_after": tuple(root.edges[action].q for action in candidates),
                "nmax_after": max((root.edges[action].visits for action in candidates), default=0),
                "q_transform_after": tuple(_q_transform(root.edges[action].q, max((root.edges[item].visits for item in candidates), default=0)) for action in candidates),
                "improvement_scores_after": tuple(_root_improvement_score(root, action) for action in candidates),
                "survivors": tuple(candidates),
                "simulations_consumed": remaining,
                "remaining_after": 0,
            })
        visits = tuple(root.edges[action].visits for action in ordered_actions)
        q_values = tuple(root.edges[action].q for action in ordered_actions)
        visit_policy = tuple(float(value) / self.simulations for value in visits)
        nmax_final = max(visits, default=0)
        completed_q = tuple(
            root.edges[action].q if root.edges[action].visits else root_raw_value
            for action in ordered_actions
        )
        q_transform = tuple(_q_transform(value, nmax_final) for value in completed_q)
        improvement_logits = tuple(
            float(logit) + transformed
            for logit, transformed in zip(logits, q_transform)
        )
        improved_policy = _softmax(improvement_logits)
        if (
            not all(math.isfinite(value) and -1.0 - 1e-9 <= value <= 1.0 + 1e-9 for value in completed_q)
            or not all(value > 0.0 for value in improved_policy)
            or abs(sum(improved_policy) - 1.0) > 1e-12
        ):
            raise RuntimeError("GUMBEL_COMPLETED_Q_POLICY_TARGET_INVALID")
        selected = candidates[0] if candidates else None
        return GumbelSearchResult(
            action=selected, declaration_id=None, root_actions=ordered_actions,
            root_logits=logits, root_priors=priors, root_gumbels=tuple(gumbels),
            root_visits=visits, root_q_values=q_values,
            root_completed_q=completed_q, root_q_transform=q_transform,
            root_improvement_logits=improvement_logits,
            improved_policy=improved_policy, visit_policy=visit_policy,
            target_policy=improved_policy, root_raw_value=root_raw_value,
            root_rounds=tuple(rounds), simulations=sum(visits),
            expanded_nodes=self._expanded_nodes,
            leaf_evaluations=self._leaf_evaluations,
            maximum_tree_depth=self._maximum_depth,
            declaration_encounters=self._declaration_encounters,
            wall_seconds=time.perf_counter() - started,
            root_position_key=root_key,
        )


def _softmax(values):
    if not values:
        return ()
    array = np.asarray(values, dtype=np.float64)
    array -= np.max(array)
    weights = np.exp(array)
    return tuple((weights / np.sum(weights)).tolist())


def _gumbel(rng: random.Random) -> float:
    value = min(max(rng.random(), 1e-12), 1.0 - 1e-12)
    return -math.log(-math.log(value))


def _q_transform(q: float, nmax: int) -> float:
    return (50.0 + float(nmax)) * 0.1 * float(q)


def _root_improvement_score(root: _Node, action: int) -> float:
    nmax = max((edge.visits for edge in root.edges.values()), default=0)
    edge = root.edges[action]
    return edge.gumbel_log_prior + _q_transform(edge.q, nmax)


def _rank_candidates(root: _Node, candidates):
    return sorted(
        candidates,
        key=lambda action: (
            -_root_improvement_score(root, action),
            action,
        ),
    )


__all__ = [
    "GumbelSearchResult",
    "SemanticGumbelMCTSV0",
    "UnsupportedNeutralDeclaration",
]


def _root_round_allocation(remaining: int, candidate_count: int):
    """Return one exact halving-round allocation.

    Non-final rounds consume only their equal base allocation; the final
    round consumes all residual simulations in deterministic candidate order.
    """
    if remaining <= 0 or candidate_count <= 0:
        raise ValueError("remaining and candidate_count must be positive")
    remaining_rounds = max(1, math.ceil(math.log2(candidate_count)))
    base = max(1, remaining // (candidate_count * remaining_rounds))
    allocations = [base] * candidate_count
    if remaining_rounds == 1:
        for index in range(remaining - sum(allocations)):
            allocations[index % candidate_count] += 1
    return remaining_rounds, base, tuple(allocations)


def _allocation_schedule(simulations: int, initial_count: int):
    """Pure deterministic schedule witness used by the F116 regression tests."""
    remaining = simulations
    candidate_count = initial_count
    schedule = []
    while candidate_count > 1:
        rounds, base, allocations = _root_round_allocation(remaining, candidate_count)
        consumed = sum(allocations)
        schedule.append((candidate_count, remaining, rounds, base, allocations, consumed))
        remaining -= consumed
        candidate_count = math.ceil(candidate_count / 2)
    if candidate_count and remaining > 0:
        rounds, base, allocations = _root_round_allocation(remaining, candidate_count)
        schedule.append((candidate_count, remaining, rounds, base, allocations, sum(allocations)))
    return tuple(schedule)


__all__ += ["_allocation_schedule", "_root_round_allocation"]
