# GenericChess F81-R2A: fail-closed evidence invalidation

Status: `PARENT_ANCHORED_FULL_RESIDUAL_FINAL_CONFIRMATION_UNRESOLVED`.

This zero-compute corrective updates the canonical F81 evidence after the
F81-R1 audit found a Native `time_budget` cap-contract mismatch in pair 5. No
Arena game, Heavy job, training run, or corpus generation was performed.

The canonical artifact
`artifacts/f81_final_confirmation/final_strength_evidence.json` now has schema
`generic-chess-f81-final-strength-evidence-v2-pending-corrective`, classification
`PARENT_ANCHORED_FULL_RESIDUAL_FINAL_CONFIRMATION_UNRESOLVED`, and content SHA
`e6ed1819a51cc6ae8e16167a42788786548e5a955679ae261910a7d9cf591a25`.

The prior F81-R1 report and confirmed artifact remain bound as invalidated
diagnostic history:

- report SHA: `9273856d350f9e9a6b94eecba251baaf4fd4275f70d8ddeb82ed39f493ad851a`;
- artifact SHA: `dc769e52c7d5d6357fabfb640c88a51ab3b0600b9c97aec8919c810b7d25e938`;
- invalidation: `INVALIDATED_BY_TIME_BUDGET_CAP_CONTRACT_MISMATCH`.

The audit remains bound to
`artifacts/f81_final_confirmation/f81_r1_time_cap_audit.json` with content SHA
`1c418b509654f4f054db738720880bf4435e611bd2cba589b4018d78a2c961a6`.
Clean pairs `[0, 1, 2, 3, 4, 6, 7]` and their 14 games are retained as
diagnostic evidence; contaminated pair `[5]` is excluded and is the only
pending replacement pair. The old eight-pair scores are retained only under
`invalidated_diagnostic_scores` and are not authoritative.

Both `champion_before` and `champion_after` are the Gen1 parent
`d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4`.
The fixed child remains a candidate pending a corrected final confirmation.
