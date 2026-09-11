# GenericChess F81-R2C: decision-bound finalization

Status: `PARENT_ANCHORED_FULL_RESIDUAL_FINAL_CONFIRMED`.

Chat accepted the F81-R2B zero-compute decision bound and cancelled the
pair-5 corrective rerun. No Arena game, Heavy job, training run, self-play,
opening generation, candidate mutation, or production search/Arena change was
performed in R2C.

The seven clean measured pair scores remain `[1.0, 0.5, 0.5, 0.0, 0.5,
1.0, 0.75]`, summing to `4.25`. Pair 5 remains excluded because of the
`TIME_BUDGET_CAP_CONTRACT_MISMATCH`; its invalidated historical score remains
diagnostic only. A legal pair score lies in `[0, 1]`, so the worst completed
eight-pair mean is `(4.25 + 0) / 8 = 0.53125 > 0.5`. Clean
better/tied/worse is `3/3/1`; the worst replacement yields `3/3/2`, still
with more better than worse pairs. Thus the final strength gate is forced for
every valid pair-5 outcome without imputing or accepting that contaminated
pair.

The durable final evidence is
`artifacts/f81_final_confirmation/final_decision_bound.json`, while the
canonical evidence is upgraded to
`generic-chess-f81-final-strength-evidence-v3-decision-bound`. It records
`confirmation_method=ZERO_COMPUTE_WORST_CASE_DECISION_BOUND`, physical pair
completion `7`, decision pair count `8`, excluded pair `[5]`, and
`decision_bound_covers_excluded_pairs=true`. The old R1 scores remain under
`invalidated_diagnostic_scores`; they are not part of the authoritative
aggregate.

The confirmed champion transition is parent
`d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4` to child
`f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4`. This is
an evidence finalization only; promotion to `master` remains separate and
held.
