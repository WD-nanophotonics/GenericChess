# GenericChess F87A-R9 Western Dynamic Discovery Closeout

- Baseline: `178b06b04e1ee47f03fe12688ca6067e75721135`
- Scope: a small ruleset-agnostic dynamic terminal-discovery control after the R8 witness.
- Policy: existing `canonical_common_tape_random`, with three fixed seeds, one role-swapped pair per seed, and a 256-ply horizon.
- Prohibited: Western-specific opening, hand-authored mate tape, external engine, training, Arena, and Heavy.

## Result

The production semantic runtime discovered one `checkmate` in six role-swapped
games across seeds `9011`, `9012`, and `9013`; the other five trajectories
reached the bounded 256-ply horizon and were reported as `CENSORED`. The policy
uses only canonical legal-action ordering and seeded common tapes, so this is
dynamic discovery evidence rather than the R8 solution tape.

Under the existing R6 termination-viability gate, the result is a PASS for the
Western termination subgate: at least one legal terminal trajectory was found
and search-budget censorship was zero. The five horizon-censored trajectories
remain a bounded-coverage indicator (`HORIZON_ONLY`), not a rejection of
termination viability. This does not authorize training or promotion: F87A
overall remains `HOLD` because paired-strength and learning/evaluator gates are
still deferred.

## Evidence

- Manifest SHA-256: `19abaf84ebe35f196004f7ad38f2e22d0047e8657cec2c869ddf826543226ecc`
- Results SHA-256: `fc9552f8177cc17d156fd5b311a56f4f243c21203313515c6c6910f41661516c`

R9 reconciles the generic dynamic checkmate with the existing termination gate:
Western termination is `PASS`, while the broader F87A qualification remains
`HOLD`.
