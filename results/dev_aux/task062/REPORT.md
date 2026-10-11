# Task062: preserve warmth versus schedule full-q4

Twelve predeclared actual calls on the same32-entry ChessEP baselineD2 TT distinguish clearing from scheduling. Every arm gets identical TT input and fixed128/512/1024 node caps, q4/hard8/maxD4. All stop by node limit with balanced full Runtime restoration and positive Native legality calls, no fallback/failure. One seed uses1505visits; measured calls6656visits/5.329s, batch7.190s. No equal-time/strength claim.

|Node cap|Baseline|Full-q4 clear|Full-q4 phase_bypass|Existing skip_warm_root, full-q4 source|
|---:|---|---|---|---|
|128|D2/score8|D1/score8|D1/score106|D2/score8|
|512|D2/score8|D1/score17|D2/score8|D2/score8|
|1024|D2/score8|D1/score17|D2/score8|D2/score8|

All three prototype sources replace only the original refreshq1 limit with configuredq4; source hashes and selection logs are stored per row. Clear discards the old table before/after refresh. Phase_bypass disables TT in cheap reserve/refresh and preserves configured-q entries for deeper iterations: it recovers D2 only once its fresh shallow work fits. At128 it changes the action as well as score, so preservation alone is insufficient. Existing skip_warm_root detects an eligible EXACT depth2 root and selects ordinary iterations without a refresh; all three selection logs say skip=true. This is a routing observation under one acquired table, not acceptance for arbitrary histories, roots or cache semantics.

Depth2 with a cached score and empty PV is a selective result, not a fresh finite-horizon proof. The comparison supports a precise opportunity-cost mechanism and possible scoped routing control, not blanket adoption/default promotion. The cold promotion loss from Task061 is outside these warm-root controls and remains unresolved here. No user label/teacher fit or new rule cohort was added.

The first invocation omitted the inherited binary hash metadata and stopped before seed/search; that harness failure is documented. Source/cases/caps remained unchanged. Primary104 cold timed records remain valid in their declared domain. The auxiliary does not alter primary scheduling or merge this prototype.
