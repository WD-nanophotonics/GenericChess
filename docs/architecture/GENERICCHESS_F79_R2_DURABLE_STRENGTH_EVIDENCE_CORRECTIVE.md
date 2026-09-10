# GenericChess F79-R2: durable strength evidence corrective

Status: `PARENT_ANCHORED_FULL_RESIDUAL_ARENA4_EVIDENCE_DURABLE`.

This zero-game, zero-training corrective preserves the accepted F79-R1 result
and removes its clean-checkout provenance gap. It does not rerun games, retrain,
change alpha/model parameters, generate openings, or alter production search,
evaluator, or Arena semantics.

## Tracked evidence

- F78 prefix: `artifacts/f78_parent_anchored_full_residual/arena2_strength_evidence.json`.
- F79 aggregate: `artifacts/f79_parent_anchored_full_residual/arena4_strength_evidence.json`.
- F78 source report SHA-256:
  `3f67f1d6c5d4c0c2e23abd84f04c4903479705076e0bb9fd83e8f0ecd5144b3d`.
- F79 source report SHA-256:
  `395080e0132b5c4a0f6c98990bbbcbfb3b07230d185486a52541862ad768886a`.

The aggregate artifact binds its F78 evidence artifact by content SHA and
recomputes the four-pair statistics from the tracked prefix and incremental
pair-score arrays. The R1 harness now consumes the tracked F78 evidence and
validates its source report hash, identities, corpus, opening indices, scores,
and W/D/L instead of reading `.generic_chess_flow` history.

## Retained result

Frozen F78 prefix scores were `[0.5, 1.0]` on source openings `[0, 1]`; the
accepted F79-R1 incremental scores were `[0.5, 0.5]` on source openings `[2, 3]`.
The aggregate is `[0.5, 1.0, 0.5, 0.5]`, mean `0.625`,
better/tied/worse `1/3/0`, bootstrap diagnostic `[0.5, 0.875]`, and combined
W/D/L `5/0/3`, with 8 games and 4 pairs complete. The retained classification
is `PARENT_ANCHORED_FULL_RESIDUAL_ARENA4_SURVIVES`; promotion remains HOLD.

## Clean-checkout validation

The F78, F79-R1, and R2 contract tests validate only tracked repository files
for the prefix and aggregate evidence. The R1 source contains no dependency on
the ignored `f78_results.json`; its runtime namespace remains output-only. The
F78 evidence source report hash is checked against the current tracked report,
and the F79 evidence source report hash is checked against this published
checkpoint's predecessor report as recorded by the signed work order.
