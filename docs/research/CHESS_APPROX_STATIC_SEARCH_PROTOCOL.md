# Explicit approximate material feature in actual Chess search

Freeze2026-10-06 before search. Purpose is actual runtime integration of the
qualified five-mode virtual coefficients at full native inventory, not a
new usefulness/performance batch or claim of current-position contact values.
New research evaluator preserves full GameState/rights/EP/history for legal
search. Its STATIC feature deliberately ignores positional/auxiliary values
and prices only current ordinary counts; this is an approximate material
component. It does NOT relax old strict virtual-equivalence adapters, whose
zero-rights/EP guards remain. No production evaluator, rule or TT changes.

Native Western fingerprint,8x8,one native K each,empty hands,<=30 ordinary
P/N/B/R/Q; native origin or promoted Pawn/current ordinary type only. Exact
geometric_half and linear_mixture constants frozen before search, plus unit
baseline. Fixed half-up scale100000, no human tuning. Coeff error<=1/200000,
full inventory leaf error<=15 integer-score units and pairwise<=30; arbitrary
min/max preserves the leaf bound. Maximum static magnitude<=3,000,000 below
existing MAX_STATIC_EVAL10,000,000 and mate separation. Side-to-move sign
is explicit; local terminal scoring stays owned by the search, not evaluator.
Automatic-author draws absent from SESSION are NOT silently installed.

One initial metadata diagnostic already compiled once and applied e2-e4 once:
initial aux storage empty but default castling slots are1; double creates
EP(4,2). Its public root-list/membership entries40 and1 transition are
disclosed as a prefix; elapsed/candidate costs were not instrumented, so do
not claim a metered total for that prefix. This new bounded run compiles once
(two compilations including prefix), retains that cost, never retries prefix.

Run five depth1/q0 searches: both fixed contact laws and unit on the already
source-qualified six-action root, and geometric/unit on native full initial
position with real initial rights. Reuse saved six children, no new Core
materializations there. Enumerate/materialize ALL20 initial children with
complete membership charge; independently source-check board/actor/effective
castling/EP/history and all20 parent actions before runtime comparisons.
Pinned python-chess source/manifest identical to earlier exact qualification.
No source tables or downloads. Initial all-material ties are integration
controls, not discriminative goal tests. Exposed small-root checks are likewise
implementation controls, not fresh independent strength evidence.

Budget combined runtime pushes plus public transitions<=128, returned action
lists/membership<=5000, source pushes<=128/entries5000,15sec metered NEW
main (unmetered prefix disclosed separately), no TT/order/tactical/PVS/native
provider/fallback, max128 total search nodes, qnodes0. Instrument runtime
push/pop/actions; each searched child position/ply/terminal must match the
complete public saved child table. Complete search value must equal integer
reference max and selected action belong to FULL reference tie set. Do not
claim search tie ordering equals canonical-string ordering. Restore patches
in finally; any cap/unsupported scope fails, no fallback or output rerun.
