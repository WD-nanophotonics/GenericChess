# F94 R7 endpoint acceptance rule repair closeout

## Immutable successor

- Repository: `GenericChess-sandbox`
- Sandbox commit: `99d8c9d5c33df080497c3a8d0e10eb3e1bc5fbf9`
- Repaired artifact: `docs/architecture/GENERICCHESS_F94_R7_PREREGISTRATION_V1.json`
- Endpoint rule: `docs/architecture/GENERICCHESS_F94_R7_ENDPOINT_ACCEPTANCE_RULE_V1.json`
- Frozen preregistration SHA256: `0bb5b352ab027e818d6dede058ff9d543b8f8c643b4805fa642783ec68c00237`

## Repair

The successor restores the preregistration byte-for-byte to the previously
accepted `5401bfde2d7ff728c991ca457c24b5b4b75a96e8` content. The endpoint rule
test now recomputes the preregistration SHA256 from the checked-out bytes and
fails closed if the rule's parent binding drifts. No endpoint threshold,
positive-direction rule, confidence method, or R6 authority was changed.

## Verification and boundary

The focused zero-compute R7/R6/arena regression set passed 42 tests through the
publish gate. The rule remains prospective: no Arena or Heavy run is
authorized, no classifier is mutated, and immutable R6
`DEFER_CONTROL_NOT_READY` is not reinterpreted. Any integrity or endpoint gate
failure remains `DEFER_PRIMARY_ENDPOINT_UNRESOLVED`.
