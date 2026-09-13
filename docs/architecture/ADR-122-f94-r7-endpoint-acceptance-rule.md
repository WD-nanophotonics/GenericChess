# ADR-122: F94 R7 primary endpoint acceptance rule

Status: Frozen prospective design.

## Decision

R7's sole blocking primary endpoint is `4096_vs_256`, evaluated over the 18
complete pair observations from three fresh tapes with six pairs per tape. A
pair is the sampling unit; individual games are never resampled or treated as
independent observations.

The positive-direction gate requires both a mean pair score strictly greater
than `0.5` and a strict majority of child-better pairs over child-worse pairs.
Ties are retained but do not count as positive evidence. Missing, duplicate,
or incomplete pairs fail closed.

The confidence gate is the existing deterministic nonparametric bootstrap of
pair means with confidence `0.95`, `10,000` resamples, seed `271828`, and the
lower percentile index `250` (`alpha = 0.025`). Acceptance requires the
recomputed lower bound to be strictly greater than `0.5`. Any blocking fallback
or identity/source digest failure takes precedence and prevents acceptance.

## Consequences

The rule is prospective and zero-compute: it authorizes neither Arena nor
Heavy execution, changes no classifier, and cannot reinterpret immutable R6
`DEFER_CONTROL_NOT_READY`. A complete result that fails any gate is reported as
`DEFER_PRIMARY_ENDPOINT_UNRESOLVED`; it is not converted into a promotion or
Layer-D authority decision.
