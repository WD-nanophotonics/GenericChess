# GenericChess F81-R2C-R1: durable decision-bound corrective

Status: `PARENT_ANCHORED_FULL_RESIDUAL_FINAL_CONFIRMED`.

This is a zero-compute provenance and contract correction after R2C. It does
not change the scientific conclusion, champion transition, canonical decision
bound, or cancelled pair-5 compute. No Arena game, Heavy job, training run,
self-play, opening generation, candidate mutation, or production semantics
change was performed.

The durable bound now records the exact R2A checkpoint/path/SHA tuple, the
time-cap audit path, and the derived mean gate margin
`0.53125 - 0.5 = 0.03125`. The canonical evidence binds the exact SHA-256 of
`artifacts/f81_final_confirmation/final_decision_bound.json` rather than only
its path.

The contract test now reads the time-cap audit rows, excludes only contaminated
pair 5, reconstructs the seven clean pair scores and `3/3/1`
better/tied/worse counts, recomputes the worst-case mean and `0.03125` margin,
and verifies the worst-case `3/3/2` count. It also verifies the R2B report
hash, R2A provenance tuple, durable-bound hash pointer, physical completion of
7 pairs, and the continued diagnostic-only status of the old pair-5 score.

F81 remains closed by the worst-case decision bound: the final strength gate
is forced for every legal replacement outcome, and pair-5 corrective compute
remains `CANCELLED_NO_DECISION_VALUE`.
