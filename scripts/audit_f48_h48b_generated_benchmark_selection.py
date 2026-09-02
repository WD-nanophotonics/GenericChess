"""Run the frozen H48B generated-benchmark screen and write its checkpoint."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from generic_chess.ai.benchmark.audit_suite import build_compiled, standard_ruleset_specs
from generic_chess.learning.leverage import (
    BRANCHING_MAX_FORCED_MOVE_FRACTION,
    BRANCHING_MIN_MEAN_LEGAL_ACTIONS,
    CANDIDATE_COUNT,
    CANDIDATE_CORPUS_COUNT,
    CANDIDATE_LEVERAGE_BUDGET,
    CANDIDATE_MASTER_SEED,
    CANDIDATE_OPENING_COUNT,
    CANDIDATE_PRESETS,
    CANDIDATE_TACTICAL_DEEP,
    CANDIDATE_TACTICAL_SHALLOW,
    FIRST_PLAYER_MAX_OWNER0_WIN_RATE,
    FIRST_PLAYER_MIN_OWNER1_WIN_RATE,
    LEVERAGE_MIN,
    TACTICAL_AGREEMENT_MAX,
    TACTICAL_AGREEMENT_MIN,
    VIABILITY_MAX_AVG_PLIES,
    VIABILITY_MAX_ENDLESS_DRAW_FRACTION,
    VIABILITY_MIN_AVG_PLIES,
    candidate_specs,
    screen_candidates,
    select_benchmarks,
)
from generic_chess.learning.serialization import canonical_json


ROOT = Path(__file__).resolve().parents[1]
BASELINE_SHA = "d02212e85e9e0b50a946ec74b21e45a315dcb6d8"
H48R2A_MANIFEST_SHA = "9db3a74f5e942e0c4bd89c99d8e275e1b1ce5273ce39dac5de0679d7e3dcdbb9"
SCREEN_REF = "a695fd6e89fb771952e208e562858710ae1e0b3d"
OUTPUT = ROOT / "tests" / "fixtures" / "h48b_generated_benchmark_selection.json"
EXECUTION_DEPENDENCIES = (
    "generic_chess/learning/leverage.py",
    "generic_chess/learning/diagnostics.py",
    "generic_chess/learning/material.py",
    "generic_chess/learning/features.py",
    "generic_chess/learning/arena.py",
    "generic_chess/learning/openings.py",
    "generic_chess/learning/serialization.py",
    "generic_chess/core/identity.py",
    "generic_chess/session/session.py",
    "generic_chess/generation/config.py",
    "generic_chess/generation/generator.py",
    "generic_chess/native/compiler.py",
    "generic_chess/native/engine.py",
    "generic_chess/ai/evaluation/config.py",
    "generic_chess/ai/evaluation/profile.py",
    "generic_chess/ai/benchmark/audit_suite.py",
)


def _raw_blob_sha256(ref: str, path: str) -> str:
    raw = subprocess.run(
        ["git", "cat-file", "blob", f"{ref}:{path}"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout
    return hashlib.sha256(raw).hexdigest()


def _predicate_ledger(row: dict) -> dict:
    metrics = row.get("metrics") or {}
    checks = {
        "terminal_rate": metrics.get("terminal_rate") == 1.0,
        "average_plies": VIABILITY_MIN_AVG_PLIES <= metrics.get("average_plies", -1) <= VIABILITY_MAX_AVG_PLIES,
        "endless_draw_fraction": metrics.get("endless_draw_fraction", 1.0) <= VIABILITY_MAX_ENDLESS_DRAW_FRACTION,
        "owner0_win_rate": metrics.get("owner0_win_rate", 1.0) <= FIRST_PLAYER_MAX_OWNER0_WIN_RATE,
        "owner1_win_rate": metrics.get("owner1_win_rate", -1.0) >= FIRST_PLAYER_MIN_OWNER1_WIN_RATE,
        "tactical_shallow_deep_agreement": metrics.get("tactical_shallow_deep_agreement") is not None and TACTICAL_AGREEMENT_MIN <= metrics["tactical_shallow_deep_agreement"] <= TACTICAL_AGREEMENT_MAX,
        "evaluation_leverage": metrics.get("eval_leverage") is not None and metrics["eval_leverage"] >= LEVERAGE_MIN,
        "forced_move_fraction": metrics.get("forced_move_fraction", 1.0) <= BRANCHING_MAX_FORCED_MOVE_FRACTION,
        "mean_legal_actions": metrics.get("mean_legal_actions", 0.0) >= BRANCHING_MIN_MEAN_LEGAL_ACTIONS,
    }
    return {"predicates": checks, "eligible": all(checks.values())}


def _r2_fingerprint() -> str:
    spec = next(s for s in standard_ruleset_specs() if s.fixture_id == "gen_free_random_4_102")
    return build_compiled(spec).ruleset_fingerprint


def main() -> int:
    specs = candidate_specs(CANDIDATE_COUNT)
    assert len(specs) == 32
    assert [s["seed"] for s in specs] == [CANDIDATE_MASTER_SEED * 1000 + i for i in range(CANDIDATE_COUNT)]
    assert [s["setup_preset"] for s in specs] == [CANDIDATE_PRESETS[i % len(CANDIDATE_PRESETS)] for i in range(CANDIDATE_COUNT)]

    summaries = screen_candidates(ROOT / ".generic_chess_flow" / "h48b-screening", CANDIDATE_COUNT)
    if len(summaries) != CANDIDATE_COUNT:
        raise RuntimeError(f"expected {CANDIDATE_COUNT} candidate rows, got {len(summaries)}")
    rows = []
    for row in summaries:
        predicate = _predicate_ledger(row)
        row = dict(row)
        row["predicate_ledger"] = predicate
        row["learned_checkpoint_input"] = False
        rows.append(row)

    selector = select_benchmarks(summaries, _r2_fingerprint())
    eligible = [row for row in rows if row["predicate_ledger"]["eligible"]]
    direct = sorted(
        eligible,
        key=lambda row: (
            -float(row["metrics"]["eval_leverage"]),
            float(row["metrics"]["owner0_win_rate"]),
            row["ruleset_fingerprint"],
        ),
    )
    if not direct:
        raise RuntimeError("H48B_NO_ELIGIBLE_GENERATED_BENCHMARK")
    selected = selector.get("evaluation_sensitive")
    if selected is None:
        raise RuntimeError("bound selector returned no evaluation-sensitive candidate")
    direct_selected = {
        "index": direct[0]["index"],
        "seed": direct[0]["seed"],
        "setup_preset": direct[0]["setup_preset"],
        "ruleset_fingerprint": direct[0]["ruleset_fingerprint"],
    }
    selector_selected = {
        "index": selected["index"],
        "seed": selected["seed"],
        "setup_preset": next(row["setup_preset"] for row in rows if row["index"] == selected["index"]),
        "ruleset_fingerprint": selected["ruleset_fingerprint"],
    }
    if selector_selected != direct_selected:
        raise RuntimeError(f"H48B selection disagreement: {selector_selected} != {direct_selected}")

    historical = {
        "historical_phase17_index": 9,
        "historical_fingerprint_prefix": "9f7e7201",
        "selected_index_matches": direct_selected["index"] == 9,
        "selected_fingerprint_matches_prefix": direct_selected["ruleset_fingerprint"].startswith("9f7e7201"),
        "role": "diagnostic_only_after_new_selection",
    }
    payload = {
        "kind": "H48B_GENERATED_EVALUATION_SENSITIVE_BENCHMARK_SELECTION",
        "protocol": "H48R2A",
        "parent_h48r2a_sha": BASELINE_SHA,
        "h48r2a_manifest_sha256": H48R2A_MANIFEST_SHA,
        "selection_completed_before_learning": True,
        "learned_checkpoint_input": False,
        "screening_constants": {
            "candidate_count": CANDIDATE_COUNT,
            "candidate_master_seed": CANDIDATE_MASTER_SEED,
            "candidate_board_size": 6,
            "candidate_presets": list(CANDIDATE_PRESETS),
            "candidate_opening_count": CANDIDATE_OPENING_COUNT,
            "candidate_arena_pairs": 2,
            "candidate_arena_nodes": 800,
            "candidate_arena_max_depth": 12,
            "candidate_corpus_count": CANDIDATE_CORPUS_COUNT,
            "candidate_corpus_seed": 42,
            "candidate_corpus_max_plies": 40,
            "candidate_leverage_budget": CANDIDATE_LEVERAGE_BUDGET,
            "candidate_leverage_factors": [0.75, 1.25],
            "candidate_tactical_shallow": CANDIDATE_TACTICAL_SHALLOW,
            "candidate_tactical_deep": CANDIDATE_TACTICAL_DEEP,
            "eligibility": {
                "terminal_rate": "== 1.0",
                "average_plies": "[4,200] inclusive",
                "endless_draw_fraction": "<= 0.5",
                "owner0_win_rate": "<= 0.90",
                "owner1_win_rate": ">= 0.05",
                "tactical_shallow_deep_agreement": "[0.30,0.98] inclusive",
                "evaluation_leverage": ">= 0.10",
                "forced_move_fraction": "<= 0.30",
                "mean_legal_actions": ">= 2.0",
            },
        },
        "execution_dependency_blobs": [
            {"ref": BASELINE_SHA, "path": path, "sha256": _raw_blob_sha256(BASELINE_SHA, path)}
            for path in EXECUTION_DEPENDENCIES
        ],
        "screening_implementation_authority": {
            "ref": SCREEN_REF,
            "paths": [
                {"path": "generic_chess/learning/leverage.py", "raw_blob_sha256": _raw_blob_sha256(SCREEN_REF, "generic_chess/learning/leverage.py")},
                {"path": "tests/test_learning_leverage.py", "raw_blob_sha256": _raw_blob_sha256(SCREEN_REF, "tests/test_learning_leverage.py")},
                {"path": "docs/learning_phase1_7_evaluation_leverage.md", "raw_blob_sha256": _raw_blob_sha256(SCREEN_REF, "docs/learning_phase1_7_evaluation_leverage.md")},
                {"path": "pyproject.toml", "raw_blob_sha256": _raw_blob_sha256(SCREEN_REF, "pyproject.toml")},
            ],
        },
        "candidates": rows,
        "eligible_set": [row["index"] for row in eligible],
        "selection": {
            "bound_selector": selector_selected,
            "direct_sort": direct_selected,
            "independent_selection_agree": True,
            "selected": direct_selected,
        },
        "historical_phase17_comparison": historical,
    }
    OUTPUT.write_text(canonical_json(payload) + "\n", encoding="utf-8")
    print(canonical_json({"selected": direct_selected, "eligible_set": payload["eligible_set"], "output": str(OUTPUT)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
