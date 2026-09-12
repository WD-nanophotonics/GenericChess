# F94 R7 Layer-D design review: fallback semantics and budget-response gates

Status: design review only. This memo does not change the frozen R6 result,
classifier, PREP, executor, or authority decision, and it authorizes no new
Arena/Heavy run.

## Evidence boundary

The review is a deterministic read of the identity-bound R6 progress evidence.
The source RESULT is
`a3008d1cc0150b82bc1682e7873a9cbe6c27232f359e57479689b486c956e4fe` and the
progress evidence digest is
`fc84255ad869240e77e4b0a38a863e86a689e48f646d0fac59300fb19b7408de`. The
machine-readable extraction, including the complete response matrix aligned by
`(tape_seed, pair_index)`, is
`GENERICCHESS_F94_R6_FALLBACK_FORENSICS.json`.

The extractor found 29 `used_fallback=true` decisions. All 29 are in Standard
Shogi `1024_vs_256`, all are parent-side at the 256-node budget, and all have
`completed_depth=0`, `termination_reason=node_budget`, and
`decision_kind=action`. They occur in two pairs: 20 rows in tape 9801 pair 5
and 9 rows in tape 9802 pair 0. There are no child-side, 1024/4096-node,
time/cancel, or internal-error fallback rows in the frozen evidence.

## What `used_fallback` means

The Arena telemetry appends one row per search decision. Its index is the ply
for an action decision (and the final index is the ply count for an optional
declaration). The native semantic search sets `used_fallback` only when no
complete iterative-deepening iteration has returned. Its fallback order is:

1. a declaration win;
2. a neutral declaration; then
3. the deterministic minimum legal action.

The native termination code separately reports `node_budget`, `time_budget`,
`cancelled`, or `internal_error`. Therefore the R6 rows are a legal root
fallback caused by budget exhaustion before the first complete iteration, not
evidence of an engine crash or a missing legal move. This is a semantic chain,
not a claim that the selected action is strong. A time/cancel/internal outcome,
a high-budget node fallback, or a post-iteration fallback must remain a
separate operational/review category.

## Budget-response gate candidates

### A. Every pairwise matchup must be strictly positive

This is easy to state and protects against any observed reversal. Its failure
mode is that it treats adjacent budget noise and a genuinely bad endpoint as
the same event. It also makes the decision sensitive to the number of adjacent
matchups: adding diagnostic comparisons can only make the gate harder to pass.
That is a selection/availability risk when the endpoint question is whether
the largest budget beats the smallest budget.

The R6 positive-control calibration is a warning against using A as an
authority rule. Western `4096_vs_256` is positive, while `4096_vs_1024` is
uncertain and locally negative. In the aligned matrix, the adjacent matchup
has 11/18 scores at or below 0.5 (only 2/18 are strictly negative), and those
at-or-below outcomes touch all six opening indices. A would reject an otherwise
positive endpoint because of a diagnostic adjacent surface. R6 itself remains
`DEFER_CONTROL_NOT_READY`; this observation does not rewrite R6.

### B. Make `4096_vs_256` the blocking primary gate

Under B, the endpoint matchup is the primary budget-response question. The two
adjacent matchups are consistency and anti-reversal diagnostics; uncertainty in
an adjacent estimate does not by itself negate the endpoint. An explicit
negative reversal still blocks.

B has the opposite failure mode: a positive endpoint can hide a non-monotone
intermediate surface, and choosing the endpoint after seeing R6 would be
post-hoc selection. The guard against that bias is prospective registration of
the primary endpoint, all diagnostics, the reversal definition, and disjoint
tapes before R7 data are collected. R6's positive-control behavior is
compatible with B as a diagnostic design, but is not sufficient approval to
change the current authority gate.

## Fallback-rule candidates

### A. Any fallback means DEFER

This is conservative, but it confounds a legal low-budget root fallback with an
operational/search failure. On the frozen sample it would turn the two Shogi
pairs containing 29 low-budget parent fallbacks into an undifferentiated
blocker, even though no high-budget or operational fallback occurred. That
creates availability bias against rulesets whose low budget cannot finish a
full iteration and obscures the mechanism that produced the row.

### B. Block only high-budget or operational fallback

This rule records low-budget, pre-first-iteration node fallback as a weak-search
strategy diagnostic, while blocking high-budget fallback and time/cancel/internal
outcomes. It preserves the distinction needed for a budget-response experiment:
the low-budget policy surface is intentionally weak, but a high-budget engine
failing to complete an iteration is an execution or search-integrity concern.

B can under-detect a systematic low-budget fallback problem, so R7 must report
fallback counts and rates by role, budget, tape, pair, and decision index. A
pre-registered rate or concentration threshold may become a diagnostic, but it
must not be chosen because it makes the current Shogi result pass.

## Design recommendation for prospective R7

Keep R6 frozen and do not reinterpret its `DEFER` outcomes. For a future,
separately approved R7 validation, carry B as the candidate design with the
following pre-registered guards:

* `4096_vs_256` is the blocking primary response gate;
* adjacent matchups are diagnostics, and only an explicit strict-negative
  reversal blocks; statistical uncertainty alone does not;
* low-budget node fallback before the first full iteration is a separate weak-
  search observation;
* high-budget fallback and time/cancel/internal outcomes are operational
  blockers;
* all rules, thresholds, tape allocation, and fallback strata are frozen before
  using any new disjoint tapes.

This is a prospective hypothesis, not a promotion or a new compute plan. The
current R6 authority remains unchanged.
