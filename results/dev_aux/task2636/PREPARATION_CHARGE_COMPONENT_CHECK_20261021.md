# task2636 preparation-charge component check — 2026-10-21

The frozen root plan (`one-init-root-plan.json`) identifies the 542.632066s
preparation/audit charge as a planning allocation, not one elapsed-time
receipt. Its component fields reconstruct as follows:

| Component | Seconds | Evidence class |
|---|---:|---|
| Dynamic-history inventory | 227.9978056001 | Observed in the frozen plan |
| Exposed-prefix audit | 4.7624095000 | Observed; `prefix-audit-status.json` records the same elapsed value and complete status |
| Sixteen-rule root-pool preparation | 165.8718512002 | Projection: the plan scales the observed 41.4679628001s four-rule preparation by 4 |
| Full-source audit | 144 | Projection; no corresponding completed elapsed-time receipt was found |
| **Total allocation** | **542.6320663003** | **Mixed observed/projection budget charge** |

The arithmetic is `227.9978056001 + 4.7624095000 + 4×41.4679628001 + 144
= 542.6320663003s` (rounding to the plan's 542.6320663003s). The plan's
source-budget note explicitly says this charge is not measured elapsed
runtime. The 144s audit projection has no independently identified timing
receipt in the task2636 records; retain it as a conservative allocation rather
than relabeling it as measured.

Using the 2026-10-21 00:06:34Z session checkpoint, the mixed-cost arithmetic is
`3,313.414228 + 542.6320663 + 2,801.9875061 = 6,658.0338004s`, or 58.0338004s
above the unchanged 6,600s design cap. This is not an experiment-runtime cap
hit: the 3,313.414228s is confirmed Agent work, 542.6320663s is a mixed
allocation, and 2,801.9875061s is a training/evaluation projection. No task2636
registration or run-v1 exists. The four remaining integration/validation gates
remain unpriced, so this scenario cannot establish an all-in estimate or justify
registration. Preserve the frozen caps and no-run status.

The charge is already inside the 1,200s preparation/audit/reporting allocation:
`542.6320663 + 657.3679337 = 1,200s`. Thus only 657.3679337s remains in that
frozen reserve for future audits/reporting and any integration work charged to
this category. The separate 2,400s training and 3,000s evaluation allocations
remain unchanged. Because the four required implementation/validation groups
have no defensible estimate yet, evidence does not show that they fit within
the remaining reserve; this is the unresolved cost decision, not an observed
overrun.

Research-route scope remains the already recorded one: task2594 supplies the
finite standard-Chess TD validation, and task2636 is the same learner's finite
generated-rule transfer panel. The route audit does not establish full
Generic-domain coverage, seed stability, or replace the separate
TreeStrap-versus-TDLeaf question. The present cost decision only keeps this
transfer panel unregistered until its missing runner/audit/stop work is scoped.
See `ROUTE_REASSESSMENT_20261021.md` and `PRE_REGISTRATION_GAP_MATRIX.md`.

Evidence inspected: `one-init-root-plan.json`, `prefix-audit-status.json`,
`one-init-study-plan.json`, `ALL_IN_COST_COMPLETENESS.md`,
`PIN_AND_COST_SCOPE_RECHECK_20261021.md`, and session
`9e97f96e-1a97-4cdd-994c-6f2b2cedc337`.
