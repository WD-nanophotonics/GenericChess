# GenericChess F76-R2 Durable Candidate Identity Corrective

## Decision

R2 repaired the durable training identity without changing the evaluator.
The result is `POINTWISE_OUTPUT_DELTA_DURABLE_IDENTITY_REPAIRED`.

The R1 candidate remains preserved as historical evidence and is invalid for
selection because its descriptor hash did not match the actual training hash
carried by its checkpoint. R2 created a separate canonical artifact and did
not run Arena, self-play, external-engine comparison, seed sweep, Heavy, or
promotion.

## Identity repair

- Work order: `GENERICCHESS-F76-R2-DURABLE-CANDIDATE-IDENTITY-CORRECTIVE`
- Baseline: `0a77db47c59b6f792b035d1e08f5e915e385d208`
- Parent checkpoint: `d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4`
- R1 checkpoint retained as historical: `140daa82ba60d5dee82a9212a679834f3c19919c43bf30704feb51c87fd1c324`
- R2 checkpoint: `fb3d3113b7044de6ebbf17352d7e34f0713618afbaae6eb792ebb515b09f30db`
- R2 artifact: `artifacts/f76_r2_trusted_pointwise_q/candidate.json`
- Canonical training hash: `56b7bb64f20a5f31fd3056aa6743071d80daaa550a1b1341a8d56662100b454f`

The canonical identity binds the R2 work order, parent checkpoint, F62 stage
SHA, F62 records SHA, fit method, regularization, ordered trusted-root
indices, raw delta, and alpha. The same identity object is hashed once and
that hash is used both in `child_checkpoint(training_config_hash=...)` and in
the durable descriptor.

The old R1 descriptor hash was
`c4a9e428498c36cbe104b1995775a1097ba32d6fb3b26086f0b0d2ddc7cf361f`; the
actual R1 checkpoint hash was
`ee3d16b950c0f20ac8b49d936dd567116fc4b9383f25ccd4896a6389ed167d43`.
They differ, which is the recorded reason R1 is
`INVALID_FOR_SELECTION_DUE_TO_DURABLE_TRAINING_IDENTITY_MISMATCH`.

## Evaluator equivalence

R2 reconstructed the same trusted pointwise fit as R1: 34 trusted roots with
246 action rows, raw delta norm `11.891430165435105`, alpha
`0.7466487291141266`, and the same final 32 output weights. The evaluator
model SHA is
`318ba6ce996f99ae569d487d8b221675ebb13ccc123ab5a2c1c07effd0879893`.

The R1 and R2 compact evaluator payloads are byte-for-byte equal; only the
training provenance hash and resulting checkpoint identity differ. R2’s
eight Native/Python fixed-point residual-delta checks were exact, and the
candidate retained the Gen1 ruleset and frozen representation bindings.

## Metadata-only search parity

Using the same 20 stable development roots, fresh engines, 2,048 nodes,
maximum depth 12, 8 MiB TT, qsearch 0, no root hint, and product
`root_window_pruning=True`, R1 and R2 were each repeated once per root.
All action, score, completed-depth, termination, and repeatability fields were
exact across all 20 roots. No search parity failures occurred.

The inherited diagnostic remains unchanged: 10/20 decision changes relative
to the parent, toward/away/lateral `0/1/9`, and parent/child deep agreement
`2/1`. These are historical deployment diagnostics only; R2 does not authorize
Arena2.
