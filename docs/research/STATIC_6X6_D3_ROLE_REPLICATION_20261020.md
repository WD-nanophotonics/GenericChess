# Fresh generated 6x6 static-leaf role replication — 2026-10-20

## Decision question and preregistered choice

Two disjoint generated 5x5 cohorts had positive aggregate static-v2-leaf effects,
but their candidate-owner/turn interaction differed materially. This single
fresh-size replication asked whether static-v2's isolated leaf effect would
remain strictly positive for both candidate owners on eight new generated 6x6
rules. Widening the finite candidate scope required positive all-slot lower
bounds overall, for each owner, and after leaving out each rule seed. Failure
keeps static-v2 at its prior 5x5 candidate scope. Neither outcome could change
the global price vector or activate a default.

The fixed 64-game design used eight previously unused seeds (539101–539108),
two deterministic four-ply roots per rule, both candidate owners, and paired
`unit_leaf__unit_order` versus `static_v2_leaf__unit_order` arms. Both candidates
and the unchanged foe used Unit move ordering; the fixed foe also used Unit
leaves. Both sides had the same D3/8192-node/0.5-second/q0/TT0/root-window-off
budget. UNKNOWN outcomes were retained and independently bounded at [-1,+1]
per signed arm reward. No training, solver, extra arm, seed reuse, extension,
or split run was used. Before execution, a recursive scan parsed all 24 prior
research `plan.json` files and found no occurrence of any of the eight rule
seeds.

## Execution and integrity

The one producer process closed all 64 slots in 315.125 seconds under its frozen
2400-second cap. It returned 60 actual terminals and four candidate-horizon
UNKNOWN games, with no unstarted slots or full-history replay mismatches. The
independent analyzer regenerated all eight rules, profiles and 16 roots; checked
the plan, source, head and tracked-code hashes; matched every query
to its game and every selected checkpoint to the planned arm; and replayed all
64 full records. It found zero fallback queries, node/depth/time-cap violations
or replay mismatches. The 2,802 search calls used 21,201,734 total nodes. Across
all moves, records contain 2,259 board actions, 543 drops and 72 promotions.

## Result

Static-v2 minus Unit had an all-slot reward interval of [+0.2500,+0.5000] across
32 matched root-owner cells; the finite-only mean was +0.4138 across 29 cells.
All eight leave-one-seed-out lower bounds were positive (minimum +0.2143).
However, the preregistered owner condition failed: candidate owner 0 was
[-0.0625,+0.1875] (one paired cell contained UNKNOWN), while owner 1 was
[+0.5625,+0.8125] (two UNKNOWN-containing cells). The candidate-first stratum
was [-0.0667,+0.2000], versus [+0.6000,+0.8667] when the Unit foe moved first;
two terminal roots required no search and contributed paired zero effects.
Consequently the positive aggregate and leave-one-seed-out bounds do not justify
widening the candidate scope. The observed effect is strongly conditional on
owner/turn in this finite cohort; this does not identify a causal mechanism or
population effect.

Static and Unit first candidate actions differed in 18 of 30 comparable states;
full action paths differed in 28 of 32 pairs. These are behavior changes, not
independent utility samples. Per-arm work totals reflect different trajectories
and are not an efficiency comparison: the static-leaf candidate made 679 calls,
used 5,024,390 nodes and 73.12 caller-seconds; Unit made 726 calls, 5,663,641
nodes and 80.70 caller-seconds. All individual calls remained inside the common
budgets.

## Consequence and limits

Keep `static_v2` as a cheap 5x5-scoped candidate only; do not extend that claim
to generated 6x6 rules, change cross-game ratios/prices, or set a global search
default. This study does not separate board-size effects from cohort/seed effects:
the eight 6x6 rules are fresh and unpaired with the 5x5 cohorts. Its owner/turn
pattern resembles the second 5x5 cohort but differs from the first; that is
descriptive finite heterogeneity, not a size-transfer explanation. Four UNKNOWN
games remain UNKNOWN throughout all interval bounds. A new size sweep, larger
panel, or training run is not justified by this result alone.

Plan, producer, analyzer, exact rows, replay inputs, summaries and hashes are
retained in `data/static_6x6_role_replication_20261020/`. The producer records
the tracked-diff hash present at launch. The immediate post-run audit compared
that value with the then-current diff; the replay analyzer intentionally checks
the immutable tracked-code tree and source/head identifiers, not a working-tree
diff that can legitimately change as reports are written later.
