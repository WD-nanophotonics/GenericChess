# task2625 censoring advice review — 2026-10-21

The saved Chat suggestion for the optional rule271003 censoring analysis is
well-founded. Its requested no-new-search deliverable is already present in
the frozen outputs, so this review adopts the evidence and closes the backup
without rerunning evaluation or changing task2625's H=128 cap.

The independently audited 1,024-slot panel has 44 UNKNOWN endpoints, all
`HORIZON_UNKNOWN` at H=128, with zero per-slot node-cap hits. Rule271003 has
39/256 UNKNOWN endpoints (15.23%); the other rules have 5/256, 0/256 and
0/256. Its finite paired stratum has UNKNOWN in 35/128 pairs and exact
completion bounds `[-44, 34]` in reward-difference sum, or
`[-0.34375, 0.265625]` in mean. The bounds cross zero, so the rule-specific
comparison remains unresolved. UNKNOWN stays censored and is not a draw.

Task2629's separate H=256 evaluation has 5/256 UNKNOWN endpoints, but it uses
a new root pool and a different finite panel. That is descriptive evidence
for that panel, not a causal estimate that doubling H resolves the task2625
UNKNOWN cases; the two panels must not be pooled.

For any future decision-changing rule271003 study, freeze a fresh outcome-blind
root pool, H, node and wall caps, and an UNKNOWN-based decision/stopping rule
before execution. Stop at the registered cap and report completion bounds if
the target remains unresolved; do not extend this frozen run or select a
stopping rule after seeing outcomes. This review requests no new run and does
not reopen the completed task.

Evidence: `run/unknown-diagnostic.json` SHA256
`960c10bf0dfc520c4dc99279a1faab57a9f68797de8383becc54865d997d3f56`;
`run/stratified-bounds.json` SHA256
`27a342b11674c4d76f2d2ad8c176f67cf9d6dfc219a5eb3b14cc61e27e8aafea`;
`results/dev_aux/task2629/REPORT.md` SHA256
`ae86bc76e3a12c0fdf0e4c4ef05e46019b4428ec2c9d02d8ce9a8561d64c735`.
