# DEV_AUX2622 — SAME fixed-scale Generic TDLeaf versus initialization

## Frozen design and root preparation

The prospective comparison uses the same task2492 `Model`/`TDLeafEpisode` on
four existing Generic rules, dynamic board-current/hand-base channels, fixed
coordinate 0 and scale 10. It predeclares four seeds, 16 training arms at
250,000 candidate-plus-foe nodes each (4,000,000 total), and 1,024 actual
terminal evaluation slots. The source-bound expected combined cost was
66.6998 minutes, below the 120-minute Chat assessment threshold. This is an
estimate, not a runtime guarantee.

The v2 root pool retains 120 training and 16 evaluation starts per rule. Its
independent audit verifies 38 source hashes, replays 544 complete histories,
and finds zero exact train/evaluation root intersections on every rule. The
pool's measured preparation time is 36.172 seconds. This establishes only
exact start-history separation from the enumerated prior records, not
descendant-state, transposition, or distributional independence.

## Registration and failed launch

The write-once registration bound the plan (`5f0fda6a…108f0674`), root pool,
root-pool audit, and 28 source files before execution. It also froze all 16
seed/rule initialization vectors. Registration expected 16 arms and 1,024
evaluation slots and did not authorize a retry or cap extension.

The sole training invocation exited with `KeyError: nodes_per_arm` at the first
training-loop guard. The plan named the budget
`training.nodes_per_arm_candidate_plus_foe`, while the runner read
`training.nodes_per_arm`. An independent AST contract audit also found that
both training and evaluation read top-level `H`, while the plan stores
`training.H` and `evaluation.H`. The first error occurred before any root
episode or search query. `queries.jsonl` and `episodes.jsonl` remain empty;
there is no training result, evaluation, or strength outcome. Exact failure
and launch evidence are in `run/launch-failure.json` and
`run/static-plan-contract-audit.json`.

## Corrective work and validation

The three consumer files as registered were copied byte-for-byte and verified
against their source pins under `run/failure-source-snapshot/`. The working
runner and independent training audit now consume the frozen node-cap field;
training and evaluation read their respective frozen horizon fields. Both
runners have preflight checks for required cap, arm, horizon, and slot-grid
fields. The corrected working files no longer match this failed registration's
source pins and were not run against it.

The static semantics review found that actual W/L/D alone receive rewards,
non-scoring terminals and cutoffs remain UNKNOWN, candidate and foe nodes share
the declared cap, and missing evaluation slots remain explicit and prevent a
complete audit or analysis. These are code-review findings, not execution
evidence. Twenty-six targeted tests pass across the recovered runner contract,
task2622 design, task2621 fixed-scale adapter, and task2511 Generic terminal
handling; Python compilation and `git diff --check` pass.

## Conclusion and limits

Task2622 has **no learning or strength result**. The prepared root pool and
study intent remain useful, but the registered one-shot failed before the first
search. The failure, empty streams, frozen registration and original source
bytes remain intact. No retry, top-up, evaluation, or cap extension was made.
Any later experiment requires a distinct registration and must not be reported
as completion of this run.
