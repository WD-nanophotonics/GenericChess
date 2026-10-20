"""Task2616 additive implementation registration. Conditions/caps stay frozen."""
from pathlib import Path
import datetime, hashlib, json, shutil

D = Path(__file__).resolve().parent
ROOT = Path.cwd()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    plan_path, eval_path, reg_path = D / "plan.json", D / "eval-plan.json", D / "registration.json"
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    if reg.get("status") != "REGISTERED_PRE_RUN" or (D / "tree-started.json").exists() or (D / "eval-started.json").exists():
        raise RuntimeError("cannot amend a started or unregistered task")
    attempt = D / "attempt-5"
    attempt.mkdir(exist_ok=False)
    for name, path in (("plan.json", plan_path), ("eval-plan.json", eval_path), ("registration.json", reg_path)):
        shutil.copy2(path, attempt / ("pre-runtime-" + name))
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    ev = json.loads(eval_path.read_text(encoding="utf-8"))
    # The reused evaluator requires the same schema as task2568; only representational
    # fields are amended. Frozen endpoints, slots, roots, search limits and caps remain.
    ev["foes"] = {"uniform": plan["conditions"]["training"]["fixed_foe"]}
    ev["cap_seconds"] = ev["global_cap_seconds"]
    ev["ordering_seed_offset"] = 972568000
    eval_path.write_text(json.dumps(ev, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    runtime_files = [
        "results/dev_aux/task2616/train_tree.py",
        "results/dev_aux/task2616/assemble.py",
        "results/dev_aux/task2568/evaluate.py",
        "results/dev_aux/task2492/learning.py",
        "results/dev_aux/task2492/adapters.py",
        "results/dev_aux/task2504/search.py",
        "results/dev_aux/task2565/train.py",
        "results/dev_aux/task2392/reader.py",
        "results/dev_aux/task2153/stop_evidence.py",
        "results/dev_aux/task109/adapter.py",
        "results/dev_aux/task2568/result.json",
    ]
    pins = {name: sha(ROOT / name) for name in runtime_files}
    old_sha = reg["plan_sha256"]
    old_eval_sha = reg["eval_plan_sha256"]
    plan["runtime_pins"] = pins
    plan["sources"]["eval_plan_sha256"] = sha(eval_path)
    plan["sources"]["runtime_registration_script_sha256"] = sha(Path(__file__))
    plan["amendment"] = {
        "version": 2,
        "supersedes_plan_sha256": old_sha,
        "supersedes_eval_plan_sha256": old_eval_sha,
        "reason": "Add exact executable/runtime source pins and adapt the reused evaluator's foe/cap/order fields without changing endpoints, slots, roots, seeds, searches, nodes or hard caps. No run started.",
        "at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    reg.update({
        "amendment": plan["amendment"],
        "plan_sha256": sha(plan_path),
        "eval_plan_sha256": sha(eval_path),
        "status": "REGISTERED_PRE_RUN",
        "no_training_yet": True,
        "no_evaluation_yet": True,
    })
    (D / "runner-registration.json").write_text(json.dumps({
        "task": "DEV_AUX2616", "status": "READY_PRE_RUN",
        "runtime_pins": pins,
        "plan_sha256": sha(plan_path), "eval_plan_sha256": sha(eval_path),
        "prior_plan_sha256": old_sha,
        "prior_eval_plan_sha256": old_eval_sha,
        "no_training_yet": True, "no_evaluation_yet": True,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    reg["runner_registration_sha256"] = sha(D / "runner-registration.json")
    reg_path.write_text(json.dumps(reg, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "status": "AMENDED_PRE_RUN", "old_plan_sha256": old_sha,
        "new_plan_sha256": sha(plan_path), "old_eval_plan_sha256": old_eval_sha,
        "new_eval_plan_sha256": sha(eval_path), "runtime_pins": pins,
        "conditions_changed": False,
    }
    (attempt / "amendment.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary

if __name__ == "__main__": print(json.dumps(main(), indent=2))
