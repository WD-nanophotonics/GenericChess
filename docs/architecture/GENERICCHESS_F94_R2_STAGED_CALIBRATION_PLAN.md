# GenericChess F94-R2 staged calibration proposal

Status: proposal for Chat review. No Stage 0 Arena and no Heavy computation
has been launched.

The previously prepared 18-invocation plan remains unapproved evidence only.
Its 12-hour single-lane envelope is intentionally not started: it lacks
runtime power/variance evidence, and its fixed full-schedule stop rules do not
permit a cheap decision bound.

## Stage 0: smallest useful runtime calibration

Use the two READY candidates from the frozen F94-R2 PREP (Built-in Western
Chess and Built-in Standard Shogi) and the same three frozen tape corpora. For
each candidate/tape, run exactly one role-swapped pair for the strongest-vs-
weakest matchup: 4096 nodes per move versus 256 nodes per move, depth 12, 8 MiB
TT, workers=1 inside each Arena. This is six Arena invocations, six paired
pairs, and twelve games total. The boundary candidate is not run; it remains
an A/C prerequisite short-circuit with compute zero.

Stage 0 must record, per invocation and per tape:

- exact corpus and PREP identities, pair/opening identity, and role-swap game
  evidence;
- paired score, pooled effect, and a descriptive uncertainty interval;
- wall time, actual searched nodes/NPS, completed depth, fallback telemetry,
  and any cap or operational failure;
- an explicit direction classification: positive, negative, mixed/uncertain,
  depth-censored, fallback, or operationally unresolved.

The two candidates and three tapes are independent measurement units. Keeping
`workers=1` inside each Arena preserves deterministic single-game behavior;
outer tape/candidate parallelism is not used in Stage 0 unless Chat approves a
separate envelope, because it would add scheduling/resource complexity before
runtime cost is known.

## Stopping and expansion rules

Stop after Stage 0 when either candidate has a consistent clearly negative
response across tapes, any fallback/depth-censoring/cap/operational failure
invalidates the response, or the measured runtime makes the next stage
economically unjustified. These are findings, not draws or PASS results.

If both candidates show a positive direction on all three tapes but the pooled
effect remains uncertain, a separately approved Stage 1 may increase to two or
three pairs per tape for strongest-vs-weakest only. Stage 1 remains bounded at
18 pairs/36 games total and must use the same frozen tapes and identities.

Only if Stage 0/1 establishes a reproducible positive budget response with no
censoring/fallback and sufficient effect size should a separately reviewed
Stage 2 add the 1024-node adjacent matchup and consider the original six-pair
full schedule. No stage authorizes Layer-E training, Gen1-to-GenN recovery,
AlphaSho benchmarking, search/evaluator tuning, or ruleset modification.

## Approval boundary

Before any Stage 0 run, generate and publish a new result-free PREP if the
Stage 0 schema requires a one-pair scope, then create an exact versioned
resource envelope and compute plan for the six invocations/twelve games.
Chat must approve the exact staged plan and envelope; the registered
Supervisor must bind the approval to the exact current sandbox SHA, plan SHA,
envelope digest, and command argv. Every Heavy invocation still carries the
explicit envelope, and only one GenericChess Heavy job may run at a time.
