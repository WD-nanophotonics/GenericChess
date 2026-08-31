# ADR-098: F33 R1 retention-gate certification

## Status

Accepted as a corrective audit checkpoint. No production candidate is retained.

## Context

H33A established exact classifier and fixed-result parity for the semantic
checking-action discovery prototypes, but its timing matrix used one fixed-node
run per root and evaluated only the 0.50-second accessibility subset. It also
did not implement Candidate A's authorized fallback retention gate.

## Decision

F33 R1 preserves the H33A manifest and result byte-identically and adds a
separate frozen manifest, three independent fixed-node repetitions per
variant/budget/root, median per-root timing, both required aggregate views,
complete 0.50/2.00-second accessibility components, and Candidate A's fallback
gate. The timing region excludes the independent reference classifier.

Candidate B remains audit-only: its exactness and structural push-reduction
evidence are accepted, but retention requires the repeated >=20% median
per-root improvement gate, no >10% regression at the other budget, and the
complete accessibility gate. Candidate A requires the repeated >=15% fallback
gate or the equivalent complete accessibility gate and is considered only when
B is not retained.

## Result

The corrective result is PASS with `retained_candidate=NONE` and
`next_boundary=F34_QUIESCENCE_BUDGET_ARCHITECTURE`. The published checkpoint has
zero production diff. Full regression retains only the documented 12 Native
F13/F14/F21 compatibility failures and the F24F Kiwipete depth-1 failure
(45 versus 48).
