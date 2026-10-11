"""Real rejected-bind and nested-payload/TT regressions from DEV_AUX witnesses."""
from copy import deepcopy
import pytest
from generic_chess import build_builtin_ruleset, compile_ruleset_for_execution
from generic_chess.native import native_available
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.native.semantic import semantic_iterative_search
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.session.session import GameSession
from generic_chess.ai.limits import SearchLimits
from generic_chess.learning.material import LearnableMaterialCheckpoint
from test_f58_compact_nonlinear import _native_constant_compact_model

pytestmark = pytest.mark.skipif(not native_available(), reason="native extension unavailable")


def _fixture():
    c = compile_ruleset_for_execution(build_builtin_ruleset("western_chess"))
    n = compile_native_semantic_rules(c)
    s = GameSession(c)
    zero = {t: 0 for t in n.type_ids}
    model = _native_constant_compact_model(c, s)
    model["output_bias"] = 0.
    limits = SearchLimits(max_depth=2, max_nodes=10000, quiescence_max_depth=0)
    return c, n, s, zero, model, limits


@pytest.mark.parametrize("failure", ["python_scale", "native_width"])
def test_rejected_direct_bind_preserves_profile_capsule_tt_and_real_search(failure):
    c, n, s, zero, model, limits = _fixture()
    e = SemanticSearchEngine(c, n, board_values=zero, hand_values=zero,
                             compact_values=model, tt_megabytes=1)
    saved_state, saved_witness = s.state, s._search_witnesses
    assert e.search(s, limits).score == 0
    old, values, tt = e._capsule, e.native_evaluator_values, e.tt_info()
    assert tt["occupied_entries"] > 0
    bad = deepcopy(model)
    bad["width"] = 17 if failure == "native_width" else 16
    with pytest.raises(ValueError):
        e.bind_evaluator({t: 1 for t in zero}, zero, compact_values=bad,
                         evaluator_scale=0 if failure == "python_scale" else 1)
    assert e._capsule is old and e.native_evaluator_values == values
    assert e.tt_info() == tt
    warm = e.search(s, limits)
    assert warm.score == 0 and warm.tt_hits > 0
    assert s.state == saved_state and s._search_witnesses == saved_witness


def test_compact_input_and_getter_cannot_mutate_warm_tt_binding():
    c, n, s, zero, model, limits = _fixture()
    e = SemanticSearchEngine(c, n, board_values=zero, hand_values=zero,
                             compact_values=model, tt_megabytes=1)
    assert e.search(s, limits).score == 0
    old, values = e._capsule, e.native_evaluator_values
    model["output_bias"] = 100.
    model["hidden_weights"][0][0] = 7.
    exposed = e.native_evaluator_values["compact_nonlinear"]
    exposed["output_bias"] = 200.
    exposed["hidden_bias"][0] = 50.
    assert e.native_evaluator_values == values and e._capsule is old
    assert e.search(s, limits).score == 0
    e.clear_tt()
    assert e.search(s, limits).score == 0
    model["hidden_weights"][0][0] = 0.
    e.bind_evaluator(zero, zero, compact_values=model)
    assert e._capsule is not old and e.tt_info()["occupied_entries"] == 0
    assert e.search(s, limits).score == 100


def test_public_checkpoint_c_rejection_preserves_id_and_retry_then_valid_commit():
    c, n, s, zero, model, limits = _fixture()
    e = SemanticSearchEngine(c, n, board_values=zero, hand_values=zero, tt_megabytes=1)
    assert e.search(s, limits).score == 0
    old, values, old_id, tt = e._capsule, e.native_evaluator_values, e.checkpoint_id, e.tt_info()
    bad = deepcopy(model)
    bad["width"] = 17
    bad_cp = LearnableMaterialCheckpoint.from_dict(LearnableMaterialCheckpoint(
        ruleset_fingerprint=c.ruleset_fingerprint, board_weights=zero,
        hand_weights=zero, compact_nonlinear=bad).to_dict())
    bad_cp.validate_ruleset(c)  # Public validation passes; actual C rejects width17.
    for _ in range(2):
        with pytest.raises(ValueError, match="width"):
            e.bind_checkpoint(bad_cp)
        assert e._capsule is old and e.native_evaluator_values == values
        assert e.checkpoint_id == old_id and e.tt_info() == tt
    model["output_bias"] = 100.
    cp = LearnableMaterialCheckpoint(ruleset_fingerprint=c.ruleset_fingerprint,
        board_weights=zero, hand_weights=zero, compact_nonlinear=model)
    assert cp.checkpoint_id != bad_cp.checkpoint_id
    e.bind_checkpoint(cp)
    assert e._capsule is not old and e.checkpoint_id == cp.checkpoint_id
    assert e.tt_info()["occupied_entries"] == 0
    bound = e.native_evaluator_values
    cp.compact_nonlinear["output_bias"] = 999.
    cp.compact_nonlinear["hidden_bias"][0] = 50.
    assert e.native_evaluator_values == bound
    assert e.search(s, limits).score == 100 * bound["scale"]


def test_ordering_checkpoint_owns_nested_compact_input():
    c, n, s, zero, model, limits = _fixture()
    cp = LearnableMaterialCheckpoint(ruleset_fingerprint=c.ruleset_fingerprint,
        board_weights=zero, hand_weights=zero, compact_nonlinear=model)
    e = SemanticSearchEngine(c, n, board_values=zero, hand_values=zero,
                             ordering_checkpoint=cp, tt_megabytes=1)
    owned = deepcopy(e._ordering_compact_values)
    cp.compact_nonlinear["hidden_weights"][0][0] = 7.
    cp.compact_nonlinear["output_bias"] = 100.
    assert e._ordering_compact_values == owned
    result = e.search(s, limits)
    assert result.learned_move_ordering and result.ordering_evaluations > 0
    assert result.score == 0  # Leaf profile remains separate from ordering.


@pytest.mark.parametrize("lengths", [(8, 10), (18, 0)])
def test_compensated_spatial_rows_are_rejected_by_both_public_entries(lengths):
    c, n, s, zero, model, limits = _fixture()
    rows = {f"{o}:{t}": [0]*9 for o in (0, 1) for t in n.type_ids}
    a, b = list(rows)[:2]
    rows[a], rows[b] = [0]*lengths[0], [0]*lengths[1]
    assert sum(map(len, rows.values())) == 2*len(n.type_ids)*9
    with pytest.raises(ValueError, match="mapping row"):
        SemanticSearchEngine(c, n, spatial_occupancy_values=rows, tt_megabytes=0)
    packed = pack_semantic_search_position(c, n, s)
    with pytest.raises(ValueError, match="mapping row"):
        semantic_iterative_search(n, packed, 1, spatial_occupancy_values=rows)
