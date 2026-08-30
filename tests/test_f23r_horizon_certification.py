"""F23R contracts for MAX_PLY abstraction and frozen V10 certification."""

from __future__ import annotations

import hashlib
import itertools
import json

from scripts.exact_generic_horizon_abstraction import (
    UNKNOWN,
    concrete_tree_value,
    tree_threshold,
)


ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
V10 = FIXTURES / "evaluator_v2_corpus_v10.json"
F23R = FIXTURES / "f23r_v10_horizon_certification.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _unknown_ids(node):
    if node[0] == "leaf":
        return {node[1]} if node[1] == UNKNOWN or isinstance(node[1], str) else set()
    return set().union(*(_unknown_ids(child) for child in node[2]))


def test_three_valued_tree_oracle_is_sound_for_every_unknown_assignment():
    trees = [
        ("node", True, [("leaf", UNKNOWN), ("leaf", 1)]),
        ("node", False, [("leaf", UNKNOWN), ("leaf", -1)]),
        ("node", True, [("leaf", UNKNOWN), ("leaf", -1)]),
        ("node", False, [("leaf", UNKNOWN), ("leaf", 1)]),
        (
            "node",
            True,
            [
                ("node", False, [("leaf", UNKNOWN), ("leaf", 0)]),
                ("leaf", -1),
            ],
        ),
    ]
    for tree in trees:
        unknown_ids = sorted(_unknown_ids(tree))
        assignments = [
            dict(zip(unknown_ids, values))
            for values in itertools.product((-1, 0, 1), repeat=len(unknown_ids))
        ]
        for threshold in (-1, 0, 1):
            abstract = tree_threshold(tree, threshold)
            concrete = [concrete_tree_value(tree, assignment) >= threshold for assignment in assignments]
            if abstract is True:
                assert all(concrete)
            elif abstract is False:
                assert not any(concrete)
            else:
                # Unknown is deliberately conservative; it may remain unknown
                # even when a particular threshold makes all assignments agree.
                assert concrete


def test_tree_oracle_short_circuits_known_winning_and_losing_branches():
    assert tree_threshold(("node", True, [("leaf", 1), ("leaf", UNKNOWN)]), 1) is True
    assert tree_threshold(("node", False, [("leaf", -1), ("leaf", UNKNOWN)]), 0) is False


def test_f23r_fixture_certifies_the_frozen_v10_set_without_contradiction():
    v10 = load(V10)
    f23r = load(F23R)
    effective = v10["effective_preference_representatives"]
    assert f23r["source_v10_fixture_sha256"] == hashlib.sha256(V10.read_bytes()).hexdigest()
    assert f23r["source_effective_count"] == 42
    assert set(f23r["certifications"]) == {row["id"] for row in effective}
    assert all(not row["abstract_base_contradiction"] for row in f23r["certifications"].values())
    assert f23r["summary"] == {
        "abstract_base_contradictions": 0,
        "computational_unknown": 1,
        "development": 32,
        "development_horizon_quality": 0,
        "holdout": 10,
        "horizon_stable_exact": 0,
        "materially_dependent": 0,
        "max_ply_abstract_certified": 0,
        "semantic_unknown": 41,
        "unknown": 42,
    }
    assert f23r["gate"]["passes"] is False
    assert f23r["selected_next_boundary"] == "F23S_NATURAL_TERMINAL_REFERENCE_CORPUS_R9"
    assert f23r["production_changed"] is False
    assert f23r["v10_rewritten"] is False
