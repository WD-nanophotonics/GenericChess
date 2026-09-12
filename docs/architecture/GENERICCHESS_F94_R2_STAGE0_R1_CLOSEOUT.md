# GenericChess F94-R2 Stage-0 R1 integrity repair closeout

Status: the Chat-requested Stage-0 integrity repair is complete and published;
no Arena or Heavy computation has run.

## Repairs

`run_stage0()` now fails closed before rebuilding candidates or invoking Arena
when the source PREP file hash differs from the staged
`source_prep_artifact_sha256`, or when the source PREP's
`source_sandbox_sha` differs from the staged frozen source binding.

Stage-0 status reduction now obeys the frozen precedence
`DEPTH_CENSORED > FALLBACK > OPERATIONALLY_UNRESOLVED > direction`, including
combined-condition handling across tapes. Operational failures are retained as
explicit unresolved tape evidence rather than being treated as draws.

The independent Stage-0 PREP, opening-index-0 selection, 4096-vs-256 scope,
workers=1, six invocations/twelve games, boundary compute-zero short-circuit,
and separate non-authoritative result schema are unchanged.

Focused Stage-0, strength-response, and F87A tests pass (24 tests). The exact
Stage-0 command and PREP path remain the ones recorded in
`GENERICCHESS_F94_R2_STAGE0_EXECUTOR_CLOSEOUT.md`.

## Next boundary

After this repair checkpoint is published, regenerate the small/medium
resource envelope and versioned compute plan against the exact current SHA and
command. Chat and the registered Supervisor must review/bind that tuple before
the sole Stage-0 Heavy run. Stage 1 and the original full F94-R2 schedule are
not authorized by this closeout.
