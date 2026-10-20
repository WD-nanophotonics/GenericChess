# task2635 outcome-blind feature activation review

## Question and frozen design

Task2634 found that all16 task2633 generated rules begin with the same all-zero
fixed-scale material vector. This bounded follow-up asked whether material
channels become active under short legal histories, without using game outcomes
or selecting histories by feature response. The frozen design used16 rules ×4
fixed-seed trajectories, uniform selection among sorted legal board `ACTION`
choices, and a128-ply ceiling. Declarations, WDL/result methods, search, models,
learner updates, training and strength evaluation were excluded.

## Execution and recovered evidence

Attempt001 stopped before creating an output directory because the plan had a
63-character typo in one source digest; the exact failure is retained in
`preflight-attempt-001-failure.json`. Attempt002 passed all source pins and
flushed64 complete trajectory records (7,553 plies) with full-history
replay checks. Its producer then raised a `NameError` in the final summary
writer. The failure is retained in `producer-attempt-002-postrun-error.json`.
No trajectory was rerun: a separate read-only reconciliation independently
replayed all64 durable records and reconstructed the summary.

All64 trajectories (4/4 for every candidate rule) reached a nonzero fixed-scale
material vector. First activation occurred between ply1 and ply30; the pooled
upper median was ply3. By candidate, the four observed first-activation upper
medians ranged from ply1 to ply13. These are feasibility traces under the
declared deterministic seeds, not estimates of action frequency, a rule
population or strength.

Fifty-seven traces stopped at the128-ply limit and remain outcome-unknown.
Seven had no board `ACTION` available; their actual result was deliberately not
queried, so those endings also remain unknown. No winner, reward or WDL value
was read, and no search query or learning update occurred. The legal-action API
internally consults `SessionResult.status` as a guard against actions after a
terminal state; the trajectory did not inspect that status to assign outcomes.
The seven no-action cases remain unclassified. See
`methodology-clarification.json`. All generated histories are now exposed and
must be excluded from later evaluation pools.

## Decision and limits

The fixed-scale material interface is not structurally stuck at its zero start:
these candidate rules produced legal histories with nonzero channels early in
all64 bounded traces. This only supports continuing to a separately prepared
learner feasibility/design question. It establishes no TD update, useful search
target, terminal rate, strength, holdout property, full-domain transfer or
population-level activation rate. Preserve every censored history as unknown;
do not impute it as a draw or use these exposed records for validation.

Frozen plan: `plan-v2.json` (SHA-256
`8218db1425f2ba379963afcb607db9904443ee58205cc25241ff3518301847cc`). Durable
episode log: `run-v2/episodes.jsonl` (SHA-256
`6ed7bee558d1077de78905d98aa3133bf6b43bccb59150cb11e96a602c032254`).
Reconciled result: `run-v2/reconciled-result.json` (SHA-256
`d271422363d3527c84a3edb41c0f3d65d72e773a3d8ee91890d7e5d53087ce91`).
