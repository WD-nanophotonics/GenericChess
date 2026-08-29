# ADR-050: Independent-mechanic preference corpus R4

## Status

F23J completed as a failed corpus gate. V6 is a durable evaluator-blind
attempt and refusal audit; it is not fit data for an evaluator prototype. The
next boundary is `F23K_EXACT_REFERENCE_SOLVER_FOUNDATION`.

## Frozen plan

The plan was encoded before solving or split inspection: six construction
families, six candidates per family, fixed parameter order, fixed DEVELOPMENT /
HOLDOUT labels, source-family identifiers, and solver limits. Five families
reuse existing GenericChess public fixtures for ordinary anchor movement,
capture/recapture, drops/hands, promotion, and semantic guard/auxiliary
behavior. One explicitly labelled auxiliary reply-chain control family is
retained only as a control and is not evidence of independent construction
diversity.

Non-control candidates use a bounded 2,000-node / depth-2 solver probe because
the existing fixture positions have broad ongoing branches. The control uses
the already validated 30,000-node / depth-6 exact contract. These limits are
part of the frozen plan; unresolved branches are rejected, never guessed.

## Result

V6 planned 36 candidates. Six physical candidates solved strongly, but four
were behaviorally identical control variants and collapsed. Thirty candidates
were unresolved under the exact reference contract. The resulting effective
set contains one DEVELOPMENT orbit and zero HOLDOUT orbits, all from the
related auxiliary control family and all `MULTIPLY_DEPENDENT` with a DRAW/LOSS
root partition. No independent construction family contributed an eligible
orbit.

The plan includes a deliberate sibling-source example: one control candidate
is DEVELOPMENT and another is HOLDOUT under the same `source_family_id`. That
source family is explicitly excluded from validation accounting. Historical
V1–V5 and F23F artifacts remain separate and byte-identical.

## Decision

The V6 advancement gate fails the required effective counts, independent
construction/mechanic coverage, and validation availability. No evaluator
features, ADR-040 values, F23F/F23I coefficients, Shogi, or AlphaSho were
inspected. Do not fit an evaluator or open HOLDOUT in F23J.

F23K should address the exact reference-solver foundation needed to solve
genuinely different finite mechanisms, with explicit tests for promotion,
drop/hand, capture/recapture, semantic guards, transpositions, and refusal of
cycles/caps. It must not backfill V6 labels or relax strong-certification
rules.
