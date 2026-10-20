"""Run the existing capped TDLeaf feasibility harness on the audited rule-1 pool."""
from __future__ import annotations

import hashlib
from pathlib import Path

from results.dev_aux.task2626 import trajectory_feasibility as runner

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "results/dev_aux/task2626/rule1-trajectory-feasibility"
SOURCE_REL = "results/dev_aux/task2626/trajectory_feasibility_rule1.py"
BASE_REL = "results/dev_aux/task2626/trajectory_feasibility.py"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def promoted_p_to_r(position) -> int:
    return sum(
        1 for piece in position.board
        if piece is not None
        and piece.base_type_id == "P"
        and piece.current_type_id == "R"
    )


runner.OUT = OUT
runner.POOL = ROOT / "results/dev_aux/task2626/rule1-root-pools.json"
runner.AUDIT = ROOT / "results/dev_aux/task2626/rule1-root-pools-audit-v2.json"
runner.RULE = "results/dev_aux/task2433/rules-1.json"
runner.promoted_count = promoted_p_to_r

original_write = runner.write


def write_with_source_pins(path: Path, value: dict) -> None:
    if path.name == "registration.json":
        value["source_sha256"][SOURCE_REL] = sha(Path(__file__).read_bytes())
        value["source_sha256"][BASE_REL] = sha(Path(runner.__file__).read_bytes())
    original_write(path, value)


runner.write = write_with_source_pins

if __name__ == "__main__":
    runner.main()
