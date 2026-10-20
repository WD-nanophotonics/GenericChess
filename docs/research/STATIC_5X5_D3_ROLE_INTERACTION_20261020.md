# Static 5x5 D3 utility and role interaction — 2026-10-20

## Decision question

Does the scoped `static_v2` leaf candidate show a stable utility effect under
symmetric D3 budgets, and did move ordering cause the earlier contrast? The
result can retain a cheap candidate, but cannot by itself change a global price
vector or default.

## Attribution panel

`data/static_5x5_d3_price_order_factorial_20261020/` contains the fixed plan,
producer/analyzer sources, exact roots, profiles, rules, complete game/query
records, and validated analysis. Eight rules × two four-ply prefixes × both
candidate owners × four candidate arms produced 128 games against a fixed
Unit-leaf/Unit-order foe. Search used D3, 8192 nodes, 0.5 s, q0, TT0 and no root
window pruning. All 128 returned; 124 were actual terminals, four UNKNOWN, no
unstarted slots or replay mismatches. The analyzer regenerated the roots and
profiles, replayed all games, and checked every query/budget record.

For static leaf at Unit ordering minus Unit leaf at Unit ordering, conservative
all-slot reward bounds were `[+0.375,+0.500]`; ordering-only at Unit leaf was
`[0,0]`. Ordering-only at static leaf and the leaf×ordering interaction were
each `[-0.125,+0.125]`. In the paired order-swap cells, no candidate action
sequence, complete action path, or reward changed. Thus the measured contrast
is leaf-mediated on these roots; the finite panel does not establish that move
ordering is irrelevant elsewhere.

## Independent fresh-root leaf replication

`data/static_5x5_leaf_only_replication_20261020/` records a separately
prespecified cohort with seeds 529101–529108. A scan of all 24 research
`plan.json` files found no overlap with those seeds. Eight generated rules ×
two four-ply prefixes × both candidate owners × two leaf arms yielded 64 games;
both arms used Unit ordering and the foe remained Unit/Unit. Search and budget
conditions matched the attribution panel. All 64 returned (63 actual terminals,
one UNKNOWN, zero unstarted), with 2,838 query records, 15,954,523 nodes and no
history-replay mismatch, fallback, or cap overrun.

Static-leaf minus Unit-leaf conservative all-slot bounds were `[+0.3125,+0.375]`
(31 finite cells, finite mean `+0.3871`). Leave-one-seed-out lower bounds
remained at least `+0.2143`; this is a within-cohort robustness check, not a
population interval. Candidate first actions differed in 17/26 shared
candidate-first states and complete paths differed in 24/32 paired games.
Among the 17 differing first actions, 11 were board→board, one board→drop,
four board→promotion, and one promotion→board. This confirms the changed
choices include promotion and drop semantics in this sample; it does not
attribute the outcome gain to any one action class.

The owner/turn stratum was not stable between the two disjoint cohorts. In the
first cohort, owner-0 minus owner-1 treatment-effect bounds were
`[+0.125,+0.375]`; in the fresh cohort they were `[-0.625,-0.500]`. Conservative
interval subtraction gives a fresh-minus-prior owner interaction of
`[-1.000,-0.625]`. In the fresh cohort alone, candidate-first bounds were
`[0,+0.1429]`, while the candidate replying after the fixed Unit move had
`[+0.7143,+0.7143]`. The cohort-level shift is descriptive: different generated
rules/prefixes are not a randomized treatment of “cohort”, and these small
panels do not identify why the role effect changes.

## Interpretation and next decision

The aggregate fresh-cohort gain and positive leave-one-seed-out bounds are
finite evidence for retaining `static_v2` as a cheap scoped candidate. The
strong change in owner/turn strata across disjoint cohorts blocks a role-stable
or global usefulness claim. No price vector, search default, or product code is
changed. Do not enlarge this same-rule 5x5 panel without a new consumer or
changed premise. A later cross-size result is useful only if it tests whether
the role interaction is a 5x5 artifact and would change candidate scope; do not
pool these cohorts as independent population samples.

## Separate search-caller source closure

The current unfamiliar-rule caller scan found no implementation-changing gap
in two plausible boundaries. `SessionStatus` session-owned resignation and
declaration terminals leave Core state ongoing, but `AlphaBetaPlayer` returns a
zero-work `TERMINAL` decision for those statuses; Core terminal states are
short-circuited by `run_root_search`. `NO_CONTEST` from Core and neutral
declarations remain unresolved in the benchmark rather than being fabricated
as a draw/win. Existing regressions cover every terminal enum and serialized
session replay. Separately, `SearchSnapshot` is deliberately a shallow frozen
envelope; GUI mutations (move, declaration, resignation, restart, undo/redo)
advance generation/cancel, and stale results are rejected. `SearchBackend` has
no production UI/benchmark caller and returns `PlayerDecision`, not per-root
action scores, so a new score-table API has no current consumer. The final
seven-module product set covering evaluation, semantic opportunity, search
runtime, AI match, benchmark, finished-session search and CLI passes with a
project-local pytest basetemp. An initial run
failed only creating pytest's default Windows Temp directory; the same targets
passed after relocating basetemp into ignored `.local_agent` and disabling the
cache provider. This is an environment limit, not a test or product failure.
