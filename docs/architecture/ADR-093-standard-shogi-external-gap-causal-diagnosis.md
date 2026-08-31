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
