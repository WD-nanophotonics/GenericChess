# ADR-102: Post-Reserve Search Capacity Rebaseline

Status: accepted diagnosis; F37 selected

## Decision

F36 is diagnosis-only and leaves production unchanged. It consumes the frozen
F35 R1 reserve-only rows at 0.50 and 2.00 seconds, then measures one current
production ladder run per frozen root at 1.00, 4.00, and 8.00 seconds. Static
evaluator and direct configured-qdepth ranking are revalidated against F31;
the direct ranking uses an audit-only configured-qdepth shadow so the F35
run-root reserve is not mistaken for a direct/internal qsearch context.

Production diff is zero relative to the accepted F35 R1 sandbox
`80c1576c4443b4c9311b86fa0d8efbbfa24150ca`; no evaluator, search policy,
Native, rules, session, runtime, CLI, AlphaSho, paired benchmark, or
AlphaChess change was made.

## Evidence and selection

Static rank parity and direct qsearch rank parity are both exact for all ten
roots. The post-reserve ladder has depth distributions 0.50s: 8 roots at
depth 0 and 2 at depth 1; 1.00s: 10 at depth 1; 2.00s: 10 at depth 1;
4.00s: 9 at depth 1 and 1 at depth 2; 8.00s: 6 at depth 1 and 4 at depth
2. There are 8 fallback-limited roots at 0.50s, but zero roots at 2.00s
reach depth 2, zero next iterations are within 50% additional time, and zero
longer-search external recoveries occur.

The six aggregate quantities are: short-control fallback roots 8,
two-second depth-2 roots 0, longer-search external recovery roots 0,
stable-value-mismatch roots 6, static top-3 gap roots 8, and next-iteration
near roots 0. Thus search capacity is not primary-actionable under the F36
gate, while evaluator/value is primary-actionable: 8 >= 7 static gaps, 6 >=
5 stable mismatches, 0 <= 2 longer recoveries, and no near-next capacity
crossings. The aggregate classification is `EVALUATOR_VALUE_PRIMARY` and the
single selected boundary is `F37_RULE_DERIVED_EVALUATOR_REENTRY`.

The ten-root causal table and raw ladder rows are retained in the F36
fixtures. F35 R1 equal-time data and F30 AlphaSho/paired references remain
frozen and were not rerun.

