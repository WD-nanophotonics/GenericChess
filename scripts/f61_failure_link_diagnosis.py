"""Diagnose the completed F61 Standard-Shogi Gen0->Gen1 failure link.

This is an audit-only reconstruction of the frozen seed-59012 run.  It does
not fit a new model or run an Arena: it checks the persisted compact residual
on the 157 training-action vectors and invokes the existing equal-budget
search-validation primitive on the four frozen Arena openings.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.learning.nonlinear import CompactNonlinearResidual
from generic_chess.learning.openings import generate_arena_openings
from scripts import f59_action_spectrum_diagnosis as f59
from scripts import f61_gen0_gen1_strength_triage as gen
from scripts import f61_strength_first_triage as f61


OUT = ROOT / ".generic_chess_flow" / "f61-gen0-gen1-strength-triage" / "failure_link_diagnosis.json"
RULESET = "B_CANONICAL_STANDARD_SHOGI"
TRAINING_SEED = 59012
ARENA_SEED = 620700
ARENA_PAIRS = 4
ARENA_NODES = 2_000
ARENA_DEPTH = 12
TOLERANCE = 1e-9


def main() -> None:
    compiled, native, parent, _ = gen._context(RULESET)
    records = gen._d0_records(compiled, 620000, count=gen.ROOT_COUNT, smoke=False)
    child, training = gen._fit_one(compiled, native, parent, records, smoke=False)
    roots = []
    for record in records:
        spectrum = gen._load_root_checkpoint(compiled, parent, record, smoke=False)
        if spectrum is None:
            raise RuntimeError("missing persisted root checkpoint")
        usable = [row for row in spectrum if row.q_20k is not None]
        if len(usable) >= 2:
            roots.append(usable)
    features = np.vstack([row.features for root in roots for row in root])
    residual = CompactNonlinearResidual.from_dict(child.compact_nonlinear)
    values = residual.predict(features)
    openings = generate_arena_openings(
        compiled, count=ARENA_PAIRS, seed=ARENA_SEED, min_plies=2, max_plies=6
    )
    search = f61._search_validation(
        compiled, native, parent, child, openings, ARENA_NODES
    )
    payload = {
        "schema": "generic-chess-f61-failure-link-diagnosis-v1",
        "ruleset": RULESET,
        "training_seed": TRAINING_SEED,
        "parent_checkpoint_id": parent.checkpoint_id,
        "child_checkpoint_id": child.checkpoint_id,
        "compact_residual": {
            "attached_to_child": bool(child.compact_nonlinear),
            "input_dimension": len(residual.input_mean),
            "width": residual.width,
            "perspective": residual.perspective,
            "training_roots": len(roots),
            "training_actions": int(len(values)),
            "min": float(np.min(values)),
            "max": float(np.max(values)),
            "mean": float(np.mean(values)),
            "std": float(np.std(values)),
            "absolute_above_tolerance": int(np.count_nonzero(np.abs(values) > TOLERANCE)),
            "fraction_absolute_above_tolerance": float(np.mean(np.abs(values) > TOLERANCE)),
            "tolerance": TOLERANCE,
        },
        "search_validation": {
            "opening_seed": ARENA_SEED,
            "nodes": ARENA_NODES,
            "max_depth": ARENA_DEPTH,
            "tt_megabytes": 8,
            **search,
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
