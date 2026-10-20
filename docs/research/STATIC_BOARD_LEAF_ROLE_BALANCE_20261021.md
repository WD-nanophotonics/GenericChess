# Isolated static board leaf values under 5x5 D3 budgets — 2026-10-21

## Question and preregistered decision

The preceding fresh 5x5 `leaf-only` replication changed both board and hand
weights in its static checkpoint. This two-stage follow-up isolates static-v2
**board** values: Unit hand weights in every arm, no optional dynamic/spatial/
compact terms, promotion-potential weight absent, and Unit ordering for both
candidate and fixed Unit foe. Search limits are matched at D3, 8192 nodes,
0.5 s, q0, TT0, root-window pruning off, with a 96-candidate-ply horizon.
Promotion, drops, actual Core terminals, full histories, and unresolved UNKNOWNs
are preserved. No product or evaluator default changed.

Before either outcome run, the retention rule required strictly positive
all-slot reward lower bounds overall, for both candidate owners, and after each
leave-one-seed-out omission; the median paired candidate-node cost could not
increase by more than 10%. UNKNOWN rewards were independently bounded in each
paired contrast by [-1,+1]. Passing the aggregate criterion alone was
insufficient.

## Panel A: fresh four-ply roots

Plan and complete records: `data/static_5x5_board_leaf_unit_hand_20261021/`.
Eight disjoint seeds (530201–530208), two deterministic four-ply roots each,
both candidate owners, 64 physical games. Static-v2 board values were the only
evaluation change; the opponent and ordering stayed Unit. All 64 slots returned,
62 were actual terminals and two were UNKNOWN. There were no unstarted slots,
history-replay mismatches, fallbacks, qnodes, or search-budget overruns.

Static-board minus Unit conservative reward bounds were `[+0.375,+0.500]`
overall and `+1.000…+1.125` for owner 0, but `-0.250…-0.125` for owner 1.
Both leave-one-seed-out lower bounds remained positive (minimum `+0.2857`). The
cost gate passed strongly: median paired candidate nodes fell 35.36% (median
absolute change -27,083.5 nodes) and median candidate caller time fell 0.386 s.
The outcome gate nevertheless failed for owner 1. Crucially, every root used a
four-ply opening, so side 0 always moved first: owner and first/reply role were
perfectly confounded in this panel. This result alone cannot identify which
factor accounts for the reversal.

## Panel B: fresh 3/4-ply role-balanced roots

Plan, feasibility screen, outcomes and replay analysis:
`data/static_5x5_board_leaf_role_balance_20261021/`. This was a new 64-game
panel; no outcomes were pooled with Panel A. Eight accepted seeds were
530301–530306, 530308 and 530310. Before outcomes, the fixed generator schedule
rejected 530307 (terminal after one opening move) and 530309 (terminal at the
four-ply root); 530310 was the next ascending candidate whose two planned roots
were both ongoing at their exact prefix lengths. The filter used only root
feasibility, not game results, and narrows the sample to rules passing that
screen. Each rule supplied one three-ply root (side 1 to move) and one four-ply
root (side 0 to move); preflight verified 8 roots of each side to move, eight
distinct rule fingerprints, and exact Unit-hand/empty optional-term parity.

All 64 games reached actual terminals; there were no UNKNOWNs, unstarted slots,
replay mismatches, fallbacks, qnodes or budget overruns. The pooled exact
contrast was `+0.09375`; by candidate owner it was `0` for owner 0 and `+0.1875`
for owner 1. By first/reply role it was `+0.3125` for candidate-first and
`-0.125` for candidate-reply. The owner-by-role cells (eight paired roots each)
were:

| Candidate owner | Candidate first | Candidate reply |
|---|---:|---:|
| 0 | +0.25 | -0.25 |
| 1 | +0.375 | 0 |

The leave-one-seed-out lower bound reached `-0.0357`, so even the small pooled
positive contrast was not seed-robust. The paired candidate-node cost gate
passed narrowly: median relative change `-1.68%` (median absolute change -121
nodes), and median caller-time change `-0.0109 s`. The owner, role and
leave-one-seed gates failed. Candidate-first outcomes are descriptively more
favorable in this finite sample, but the roots differ by one opening ply; the
design cannot assign the pattern causally to turn role rather than to the
resulting state difference. The feasibility screen is an additional scope
limit.

## Interpretation and next route

The controlled comparison shows that board values alone can change finite
search outcomes and choices, but this study does **not** establish an
owner-robust 5x5 D3 utility signal. Panel A's apparent role reversal was
confounded by its all-four-ply roots; Panel B reduces that aliasing descriptively
but retains owner-by-role and seed heterogeneity. Do not retain this board-only
candidate as owner/role-robust, do not repeat these panels or widen the 5x5/6x6
sweep, and do not change a global price vector or default. This does not refute
the separate complete static-v2 candidate evidence, whose hand and other
components differ.

Next, select one distinct GenericChess rule-price transfer consumer from
existing evidence. Any new panel needs a changed premise and a predeclared
decision it could change; avoid another sample of the same 5x5 D3 board-only
question. These results are finite generated legacy-rule evidence, not a
population, all-rule, WDL, human-price or global strength claim.

Replay and independent paired-cost commands (run from repository root):

```powershell
.\.venv\Scripts\python.exe docs/research/data/static_5x5_board_leaf_unit_hand_20261021/analyze.py
.\.venv\Scripts\python.exe docs/research/data/static_5x5_board_leaf_unit_hand_20261021/independent-cost-audit.py
.\.venv\Scripts\python.exe docs/research/data/static_5x5_board_leaf_role_balance_20261021/analyze.py
.\.venv\Scripts\python.exe docs/research/data/static_5x5_board_leaf_role_balance_20261021/role-strata-audit.py
```
