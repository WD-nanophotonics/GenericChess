"""Materialize the cheap, fail-closed F48 preflight checkpoint."""

from __future__ import annotations

from pathlib import Path

from f48_protocol import ROOT, atomic_write_json, preflight


OUT = ROOT / "tests" / "fixtures" / "f48_preflight_plan.json"


def main() -> None:
    plan = preflight()
    atomic_write_json(OUT, plan)
    print(f"F48_PREFLIGHT_PASS partitions={len(plan['partitions'])} output={OUT}")


if __name__ == "__main__":
    main()

