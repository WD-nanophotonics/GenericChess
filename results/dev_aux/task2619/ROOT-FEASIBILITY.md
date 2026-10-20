# DEV_AUX task2619 — prospective Chess root-pool feasibility

**Status: outcome-blind root feasibility only.** No learner/search was run and
no model/outcome was selected. The root lists are prospective inputs for a
possible task2618 registration, not a registration or holdout claim.

## Result

The deterministic generator produced all requested starts immediately:

- Training pool: 512 eight-ply full-history roots, generator seed `0`, family
  IDs 810001–810512.
- Evaluation pool: 32 eight-ply full-history roots, generator seed `0`, family
  IDs 910001–910032.
- Exact overlap between the two prospective pools: 0.
- Training/evaluation roots also had zero exact matches against the audited
  prior-root union: 7,451 rows / 250 unique registered Chess evaluation roots,
  4,040 rows / 292 unique observed Chess training roots, and all 5,000 possible
  task2616 training-pool roots reconstructed from its frozen task2568 recipe.

The identity is the canonical complete standard-Chess root record: initial FEN,
ordered eight-ply UCI history and resulting FEN. The generator and `ChessEnv`
sources are SHA-pinned in `root-feasibility.json`; roots themselves include
per-record hashes. `root_feasibility.py` scans registered Chess `eval-plan.json`
receipts and their initial records, Chess `plan.json` training traces, and the
complete task2616 family pool. It never uses post-root actions or outcome values
for selection.

## Limits and next gate

This is exact start-record disjointness from the sources enumerated above. It
does not establish descendant-state, semantic/transposition or distributional
independence, and does not reconstruct every unobserved possible training root
from older historical runners. The finite prospective roots remain development-
exposed once published. Any change to seed, family range, prefix generator,
runner or roots requires regeneration and re-audit before registration.

Before task2618 registration, bind these roots to the final paired arm/seed/color
cross product; verify every evaluation root remains disjoint from all training
starts; freeze the fixed foe, all-side paid-node caps, WDL proposal rule and
complete source hashes. Recompute the all-in cost from those exact sources.
The current feasibility estimate is below 120 minutes, so Dot review is not a
launch prerequisite unless the frozen design increases the expected duration
to 120 minutes or more. Preserve cap-bound missing and UNKNOWN slots.
