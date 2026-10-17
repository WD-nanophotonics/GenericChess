# Fixed/probe terminal dominance — 2026-10-17

The accepted material range exposed a real compatibility-search defect. On the
existing western-chess mate-in-one fixture, both `probe_search` and
`fixed_depth_search` chose an ongoing position worth 2,000,000 over an actual
winning checkmate worth 1,000,000. The identical rule/state/history at rook
weight 1 chose mate. A paired six-query plan was saved before execution; all
one-ply legal outcomes were checked with Core. Both weights are accepted inputs.
The production iterative entry chose mate (99,999,999) in both cases.

The narrow repair puts fixed/probe rule wins/losses at **±100,000,000**, strictly
outside the existing ordinary static saturation **±90,000,000**. Ordinary
coefficients, integer bounds, clipping, current/base handling, terminal/winner
priority and complete history are preserved. Fixed/probe keeps its existing
absence of mate-distance scoring; production iterative/persistent search keeps
its existing root-relative mate scores. Result dictionaries and import paths
are unchanged. Terminal numeric values intentionally change; callers must not
continue hard-coding the old ±1,000,000 contract.

The rebuilt C kernel advertises `semantic_fixed_depth_terminal_dominance`.
Current Python fixed/probe wrappers explicitly refuse stale kernels missing it,
with `NativeUnsupportedRuleError`: rebuild, use existing iterative search, or
use Core. There is no implicit fallback/history truncation. A real separately
bound pre-fix binary (its own rules/position capsules) is refused by both wrappers;
production D2 on two profiles preserves exact score/action/PV/nodes/depth across
the old and rebuilt binaries. This bounded check is not all-domain or timing
identity. Direct historical raw binaries naturally retain their old behavior.

The exact six original inputs now all choose mate through the intended entries.
New tests cover signed accepted profile extremes, Core-verified winning actions,
terminal roots at depth zero, unchanged high-hand ordinary saturation, state
restoration and stale-kernel refusal. Before fixing, six new assertions failed
and four saturation cases passed. After rebuilding, all **70 affected checks**
and the **full 3,284-test active regression** pass (307.53s for the full run;
70 is a subset, not another independent suite).

The preceding 7,040-game mature comparison used the already-correct production
semantic search, so this does not invalidate its frozen data or justify rerunning
it. Legacy non-semantic search is a separate entry, not changed here. No AUX
checkout, solver, learner, checkpoint optimizer or default model was changed.
An initially refused exact-text edit and snapshot-container harness setup errors
were retained privately; no build/publication followed the failed edit, and
no actual diagnostic result was overwritten to hide a failure.

Inputs, before/after receipts, real old-kernel control and validation counts:
[data/probe_terminal_score_band_20261017](data/probe_terminal_score_band_20261017).
The original pre-fix source is fixed public revision
[05c8c16351a9ffbffe20333ee8ad0d598bb1cd8a](https://github.com/WD-nanophotonics/GenericChess/tree/05c8c16351a9ffbffe20333ee8ad0d598bb1cd8a).
This closes the specific score-band defect, not the complete scientific target.
