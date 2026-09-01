# ADR-099: Quiescence budget architecture selection

## Status

Audit-only F34 selection accepted. Production diff remains zero.

## Context

F32 established that the production `quiescence_max_nodes` threshold counts
global qnodes and raises `SearchAborted("qsearch_budget")`. The observed
behavior is MIXED: a cap can abort an incomplete root iteration while an
earlier completed result or root fallback remains available. F33 showed that
removing qsearch classification pushes improves fixed-node work but does not
cross the short wall-time iterative-deepening boundary.

## Decision

F34 evaluated three audit-only architecture families. Q34A tested soft
non-check qnode caps 16, 32, 64, 128, and 256 on the first four frozen roots,
then extended only eligible caps. At a cap hit, ordinary non-check qsearch may
return its bounded stand-pat value; in-check qsearch temporarily bypasses the
optional cap and continues every legal evasion through the unchanged
production path. Caps 16 and 256 were eligible for extension; 256 was the
largest declared cap, but it failed the material accessibility gate.

Q34B tested the parameter-free schedules `min(qdepth, D-1)` and
`min(qdepth, D)`. Q34C reserved ordinary non-check qsearch depth until the
first main iteration completed, then restored configured depth 4. All
candidates passed the frozen tactical safety corpus and no candidate caused a
depth regression on more than two roots.

Q34C is selected because it met the material accessibility gate and has the
narrowest scope: at 2.00 seconds it improved median time to first completed
iteration by 22.42% without new fallback or depth regression. Q34B D−1 also
met accessibility (21.31%), but Q34C is preferred by the predeclared
first-iteration reserve rule. Q34B D and Q34A cap 256 were not materially
accessible.

## Safety and boundaries

The audit covers terminal scoring, declarations, repetition/perpetual-check,
automatic adjudication, max-ply, in-check evasion, hard qsearch depth,
tactical membership, checking/discovered checks, push/pop balance,
cancellation-shaped bounded execution, and opaque generic-history witnesses.
No evaluator, Native path, rule schema, qsearch production set, or configured
qdepth was changed. AlphaSho is descriptive only and was not rerun.

Implementation is deferred to:

`F35_FIRST_ITERATION_QUIESCENCE_RESERVE_IMPLEMENTATION`
