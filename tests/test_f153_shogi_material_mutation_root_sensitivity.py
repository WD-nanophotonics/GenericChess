from scripts import f144_shogi_material_only_arena_evolution as f144
from scripts import f153_shogi_material_mutation_root_sensitivity as probe


def test_contract_and_f144_sigma035_parity():
    assert probe.WORK_ORDER == "GENERICCHESS_F153_SHOGI_MATERIAL_MUTATION_ROOT_SENSITIVITY"
    assert probe.POSITION_LIMITS == (4, 8, 12)
    assert probe.SIGMAS == (0.35, 0.70, 1.40)
    gen0 = tuple(f144.gen0_vector(f144.GEN0_SEED))
    assert probe.mutation_vectors_at_sigma(gen0, 0.35) == tuple(f144.mutate_vectors(gen0, 1))


def test_leverage_classes_and_minimums():
    def row(position, changed):
        roots = [{"label": "Gen0", "action_differs_from_gen0": False}]
        roots.extend({"label": f"mutant_{i}", "action_differs_from_gen0": i in changed} for i in range(6))
        return {"position": {"opening_id": position}, "root_searches": roots}

    assert probe.leverage_summary([])["classification"] == "NO_LEVERAGE"
    assert probe.leverage_summary([row("a", {0})])["classification"] == "SPARSE_LEVERAGE"
    assert probe.leverage_summary([row("a", {0, 1}), row("b", {0})])["classification"] == "SUFFICIENT_LEVERAGE"


def test_fresh_probe_record_is_minimal():
    record = probe._record_probe({
        "best_action": {"kind": "move"},
        "best_action_key": "x",
        "score": 4,
        "completed_depth": 2,
        "nodes": 100,
        "qnodes": 7,
        "termination_reason": "node_limit",
    })
    assert set(record) == {"best_action", "best_action_key", "score", "completed_depth", "nodes", "qnodes"}


def test_artificial_extreme_vector_changes_known_root_and_is_deterministic():
    compiled = probe.race._compile()
    opening = probe.race.opening_corpus(compiled, probe.F151_SEED, 32)[0]
    ordering_values = f144._ordering_values(compiled)
    gen0 = tuple(f144.gen0_vector(f144.GEN0_SEED))
    first = probe._record_probe(probe.root_probe(compiled, opening, gen0, ordering_values))
    second = probe._record_probe(probe.root_probe(compiled, opening, gen0, ordering_values))
    extreme = probe._record_probe(
        probe.root_probe(compiled, opening, probe.artificial_extreme_vector(), ordering_values)
    )
    assert first == second
    assert first["best_action_key"] != extreme["best_action_key"]
