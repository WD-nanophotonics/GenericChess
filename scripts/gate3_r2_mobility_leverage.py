"""Gate 3 R2: measure local leverage of the mobility coefficient."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.gate3_r1_rule_prior_contrast_leverage import (
    ROOT,
    _gen0,
    _load_root_digests,
    _replay_root,
    _replay_target_root,
    _search,
)


GEN0_CHECKPOINT_ID = "0d71bf4f9385820bf30fc905a65c6456d70ad7c4c4f90c3809729853eaa38c1d"
PRIMARY_MOBILITY = (1, 3)
WIDE_MOBILITY = (0, 4)


def _child_checkpoint(gen0, mobility: int):
    dynamic = dict(gen0.dynamic_weights)
    dynamic["mobility"] = mobility
    return replace(
        gen0,
        generation=1,
        parent_checkpoint_id=gen0.checkpoint_id,
        created_at="1970-01-01T00:00:00Z",
        training_config_hash=f"gate3-r2-mobility-{mobility}",
        dynamic_weights=dynamic,
    )


def _record(root_digest, mobility, decision, changed_from_gen0):
    return {
        "root_digest": root_digest,
        "mobility": mobility,
        "action_digest": decision["action_digest"],
        "score": decision["score"],
        "completed_depth": decision["completed_depth"],
        "nodes": decision["nodes"],
        "changed_from_gen0": changed_from_gen0,
    }


def run_gate3_r2(root: Path = ROOT):
    root_digests = _load_root_digests(root)
    roots = []
    for digest in root_digests:
        compiled, state, witnesses, _replay = (
            _replay_target_root(root) if digest == root_digests[0] else _replay_root(root, digest)
        )
        roots.append({"digest": digest, "compiled": compiled, "state": state, "witnesses": witnesses})

    config, profile, gen0 = _gen0(roots[0]["compiled"])
    if gen0.checkpoint_id != GEN0_CHECKPOINT_ID:
        return {
            "status": "GATE3_R2_GEN0_IDENTITY_DRIFT",
            "classification": "GATE3_R2_GEN0_IDENTITY_DRIFT",
            "gen0_checkpoint_id": gen0.checkpoint_id,
            "expected_gen0_checkpoint_id": GEN0_CHECKPOINT_ID,
            "searches": [],
        }

    checkpoints = {mobility: _child_checkpoint(gen0, mobility) for mobility in PRIMARY_MOBILITY + WIDE_MOBILITY}
    gen0_rows = []
    gen0_by_root = {}
    for row in roots:
        decision = _search(row["compiled"], row["state"], row["witnesses"], config, profile, gen0)
        gen0_by_root[row["digest"]] = decision
        gen0_rows.append(_record(row["digest"], 2, decision, False))

    mutant_rows = []

    def run_mutations(mutations):
        for mobility in mutations:
            checkpoint = checkpoints[mobility]
            for row in roots:
                decision = _search(row["compiled"], row["state"], row["witnesses"], config, profile, checkpoint)
                changed = decision["action_digest"] != gen0_by_root[row["digest"]]["action_digest"]
                mutant_rows.append(_record(row["digest"], mobility, decision, changed))

    run_mutations(PRIMARY_MOBILITY)
    primary_changed = [row for row in mutant_rows if row["mobility"] in PRIMARY_MOBILITY and row["changed_from_gen0"]]
    tested = list(PRIMARY_MOBILITY)
    if not primary_changed:
        run_mutations(WIDE_MOBILITY)
        tested.extend(WIDE_MOBILITY)
    changed = [row for row in mutant_rows if row["changed_from_gen0"]]
    if primary_changed:
        classification = "GATE3_MOBILITY_HAS_LOCAL_LEVERAGE"
        smallest_step = 1
    elif changed:
        classification = "GATE3_MOBILITY_HAS_LOCAL_LEVERAGE"
        smallest_step = 2
    else:
        classification = "GATE3_MOBILITY_NO_LOCAL_LEVERAGE"
        smallest_step = None
    return {
        "status": "PASS",
        "classification": classification,
        "gen0_checkpoint_id": gen0.checkpoint_id,
        "root_digests": list(root_digests),
        "mobility_values_tested": tested,
        "smallest_mobility_step": smallest_step,
        "searches": gen0_rows + mutant_rows,
        "compute": {"search_count": len(gen0_rows) + len(mutant_rows), "max_nodes": 1000},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_gate3_r2()
    if args.output:
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: result.get(key) for key in ("status", "classification", "mobility_values_tested", "smallest_mobility_step", "compute")}, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
