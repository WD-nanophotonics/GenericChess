# Task2636 one-init TDLeaf study design review

This is a source-bound design only. The task2636 root pool is prepared and
audited, but this record does not register, train, or evaluate a model.

The frozen panel contains 120 training roots and 16 evaluation roots for each
of the 16 task2633 generated rules. All candidates have the same ordered ten
fixed-scale channels, confirmed across every selected root; training would
use one shared initialization seed (1977), producing the same ten-coordinate
initial vector for each rule, 250,000 combined candidate-plus-foe nodes per
rule, and the task2625 fixed-scale TDLeaf/search-bootstrap method. This
preserves four million aggregate training nodes. Evaluation would compare each trained model
with its own initialization over 16 roots per rule, both learner colors, and
actual terminal W/L/D only: 1,024 slots and 512 paired root/color contrasts.
Horizon, search/resource cutoffs, non-scoring terminals, and incomplete slots
remain UNKNOWN or missing; none becomes a draw.

The review found a hard-cap accounting issue in simply reusing task2625's
phase caps. Its 2,400-second training cap plus 3,600-second evaluation cap and
the 1,200-second prep/audit reserve sum to 7,200 seconds, above task2636's
6,600-second ceiling. The new design therefore sets a 3,000-second evaluation
cap, leaving training at 2,400 seconds and the combined prep/audit/reporting
lifetime reserve at 1,200 seconds. Lifetime allocations sum exactly to 6,600
seconds (110 minutes). The root plan conservatively budgets 542.632 seconds
for task2636 preparation/audit work already accounted in its estimate, leaving
657.368 seconds for future replay, analysis, and reporting. This is a budget
allocation, not a claim that projected preparation time was all measured. A
future separately registered runner must enforce one cumulative deadline
across phases, preserve partial results at the deadline, and cannot extend the
cap. The projected all-in duration remains 4,001.99 seconds (66.70 minutes),
not a guarantee.

Two scope limits remain explicit. First, the prepared root pool only requires
one non-anchor feature to be active: six training rules and fifteen evaluation
rules do not cover all ten dynamic channels at the root, with evaluation as low
as three channels. The frozen roots must not be changed to chase coverage.
Second, one initialization provides no seed or population estimate; exact
action-prefix exclusion does not establish transposition or distributional
independence. Any result is a finite feasibility signal on these 16 generated
rules only.

The current mailbox probe `GC-MAIL-c8b6e4526c844fd79a912a6be946526a` was
already read and saved through `1792521109.445779`; it contains no new
DEV_AUX advice beyond reviewed comments. The suggested task2625
rule271003 censoring profile is already present in
`results/dev_aux/task2625/CHAT_CENSORING_PROFILE_20261021.md` and
`CHAT_CENSORING_REVIEW_20261021.md`; it remains a descriptive frozen-log
analysis and does not justify resampling or changing this root pool. The
other optional comments concern PRIMARY-owned work or completed/unchanged
backlog and are deferred under their recorded exact-revision decisions.

The complete machine-readable design and source hashes are in
`one-init-study-plan.json`. No prior frozen cap, result, or root was changed.
