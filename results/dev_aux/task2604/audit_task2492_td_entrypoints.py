from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "results/dev_aux/task2492"
FILES = ("run.py", "learning.py", "episode.py", "adapters.py")
OUTPUT = Path(__file__).with_name("entrypoints.json")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def top_level_classes(tree: ast.Module) -> set[str]:
    return {n.name for n in tree.body if isinstance(n, ast.ClassDef)}


def run_imports(tree: ast.Module) -> dict[str, str]:
    found: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.endswith(("learning", "episode", "adapters")):
                for alias in node.names:
                    found[alias.asname or alias.name] = f"{module}.{alias.name}"
    return found


def audit() -> dict:
    trees = {name: ast.parse((TASK / name).read_text(encoding="utf-8")) for name in FILES}
    defs = {name: sorted(top_level_classes(tree)) for name, tree in trees.items()}
    imports = run_imports(trees["run.py"])
    run_names = {n.id for n in ast.walk(trees["run.py"]) if isinstance(n, ast.Name)}
    learner_calls = sorted({
        f"{n.func.value.id}.{n.func.attr}"
        for n in ast.walk(trees["run.py"])
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and isinstance(n.func.value, ast.Name) and n.func.value.id == "learner"
    })
    return {
        "task_id": 2604,
        "status": "SOURCE_ONLY_ENTRYPOINT_AUDIT",
        "source_sha256": {name: digest(TASK / name) for name in FILES},
        "top_level_classes": defs,
        "run_learning_imports": imports,
        "run_references_tdleaf_episode": "TDLeafEpisode" in run_names or "episode" in imports,
        "run_learner_calls": learner_calls,
        "adapter_support": {
            "ChessEnv": "ChessEnv" in defs["adapters.py"],
            "SessionEnv": "SessionEnv" in defs["adapters.py"],
            "generic_tactical_qsearch": False,
        },
        "scope": "AST/source read only; no result, weight, query, game-record, or training execution read/performed.",
    }


if __name__ == "__main__":
    result = audit()
    if OUTPUT.exists():
        raise SystemExit(f"refusing to overwrite {OUTPUT.name}")
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "run_learning_imports": result["run_learning_imports"],
        "run_references_tdleaf_episode": result["run_references_tdleaf_episode"],
        "run_learner_calls": result["run_learner_calls"],
    }, sort_keys=True))
