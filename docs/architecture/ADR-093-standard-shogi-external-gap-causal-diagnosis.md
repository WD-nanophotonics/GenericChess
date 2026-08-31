# ADR-093: Standard Shogi External Gap Causal Diagnosis

## Status

Accepted as an audit protocol; F31 results are recorded in the bound fixture
`tests/fixtures/f31_causal_diagnosis.json`.

## Context

F30 R1 established a frozen external AlphaSho comparison and a corrected
persistent-player GenericChess match. The clean score was `0W/3D/17L` (0.075),
so the next decision must distinguish evaluator value, search horizon, root
fallback overhead, qsearch/order/TT policy, Python semantic throughput, and
Native legality availability without tuning the product from the result.

## Decision

F31 uses an additive, audit-only harness. It consumes the exact F25/F30 frozen
roots and F30 R1 evidence, freezes a SHA-bound pre-diagnosis manifest, and runs
static evaluator ranks, bounded qsearch ranks, timing and policy ablations,
node-budget and horizon ladders, forced-candidate scores, a stripped RuleSet
Native counterfactual, and a three-game stalemate correctness gate. The
stripped RuleSet removes only declarations and automatic adjudications; legal
sets and evaluator-v1 root-perspective scores must be proven identical before
its throughput comparison is interpreted.

No file under `generic_chess/` is changed. F30 R1 remains the authoritative
paired-match anchor; F31 does not start a new broad paired match or use results
to alter evaluator coefficients, search defaults, rules, or runtime behavior.

## Boundary selection

The harness records exactly one next boundary after all gates pass. A Native
capability boundary is selected only when the stripped counterfactual materially
raises completed depth without changing legal sets or static scores; otherwise
the fixture records the most supported search/evaluator boundary and leaves
implementation for a subsequent Chat-issued work order.

## Evidence

The pre-diagnosis manifest and consolidated result are SHA-bound and published
with the checkpoint that closes F31. Raw benchmark output and Courier state are
not retained in Git.

The F31 run passed all six completion flags with manifest SHA
`e08867b24fc268581b7853caf8e6bf2da0d2c25307c36120540313ea44f677dd`.
Static evaluator ranks put the fresh AlphaSho 0.50 s / 2.00 s modal moves
outside evaluator-v1 top-3 on 8/10 roots, matching the prior F22 observation;
the current fresh AlphaSho controls also have an outside-top-3 count of 8/10.
The qsearch comparison did not produce an aggregate quality gain, while the
0.50 s baseline used root fallback on all ten roots and completed depth 0; the
2.00 s baseline completed depth 1 on all ten roots. The fixed-node matrix did
not show a consistent TT/order/PVS improvement, and the horizon extension
subset contained both never-recovered and unstable/stable cases rather than a
uniform horizon recovery.

The stripped RuleSet proved exact legal-set and static-score equality on all
10 roots, but live, stripped/native-off, and stripped/native-requested runs
all reported `PYTHON_AUTHORITY_FALLBACK`; the result is therefore explicitly
`NATIVE_COUNTERFACTUAL_UNAVAILABLE`, with no Native repair attempted. The three
draw transcripts were independently verified as product `stalemate`, zero
legal actions, side not in check, and zero cshogi legal actions.

Aggregate labels are: root fallback/tactical scan overhead PRIMARY, Python
semantic/legal-generation throughput PRIMARY, evaluator/value SECONDARY,
qsearch NOT_SUPPORTED, horizon/depth UNRESOLVED, TT/order UNRESOLVED, and
Native capability gating UNRESOLVED with the separate unavailability marker.
The evidence-based next boundary is exactly
`F32_ROOT_SEARCH_FALLBACK_AND_BUDGET_ARCHITECTURE`; F31 makes no production
change and does not authorize implementing F32 in this checkpoint.

The full regression completed with the expected historical result: 12 failures
in the F13/F14/F21 Native suites (`enum code out of allowed domain` or provider
unavailable) and one F24F Kiwipete perft mismatch (`45` versus the historical
expected `48` at depth 1). No additional failure was introduced by F31.
