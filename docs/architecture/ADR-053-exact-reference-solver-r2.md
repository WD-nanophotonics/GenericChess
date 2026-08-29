# ADR-053: Exact reference solver R2 capability audit

## Status

F23L completed with sound proof-window and capability-v3 verification. The
solver still cannot certify the five fixed independent F23J representatives
within the meaningful frozen ladder, so the next boundary is
`F23M_EXACT_REFERENCE_SOLVER_FOUNDATION_R3`.

## Proof-window and TT contract

The V2 solver now uses a full proof window outside the value domain
`LOSS=-1`, `DRAW=0`, `WIN=+1`: recursive root-action searches use
`alpha=-2, beta=+2`. A fully searched WIN or LOSS is therefore exact even when
it is an extremal game value. Unresolved descendants still write no TT entry;
complete typed entries remain safe, and TT-disabled differential mode produces
the same root values and complete optimal sets on the fixed oracle cases.

Authoritative horizon mode remains `max_depth=None`, derived from compiled
RuleSet `max_ply - state.ply_count`; explicit integer depth is only a bounded
diagnostic mode. Full state/history identity is retained because no compact
history equivalence has been proved for every supported repetition policy.

## Capability-v3 result

The same five non-control F23J representatives were tested without substitution
using the predeclared SMALL/MEDIUM/LARGE ladder of 2,000 / 20,000 / 100,000
nodes, authoritative horizon mode, and an 8-second per-attempt process cap.
None resolved. All five were classified as `BRANCHING_EXPLOSION` after the
fixed ladder/time safety contract. No budget was increased after observing a
result, no V7 corpus was created, and no evaluator or production path was
touched.

The capability gate therefore remains false, while correctness gates pass:
legacy differential parity is zero-mismatch, full WIN/DRAW/LOSS root-action
exactness is tested, unresolved paths refuse certification, and V1–V6 plus
capability-v1/v2 remain byte-identical.

## Decision

Continue with F23M solver-foundation R3 to address branching and semantic
successor cost. Do not start another corpus phase, relax exact certification,
or treat the time-capped capability rows as solved labels.
