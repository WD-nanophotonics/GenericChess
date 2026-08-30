# ADR-069: F23V final admission correction

## Status

Accepted final diagnostic checkpoint; no production integration or promotion
is authorized. No third F23V corrective cycle is permitted by the work order.

## Context

F23V first pass used dormant K/R roots. R1 corrected the evaluator measurement
contracts but incorrectly used a four-second wall and rejected any search that
globally visited MAX_PLY. The final corrective work order required one Phase-A
rerun on the same frozen R1 plan with the established eight-second wall.

## Decision

R2 adds only admission/preflight diagnostics. It uses 100,000-node V3 and
abstraction limits and an exact eight-second isolated wall per attempt. V3
nontrivial roots always run abstraction; global MAX_PLY visitation is retained
as a diagnostic and is not an admission veto. Admission requires only strong
abstraction plus exact action W/D/L and optimal-set equality with V3.

The five-feature R1 evaluator and all first-pass/R1 artifacts remain unchanged.
No replacement plan is constructed unless Phase A passes both admitted-count
and admitted-mechanic viability gates. The frozen R1 plan is structurally
preflight-invalid because SHOGI promotion-active planned coverage is 2 rather
than 3 and MIXED drop-active coverage is 0.

## Result

Phase A ran abstraction for 20 strong V3 nontrivial roots. Four abstraction
certifications had nonzero MAX_PLY visitation diagnostics and remained strong,
proving that global visitation is not proof dependence. Refusal decomposition
is retained in the R2 signal fixture. Corrected admitted roots were SHOGI 0,
WESTERN 1, and MIXED 3; no group reached the required six, and admitted
mechanic coverage also failed. Execution stopped at Phase A with
`INSUFFICIENT_MECHANIC_ACTIVE_EXACT_COVERAGE`.

## Consequence

The exact-supervision route is retired as the default validation mechanism for
this mechanic-active evaluator experiment. No scoring metrics, transfer claim,
replacement plan, or F23W shadow was started. The selected final boundary is
`F23W_EVALUATOR_SUPERVISION_STRATEGY_REASSESSMENT_R2`; the R2 checkpoint closes
F23V without promotion.
