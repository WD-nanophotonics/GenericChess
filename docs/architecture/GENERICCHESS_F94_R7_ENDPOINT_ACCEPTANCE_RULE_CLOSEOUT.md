# F94 R7 endpoint acceptance rule closeout

## Immutable checkpoint

- Repository: `GenericChess-sandbox`
- Sandbox commit: `3d012e2c4edc4a9babfad2bc52d8df67912a6ace`
- Parent preregistration: `docs/architecture/GENERICCHESS_F94_R7_PREREGISTRATION_V1.json`
- Parent preregistration SHA256: `0bb5b352ab027e818d6dede058ff9d543b8f8c643b4805fa642783ec68c00237`
- Endpoint rule: `docs/architecture/GENERICCHESS_F94_R7_ENDPOINT_ACCEPTANCE_RULE_V1.json`

## Frozen prospective rule

The blocking endpoint is `4096_vs_256` over 18 complete pair observations
(three tapes, six pairs per tape). The positive-direction gate requires a mean
pair score strictly above `0.5` and strictly more child-better than
child-worse pairs; ties do not count as positive evidence. Missing, duplicate,
or incomplete pairs fail closed.

Confidence is the deterministic pair-level nonparametric bootstrap: 95%
confidence, 10,000 resamples, seed `271828`, lower percentile index `250`,
and acceptance only when the lower bound is strictly above `0.5`. Blocking
fallbacks, identity drift, source/PREP/protocol/preregistration SHA drift, or
timing-dependent calculations fail closed.

## Verification and boundary

The focused R7/R6/arena regression set passed 42 tests through the publish
gate. This is zero-compute design work: it authorizes no Arena or Heavy run,
changes no classifier, and cannot reinterpret immutable R6
`DEFER_CONTROL_NOT_READY`. A result failing any gate remains
`DEFER_PRIMARY_ENDPOINT_UNRESOLVED`.
