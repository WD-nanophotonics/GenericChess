"""Regression for the frozen-plan consumer mismatch found before task2622 queries."""
from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "results/dev_aux/task2625/run"
PLAN_PATH = RUN / "plan.json"
if not PLAN_PATH.exists():
    # Before task2625 is frozen, validate the corrected consumer schema against
    # the prior plan's identical training/evaluation contract.
    PLAN_PATH = ROOT / "results/dev_aux/task2623/run/plan.json"


def _plan_path(node: ast.AST):
    if isinstance(node, ast.Name) and node.id == "plan":
        return []
    if isinstance(node, ast.Subscript):
        parent = _plan_path(node.value)
        key = node.slice.value if isinstance(node.slice, ast.Constant) else None
        if parent is not None and isinstance(key, str):
            return parent + [key]
    return None


def test_frozen_plan_has_every_literal_path_used_by_corrected_consumers():
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    consumers = (
        "train.py", "evaluate.py", "audit_training.py", "audit_evaluation.py",
        "bind_evaluation.py", "analyze.py",
    )
    missing = set()
    for name in consumers:
        tree = ast.parse((ROOT / "results/dev_aux/task2625" / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Subscript):
                continue
            path = _plan_path(node)
            if not path:
                continue
            value = plan
            for part in path:
                if not isinstance(value, dict) or part not in value:
                    missing.add(".".join(path))
                    break
                value = value[part]
    assert missing == set()


def test_future_train_preflight_rejects_missing_cap_with_clear_error():
    from results.dev_aux.task2625.train import validate_plan_contract

    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    invalid = json.loads(json.dumps(plan))
    del invalid["training"]["nodes_per_arm_candidate_plus_foe"]
    try:
        validate_plan_contract(invalid)
    except ValueError as exc:
        assert "nodes_per_arm_candidate_plus_foe" in str(exc)
    else:
        raise AssertionError("incomplete registered training cap was accepted")


def test_future_eval_preflight_checks_fixed_slot_and_family_cap_grid():
    from results.dev_aux.task2625.evaluate import validate_plan_contract

    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    validate_plan_contract(plan)
    invalid = json.loads(json.dumps(plan))
    invalid["evaluation"]["slots"] -= 1
    try:
        validate_plan_contract(invalid)
    except ValueError as exc:
        assert "slot count" in str(exc)
    else:
        raise AssertionError("invalid slot denominator was accepted")


def test_runner_plan_preflights_run_before_any_start_receipt_or_output_creation():
    for filename, guarded in (("train.py", "validate_inputs"), ("evaluate.py", "validate_plan_contract")):
        tree = ast.parse((ROOT / "results/dev_aux/task2625" / filename).read_text(encoding="utf-8"))
        run = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run")
        calls = [
            (node.lineno, node.func.id)
            for node in ast.walk(run)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        ]
        guard_lines = [line for line, name in calls if name == guarded]
        receipt_lines = [
            node.lineno for node in ast.walk(run)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "write_once"
            and any(token in (ast.get_source_segment((ROOT / "results/dev_aux/task2625" / filename).read_text(encoding="utf-8"), node) or "")
                    for token in ('"started.json"', '"eval-started.json"'))
        ]
        assert guard_lines and receipt_lines and min(guard_lines) < min(receipt_lines)
