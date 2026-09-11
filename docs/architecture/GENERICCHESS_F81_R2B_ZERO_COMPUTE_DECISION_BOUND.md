# GenericChess F81-R2B: zero-compute decision bound

Status: `PARENT_ANCHORED_FULL_RESIDUAL_FINAL_CONFIRMATION_UNRESOLVED`.

This R2B closeout applies the cheapest-sufficient decision procedure to the
single contaminated F81-R1 pair. It performs no Arena game, Heavy job,
training run, corpus generation, or production change. The canonical evidence
remains fail-closed: pair 5 is excluded, the seven clean pairs are retained,
and the old eight-pair result remains diagnostic only.

The retained clean pair scores are `[1.0, 0.5, 0.5, 0.0, 0.5, 1.0, 0.75]`,
with sum `4.25`. For every valid replacement score `x` in `[0, 1]`, the
completed eight-pair mean would be `(4.25 + x) / 8`, whose minimum is
`0.53125`, strictly above the `0.5` mean threshold. The clean pairs also have
better/tied/worse counts `3/3/1`; the worst possible replacement adds one
worse result, leaving `3/3/2`, so better pairs still outnumber worse pairs.

Therefore every valid replacement outcome satisfies the F81 Arena strength
decision. The proposed pair-5 rerun cannot change pass versus reject; it would
only complete the eight-pair convention syntactically. Under the repository's
cheapest-sufficient rule, the rerun has no decision value. Chat should accept
this zero-compute bound or provide an explicit independent long-term
justification for paying the approximately 45–55 minute compute cost for
syntactic completeness alone.

This report does not promote the candidate or restore `FINAL_CONFIRMED`.
Canonical evidence and the pending corrective classification remain bound to
the R2A artifact and audit:

- artifact: `artifacts/f81_final_confirmation/final_strength_evidence.json`;
- artifact SHA: `e6ed1819a51cc6ae8e16167a42788786548e5a955679ae261910a7d9cf591a25`;
- audit SHA: `1c418b509654f4f054db738720880bf4435e611bd2cba589b4018d78a2c961a6`;
- R2A checkpoint: `9dbd5e3e82bdf471d63eb1c13c54f33427c84761`.
