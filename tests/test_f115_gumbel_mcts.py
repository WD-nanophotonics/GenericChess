import json
from pathlib import Path
from scripts.f115_shogi_gumbel_mcts_policy_iteration_arena2 import (
    ARENA_OPENING_SEED,
    ARENA_SEARCH_SEED_BASE,
    CONSISTENCY_SEED_BASE,
    GENERICITY_SEED_BASE,
    SELFPLAY_SEED_BASE,
    TRAINING_SEED,
)

from generic_chess.learning.gumbel_mcts import (
    SemanticGumbelMCTSV0,
    _Edge,
    _Node,
    _allocation_schedule,
    _rank_candidates,
)
from generic_chess.learning.policy_v1 import SemanticPolicyV1
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic import policy_logits
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.session.session import GameSession


ROOT = Path(__file__).resolve().parents[1]
POLICY_REPORT = ROOT / ".generic_chess_flow" / "f111-offline.json"


def _context():
    compiled = compile_semantic_ruleset(build_standard_shogi_ruleset())
    native_rules = compile_native_semantic_rules(compiled)
    return compiled, native_rules


def _policy():
    report = json.loads(POLICY_REPORT.read_text(encoding="utf-8"))
    return SemanticPolicyV1.from_dict(
        report["rulesets"]["standard_shogi"]["policy_v1_artifact"]
    )


def test_f115_gumbel_smoke_has_exact_sixteen_simulation_budget():
    compiled, native_rules = _context()
    result = SemanticGumbelMCTSV0(
        compiled, native_rules, simulations=16, policy=None
    ).search(GameSession(compiled), search_seed=1150101)
    assert result.action in result.root_actions
    assert result.simulations == 16
    assert sum(result.root_visits) == 16
    assert len(result.root_actions) == len(result.root_gumbels)
    assert len(result.root_rounds) == 3
    assert len(result.improved_policy) == len(result.root_actions)
    assert result.target_policy == result.improved_policy
    assert all(value > 0.0 for value in result.improved_policy)
    assert abs(sum(result.improved_policy) - 1.0) < 1e-12
    assert abs(sum(result.target_policy) - 1.0) < 1e-12


def test_f115_gumbel_is_deterministic_for_uniform_smoke():
    compiled, native_rules = _context()
    session = GameSession(compiled)
    a = SemanticGumbelMCTSV0(
        compiled, native_rules, simulations=64, policy=None
    ).search(session, search_seed=1150101)
    b = SemanticGumbelMCTSV0(
        compiled, native_rules, simulations=64, policy=None
    ).search(session, search_seed=1150101)
    assert a.action == b.action
    assert a.root_actions == b.root_actions
    assert a.root_gumbels == b.root_gumbels
    assert a.root_visits == b.root_visits
    assert a.target_policy == b.target_policy
    assert a.root_rounds == b.root_rounds


def test_f116_corrected_eight_candidate_schedule():
    compiled, native_rules = _context()
    result = SemanticGumbelMCTSV0(
        compiled, native_rules, simulations=64, policy=None
    ).search(GameSession(compiled), search_seed=1150101)
    rounds = result.root_rounds
    assert [row["candidate_count"] for row in rounds] == [8, 4, 2]
    assert [row["allocations"] for row in rounds] == [(2,) * 8, (6,) * 4, (12,) * 2]
    assert [row["simulations_consumed"] for row in rounds] == [16, 24, 24]
    assert [row["remaining_after"] for row in rounds] == [48, 24, 0]
    assert len(rounds[-1]["survivors"]) == 1
    assert sum(row["simulations_consumed"] for row in rounds) == 64


def test_f116_all_initial_candidate_counts_have_exact_schedule():
    for initial_count in range(2, 9):
        schedule = _allocation_schedule(64, initial_count)
        assert sum(row[5] for row in schedule) == 64
        assert schedule[-1][0] == 2 or initial_count == 2
        assert all(all(allocation >= 1 for allocation in row[4]) for row in schedule)
        assert all(row[2] == 1 for row in schedule[-1:])


def test_f117_halving_ranks_gumbel_logit_plus_transformed_q():
    root = _Node(None, 0)
    root.edges = {
        10: _Edge(10, 0.5, gumbel_log_prior=0.0, visits=4, total_value=4.0),
        20: _Edge(20, 0.2, gumbel_log_prior=1.0, visits=4, total_value=0.0),
    }
    # Action 10 has transformed Q=4.0 while action 20 has transformed Q=0;
    # the declared improvement score therefore keeps action 10.
    assert _rank_candidates(root, [20, 10]) == [10, 20]


def test_f118_seed_contract_constants_are_exact():
    assert GENERICITY_SEED_BASE == 1180001
    assert SELFPLAY_SEED_BASE == 1180101
    assert TRAINING_SEED == 1180111
    assert CONSISTENCY_SEED_BASE == 1180201
    assert ARENA_OPENING_SEED == 1180801
    assert ARENA_SEARCH_SEED_BASE == 1180901


def test_f115_native_policy_logits_order_is_stable():
    compiled, native_rules = _context()
    policy = _policy()
    session = GameSession(compiled)
    position = pack_semantic_search_position(compiled, native_rules, session)
    first = policy_logits(native_rules, position, policy)
    second = policy_logits(native_rules, position, policy)
    assert first == second
    assert len(first["actions"]) == len(first["logits"])
    assert len(first["actions"]) > 1
