# ADR-047: Decision-subtree diversity correction

## Status

F23G corrective R1. V4 remains historical evidence and is immutable. No
production evaluator/search/Native behavior, V1/V2/V3 fixture, or rejected
F23F candidate specification changed.

## Finding

The V4 physical deep stratum has 30 rows and 30 canonical state identities,
but the new behavior-only recursive fingerprint finds only five effective
decision orbits. Each orbit has multiplicity six: its rows differ only in
non-droppable D hand counters, which do not change legal actions, W/D/L values,
reachable proof tree, terminal outcomes, or proof depths.

Four of the five orbits occur on both the frozen DEVELOPMENT and HOLDOUT
assignments. This is `DECISION_ORBIT_SPLIT_LEAKAGE`; those orbits are excluded
from future validation accounting rather than being used on both sides. The
corrected counts are:

- physical rows: 30;
- canonical state identities: 30;
- effective orbits: 5;
- effective DEVELOPMENT/HOLDOUT before leakage exclusion: 5/4;
- eligible effective DEVELOPMENT/HOLDOUT after exclusion: 1/0;
- effective proof classes: 5 `MULTIPLY_DEPENDENT`, 0 max-ply-dependent;
- duplicate multiplicity: six rows per effective orbit.

A changed B-piece location produces a different decision fingerprint, proving
the audit distinguishes a real reachable-reply change from inert identity
perturbation.

## Decision

Do not count the V4 rows toward evaluator fitting or validation. No corrected V5
corpus is added in this checkpoint because the current effective coverage is
insufficient and the next work must construct genuinely distinct decision
subtrees, not manufacture more rows around the same five structures.

Select exactly `F23H_REFERENCE_PREFERENCE_CORPUS_R3`. That phase must add real
branch, outcome, mechanic, or proof-horizon diversity and apply the behavioral
orbit/leakage gates before any evaluator prototype is authorized.
