# Task006: restoration oracle sensitivity to occurrence values

Independent DEV_AUX audit of its own Task001 validation claim, not product change.
Source inspection finds that original snapshot used tuple(repetition_counts):
it compares keys, whereas count values remain in a mutable occurrence structure.
Persistent _snapshot equality is also checked, but is a separate field.
A value-only corruption with stable keys may evade that specific old oracle.

Predeclare one ten-ply exposed Chess root. AST-load the original snapshot
function without running its old experiment. Record both original oracle and a
stronger value-bearing oracle. Plant one private occurrence-count increment at
the current root, keeping Position/hash/history/snapshot/context/keys unchanged.
Require the original oracle to miss that planted change and the stronger oracle
to catch it, then remove the sentinel and require exact restoration.
This is an audit-helper mutation, not evidence that product code corrupts counts.

Separately repeat the four original failure seams (transition/component_diff/
snapshot/terminal) once per plain/instrumented arm using the stronger oracle.
The premise and question change: directly check actual count values rather than
the old key-only claim. Keep the original Task001 output/producer untouched and
retain the correction. No completedD2/timing rerun, defaults change or primary
edits. Eight short pushes plus one sentinel, all bounded under60seconds.
Work after the third primary five-minute time slot ends; source/report work first.
If an actual restoration mismatch appears, retain it and isolate that one case.

## Source refinement before the oracle run

Further source reading shows repetition_counts at depth0 returns the external
compatibility projection. Even adding .items() to that root projection does
not directly observe the private table used by terminal search. Refine the
strong oracle to collect actual _occurrences hash/identity/count triples,
independently of _snapshot and external counts. Keep old and naive-value
oracles too so their blind spot is observable. No test has run yet.
Source also suggests a specific post-occurrence/pre-history failure:
rollback removes the added occurrence without a history record only when a
bridge_key exists. A snapshot exception without a bridge may leave an extra
entry despite all root projections matching. The fixed eight-seam batch will
report mismatch rather than assert that all product restoration must pass.
