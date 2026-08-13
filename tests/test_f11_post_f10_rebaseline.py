"""F11 H11A evidence contract tests."""

from __future__ import annotations

import json
from pathlib import Path


ART = Path(__file__).resolve().parents[1] / "artifacts" / "f11_post_f10_rebaseline"


def read(name):
    return json.loads((ART / name).read_text(encoding="utf-8"))


def test_f11_baseline_and_fingerprint_are_locked():
    baseline = read("baseline.json")
    corpus = read("corpus.json")
    assert baseline["origin/sandbox"] == "83b921a07277ca7186f66a65ecc95fb040838a34"
    assert baseline["origin/master"] == "4f1d03a308f5fd04a01bbd980c7411888ea1ed9d"
    assert baseline["origin/chat"] == "d6b0d5720efe23019a7a2b4cce72e05beee2e6c4"
    assert corpus["certified_fingerprint"] == "5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345"


def test_f11_h11a_is_single_winner_audit_only():
    decision = read("single_winner_decision.json")
    matrix = read("candidate_matrix.json")
    assert decision["selected"] is None
    assert decision["H11B_CREATED"] is False
    assert decision["status"] == "NO_CLEAR_SINGLE_WINNER"
    assert any(row["status"] == "FORBIDDEN" for row in matrix)


def test_f11_profiles_cover_the_certified_corpus():
    for profile in ("a", "b"):
        rows = (ART / f"whole_search_profile_{profile}.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(rows) == 30
        assert {json.loads(row)["case_id"] for row in rows} == {
            "legacy_draw_root",
            "continuous_check_prefix",
            "semantic_prefix_0",
            "semantic_prefix_1",
            "semantic_prefix_2",
            "semantic_prefix_3",
        }
