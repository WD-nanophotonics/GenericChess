# Partial goal intervals for frozen action-choice auditing

Frozen before implementation/control runs, 2026-10-04. This changes validation
units, not candidate coefficients or the failed service-count contracts.

For each nonterminal root, freeze a candidate and baseline's chosen complete
legal choice IDs before goal observation. Include Session claims; board moves
alone are not a complete choice set. Give every choice an independently sound
owner-zero WDL interval. Convert to root-owner units: owner1 negates and swaps
endpoints. Missing, interrupted and RESTART choices retain [-1,1]. Never select
a different action after reading labels. No new real-game corpus is admitted.

For selected a, regret is max_b V_b - V_a. It is nonnegative because the choice
set includes a. Bounds excluding a avoid fictitious independent copies of its
value: lower=max(0,max_{b!=a} L_b-U_a), upper=max(0,max_{b!=a} U_b-L_a).
A singleton has regret0. These bounds are exact for the interval box; actual
game correlations may narrow the box but cannot invalidate containment.

For frozen candidate a and baseline c on the SAME root, the regret difference
R_c-R_a equals V_a-V_c: the common optimum cancels. Its sound interval is
[L_a-U_c,U_a-L_c]; if IDs coincide, it is exactly0, regardless of label width.
Use this paired difference, not separate regret extrema, to certify a frozen
weighted population's additive margin. Nonnegative rational weights sum to1.
The independently declared required improvement delta must be positive. If the
lower weighted margin >= delta, certify improvement; if upper < delta, certify
failure to meet that margin; otherwise inconclusive. Failure need not mean
candidate is worse. Root tolerance similarly distinguishes pass/fail/unknown.

Controls: exact winning selected action with unknown alternatives, proven loss
against draw/unknown, singleton, both owners, identical choices, all unknown;
exhaustive rational tiny interval boxes independently enumerate completions
and check regret extrema/paired differences. Reject missing selection, empty
choice sets, nonrational or out-of-range intervals, malformed owners/weights.
No time padding, public board expansions or new material values are needed.

This is decision-use evidence only. It cannot derive a relative vector or
choose deployment roots, horizons, mixed evaluator units or a prior formula.
Existing ROOT_DECISION_IDENTIFIABILITY.md remains applicable. Construction
assumptions, semantics/cost and independent deployment validation are separate.
