"""Assemble frozen task2568 controls and the task2616 TreeStrap endpoint."""
from pathlib import Path
import hashlib, json

TASK = Path(__file__).resolve().parent
ROOT = Path.cwd()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def run(directory=None):
    d = TASK if directory is None else Path(directory)
    plan = json.loads((d / "plan.json").read_text(encoding="utf-8"))
    reg = json.loads((d / "registration.json").read_text(encoding="utf-8"))
    tree = json.loads((d / "tree-training-result.json").read_text(encoding="utf-8"))
    frozen_path = ROOT / "results/dev_aux/task2568/result.json"
    if sha(d / "plan.json") != reg["plan_sha256"]:
        raise RuntimeError("registered plan hash mismatch")
    if sha(frozen_path) != plan["sources"]["task2568_result_sha256"]:
        raise RuntimeError("frozen TD/WDL result source changed")
    if (d / "result.json").exists():
        raise FileExistsError("refusing to replace assembled endpoint evidence")
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    controls = [arm for arm in frozen["arms"] if arm["method"] in ("TD", "WDL")]
    if len(controls) != 8:
        raise AssertionError("expected all four frozen TD and WDL endpoints")
    td = {a["seed"]: a for a in controls if a["method"] == "TD"}
    wdl = {a["seed"]: a for a in controls if a["method"] == "WDL"}
    if set(td) != set(plan["conditions"]["seeds"]) or set(wdl) != set(td):
        raise AssertionError("frozen TD/WDL seeds differ from registration")
    if any(td[s]["initial"] != wdl[s]["initial"] for s in td):
        raise AssertionError("frozen TD/WDL initial vectors differ")
    if any(a["initial"] != td[a["seed"]]["initial"] for a in tree["arms"]):
        raise AssertionError("TreeStrap initialization differs from its paired frozen control")
    if tree["status"] not in ("COMPLETE", "PARTIAL_CAP"):
        raise AssertionError("unexpected TreeStrap result status")
    if len({arm["seed"] for arm in tree["arms"]}) != len(tree["arms"]):
        raise AssertionError("duplicate TreeStrap seed")
    out = {
        "status": tree["status"], "expected_arms": 12,
        "arms": controls + tree["arms"],
        "sources": {
            "frozen_task2568_result_sha256": sha(frozen_path),
            "tree_training_result_sha256": sha(d / "tree-training-result.json"),
            "plan_sha256": sha(d / "plan.json"),
        },
        "scope": "Frozen TD/WDL and initial controls plus new TreeStrap models; no model selected by training outcome.",
    }
    (d / "result.json").write_text(json.dumps(out, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    binding = {
        "task": "DEV_AUX2616", "assembled_result_sha256": sha(d / "result.json"),
        "tree_training_result_sha256": sha(d / "tree-training-result.json"),
        "frozen_task2568_result_sha256": sha(frozen_path),
        "plan_sha256": sha(d / "plan.json"), "eval_plan_sha256": sha(d / "eval-plan.json"),
    }
    (d / "model-binding.json").write_text(json.dumps(binding, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out

if __name__ == "__main__": print(json.dumps(run(), indent=2, allow_nan=False))
