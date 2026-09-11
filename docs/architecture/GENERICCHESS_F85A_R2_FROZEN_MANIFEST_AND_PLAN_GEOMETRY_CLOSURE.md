# GenericChess F85A-R2 Frozen Manifest and Plan Geometry Closure

F85A-R2 closes the manifest and planning-geometry corrective for the C2 teacher
acquisition harness. It performs zero teacher calls, zero Heavy work, zero C2
fitting, zero Arena/self-play, and zero root resampling.

## Frozen authority

The tracked `train_precompute_manifest.json` remains byte-for-byte unchanged.
It still contains the 36 train roots (12 in each required stratum), frozen
positions and roles, replay-derived legal-action counts, per-root declared node
ceilings, and total declared node ceiling `15,426,000`. Its F83 root-set,
F84 calibration, C1, and F59/F62 teacher-contract bindings are unchanged.

The manifest is intentionally bound to the immutable precompute source
checkpoint `e54ff4f9ca05ee3eb33a9a693d8577a99992b991`, rather than to the later
closure commit. The precompute command validates the existing manifest against
that source binding and refuses to rewrite it if any byte or derived value
differs.

## Authorized execution geometry

The only authorized large-plan geometry is:

- two concurrent train-root lanes on the declared 16-logical-CPU host;
- one stage, 720 seconds per-root wall cap;
- expected wall 110 minutes, planning range 95–125 minutes, hard wall 240 minutes;
- expected CPU 8.5 hours, hard CPU 15 hours;
- effective games, Arena pairs, and plies all zero;
- total declared node ceiling `15,426,000`.

Three- and four-lane values remain unvalidated diagnostic projections from the
F84 measurements. They are not approvals or fallbacks. The approved-run path
rejects any envelope whose intended lane count is not exactly two, before any
teacher runner is invoked; the same validated value controls batch width.

## Resumability and clean-checkout guarantees

Progress remains namespaced by the exact plan SHA. Each unit binds the exact
plan, manifest, root record, root identity, C1 checkpoint/model, and F59/F62
script hashes. Any stale COMPLETE unit is rejected as
`STALE_PROGRESS_PROVENANCE`. TIME_CAP and HARNESS_MISMATCH are terminal for the
plan and persist no teacher rows; same-plan re-entry returns
`RETRY_REQUIRES_NEW_AUTHORIZATION`. A terminal result stops later batches, and
sealed training evidence is possible only after provenance-bound 36/36 COMPLETE
units.

The contract tests create their own minimal plan files and operating-system
temporary runtime directories. They do not rely on ignored `.generic_chess_flow`
plans or runtime state, and they cover every provenance binding, exact two-lane
validation, both terminal first-batch outcomes, same-plan non-retry, and 36/36
sealing.

## Classification

`C2_TRAIN_TEACHER_ACQUISITION_HARNESS_READY_FOR_LARGE_APPROVAL`

This classification means the harness and frozen plan are ready for separately
bound scientific and Supervisor approval. It does not authorize acquisition.
