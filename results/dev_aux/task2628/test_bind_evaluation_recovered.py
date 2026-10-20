"""The evaluation arm grid is derived from, not hardcoded beside, the plan."""
from __future__ import annotations

import json
from pathlib import Path

from results.dev_aux.task2628.bind_evaluation_recovered import expected_arm_keys

ROOT = Path(__file__).resolve().parents[3]


def test_expected_arm_keys_match_frozen_rules_and_seeds():
    plan = json.loads((ROOT / "results/dev_aux/task2628/run/plan.json").read_text(encoding="utf-8"))
    assert expected_arm_keys(plan) == {(15, 1977), (15, 8173), (15, 27182), (15, 31415)}
