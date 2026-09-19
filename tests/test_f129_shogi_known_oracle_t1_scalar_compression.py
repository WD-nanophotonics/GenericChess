from __future__ import annotations

from scripts.f122_reverse_benchmark_known_evaluator_system_identification import FrozenBasis
from scripts.f129_shogi_known_oracle_t1_scalar_compression import _load_or_generate_shards
from generic_chess.core.identity import position_identity_key
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset


def test_f129_materialized_root_generates_and_reuses_verified_t1_shard(tmp_path):
    compiled = compile_semantic_ruleset(build_standard_shogi_ruleset())
    basis = FrozenBasis("standard_shogi", compiled)
    state = initial_state(compiled)
    features = basis.vector(state)
    root = {
        "identity": str(position_identity_key(state.position, compiled)),
        "state": state,
        "split": "train",
        "features": features.tolist(),
        "oracle": basis.oracle(features),
        "direct_oracle": basis.oracle(features),
    }
    output = tmp_path / "f129-test-result.json"

    first_records, first_manifest = _load_or_generate_shards([root], basis, compiled, output)
    second_records, second_manifest = _load_or_generate_shards([root], basis, compiled, output)

    assert first_manifest["shards"][0]["reused"] is False
    assert second_manifest["shards"][0]["reused"] is True
    assert first_manifest["total_child_states_evaluated"] == len(legal_actions(state, compiled))
    assert second_records == first_records
    assert first_records[0]["direct_value"] == root["direct_oracle"]
    assert first_records[0]["root_legal_action_count"] == len(legal_actions(state, compiled))
    assert first_records[0]["action_spectrum_sha256"]
