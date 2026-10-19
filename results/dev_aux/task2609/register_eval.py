"""Register corrected evaluation-only use of frozen task2606 models."""
from pathlib import Path
import datetime, hashlib, json

D = Path("results/dev_aux/task2609")
assert not any((D / n).exists() for n in ("eval-plan.json", "root-manifest.json", "registration.json", "eval-started.json"))
rows = json.loads(Path("results/dev_aux/task2607/root-candidates.json").read_text(encoding="utf-8"))
root_result_path = Path("results/dev_aux/task2607/result.json")
root_result = json.loads(root_result_path.read_text(encoding="utf-8"))
prefix_plies = json.loads(Path("results/dev_aux/task2607/plan.json").read_text(encoding="utf-8"))["prefix_plies"]
train_path = Path("results/dev_aux/task2606/result.json")
train = json.loads(train_path.read_text(encoding="utf-8"))
assert root_result["status"] == "PASS" and prefix_plies == 4
assert train["status"] == "COMPLETE" and len(train["arms"]) == 32

selected, roots = {}, {}
for rule in (271001, 271002, 271003, 271004):
    accepted = [row for row in rows if row["rule"] == rule and row["reason"] == "ACCEPT_FIRST_16"]
    assert len(accepted) == 16 and all(len(row["record"]["actions"]) == prefix_plies for row in accepted)
    selected[rule] = [row["family"] for row in accepted]
    roots.update({f"{rule}:{row['family']}": row["record"] for row in accepted})
(D / "root-manifest.json").write_text(json.dumps({
    "state": "FROZEN_BEFORE_EVALUATION",
    "identity": "Exact complete GameSession record with ruleset fingerprint and complete action history.",
    "prefix_plies": prefix_plies,
    "task2607_result_sha256": hashlib.sha256(root_result_path.read_bytes()).hexdigest(),
    "roots": roots,
    "selected_families": selected,
}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
slots = [[rule, seed, family, color, endpoint, "uniform"]
         for rule in selected for seed in (1977, 8173, 27182, 31415)
         for family in selected[rule] for color in (0, 1)
         for endpoint in ("initial", "TD95", "LocalLambda")]
assert len(slots) == 1536

pin_paths = [
    "results/dev_aux/task2606/train.py", "results/dev_aux/task2606/result.json",
    "results/dev_aux/task2607/plan.json", "results/dev_aux/task2607/registration.json",
    "results/dev_aux/task2607/result.json", "results/dev_aux/task2607/root-candidates.json",
    "results/dev_aux/task2608/eval-plan.json", "results/dev_aux/task2608/registration.json",
    "results/dev_aux/task2608/run_eval.py", "results/dev_aux/task2608/attempt-1-failure.json",
    "results/dev_aux/task2609/register_eval.py", "results/dev_aux/task2609/run_eval.py",
]
pin_paths += [f"results/dev_aux/task2525/rules-{rule}.json" for rule in selected]
pins = {path: hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in pin_paths}
plan = {
    "state": "REGISTERED_BEFORE_EVALUATION", "task": "DEV_AUX2609",
    "purpose": "Evaluation-only repair of task2608's zero-row runner failure, reusing its frozen models and outcome-blind exact-root-disjoint panel.",
    "question": "Do frozen task2606 TD95 and LocalLambda endpoints retain finite-panel outcomes on exact start histories disjoint from all 512 potential task2606 training-family roots?",
    "model_source": "Frozen task2606/result.json; all 32 models and initial weights fixed.",
    "models_sha256": hashlib.sha256(train_path.read_bytes()).hexdigest(),
    "rules": [271001, 271002, 271003, 271004], "seeds": [1977, 8173, 27182, 31415],
    "endpoints": ["initial", "TD95", "LocalLambda"], "foes": {"uniform": [1.0] * 6},
    "depth": 2, "H": 128, "nodes_per_query": 8192, "seconds_per_query": 2,
    "cap_seconds": 1200, "expected_duration_minutes": 10, "prefix_plies": prefix_plies,
    "slots": slots,
    "root_manifest_sha256": hashlib.sha256((D / "root-manifest.json").read_bytes()).hexdigest(),
    "selection": "Ascending family IDs, first16 ACCEPT_FIRST_16 per rule; selected without outcome access. Complete start records are disjoint from every 512 potential 4-ply training-family root. Descendant-state/generalization holdout is not claimed.",
    "repair_provenance": "task2608 failed before the first game/query because eval-plan omitted prefix_plies; its registration and zero-row artifacts are retained unchanged.",
}
(D / "eval-plan.json").write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
registration = {
    "state": "REGISTERED_BEFORE_EVALUATION",
    "registered_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "task": "DEV_AUX2609", "model_result_sha256": plan["models_sha256"],
    "root_manifest_sha256": plan["root_manifest_sha256"],
    "eval_plan_sha256": hashlib.sha256((D / "eval-plan.json").read_bytes()).hexdigest(),
    "source_pins": pins, "expected_slots": len(slots), "hard_cap_seconds": 1200,
    "training_or_fitness_started": False,
}
(D / "registration.json").write_text(json.dumps(registration, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"registered": True, "slots": len(slots), "roots": len(roots), "prefix_plies": prefix_plies, "expected_minutes": 10, "cap_seconds": 1200, "registration_sha256": hashlib.sha256((D / "registration.json").read_bytes()).hexdigest()}))
