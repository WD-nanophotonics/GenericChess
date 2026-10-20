"""Regressions for the supplemental plan-derived task2628 analysis."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path

from results.dev_aux.task2628.analyze_corrected import bounds, expected_pairs

ROOT = Path(__file__).resolve().parents[3]


def test_frozen_plan_implies_128_pairs_and_256_endpoint_slots():
    plan = json.loads((ROOT / "results/dev_aux/task2628/run/plan.json").read_text(encoding="utf-8"))
    pool = json.loads((ROOT / "results/dev_aux/task2627/rule15-successor-root-pools.json").read_text(encoding="utf-8"))
    pairs = expected_pairs(plan, pool)
    assert len(pairs) == 128
    assert len(pairs) * 2 == plan["evaluation"]["slots"] == 256


def test_unknown_completion_bounds_keep_draw_distinct():
    assert bounds(None, None) == (-2, 2)
    assert bounds(None, 0) == (-1, 1)
    assert bounds(1, 0) == (1, 1)


def test_registered_analyzer_source_remains_pinned_unchanged():
    run = ROOT / "results/dev_aux/task2628/run"
    reg = json.loads((run / "registration.json").read_text(encoding="utf-8"))
    source = ROOT / "results/dev_aux/task2628/analyze.py"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    assert digest == reg["source_pins"]["results/dev_aux/task2628/analyze.py"]
