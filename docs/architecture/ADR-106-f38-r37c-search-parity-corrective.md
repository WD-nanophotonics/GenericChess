# ADR-106 — F38 R37C frozen-search parity corrective

- Status: accepted audit result; no production integration
- Date: 2026-09-01
- Work order: `GENERICCHESS-F38-CORRECTIVE-R1-FROZEN-R37C-SEARCH-PARITY-AND-BOUNDARY-RECLASSIFICATION`

## Corrective decision

F38 first pass used the wrong original-ten-root search-parity oracle. It
compared `ProductionShapedR37CPrototype` to V1 production search, although the
required target was frozen F37 R37C search. The defect identifier is
`WRONG_ORIGINAL_SEARCH_PARITY_ORACLE`. Its first-pass 0/10 comparison is
therefore non-outcome data for prototype parity; all first-pass F38 artifacts
remain preserved as frozen evidence.

R1 replays the exact F37 fixed-node protocol on the same ten roots at 512 and
2048 nodes: Standard-Shogi production authority, fresh transposition table per
run, deterministic node limit, max depth 8, qsearch 4/8, and the same
native-legality request behavior. It excludes timing and NPS from exact
identity.

## Three-way result

For all 20 root/budget runs, the seven deterministic fields (selected move,
score, PV head, completed depth, main nodes, qnodes, termination reason) match
exactly for every comparison:

- Frozen F37 R37C versus fresh `CandidateEvaluator(production, "R37C")`: 20/20.
- Frozen F37 R37C versus `ProductionShapedR37CPrototype`: 20/20.
- Fresh F37 R37C oracle versus production-shaped prototype: 20/20.

There is no divergent row. Thus
`ORIGINAL_TEN_ROOT_R37C_SEARCH_IDENTITY=true`; the R37C production-shaped
prototype is search-identical to the frozen F37 R37C evidence.

## Boundary reclassification

R1 consumes, but does not rerun, H38A/H38B holdout evidence. The independent
20-position F30 transcript holdout remains a negative generalization result:
R37C mean AlphaSho-action rank is 11.4 versus V1 8.9 (-28.09%); top-3 is 8
versus 9; 10 positions worsen and 5 worsen by more than three ranks. Its
static signal and independent search signal therefore remain failed, even
though static identity, generic transfer, micro-cost, search cost, and runtime
safety pass.

`F39_IMPLEMENTATION_ELIGIBLE=false`. The single corrected next boundary is
`F39_EVALUATOR_REENTRY_GENERALIZATION_CORRECTIVE`, not a search-interaction or
prototype-parity diagnosis. No evaluator/search/Native/rule/runtime production
change, no holdout reselection, no AlphaSho/paired benchmark rerun, and no
R37C fitting is authorized by this ADR.

## Evidence binding

`tests/fixtures/f38r1_frozen_r37c_search_parity.json` binds SHA-256 identities
for the F37 search/rank/selection/R1 fixtures, H38A manifest and descriptor,
and every required first-pass F38 script/fixture. The companion test verifies
those bound hashes against the repository files, as well as the zero production
diff guarantee.

## Verification

The F38 R1 and inherited F38/F37-to-F25, semantic, AlphaBeta,
SearchPathRuntime, terminal, and repetition focused regression passed. Fresh
full pytest collected 1260 tests and passed 1247. The only 13 failures are the
documented historical nodes: F13 (4), F14 (2), F21 (6), and F24F (1).
