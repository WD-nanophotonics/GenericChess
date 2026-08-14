# F18 Evidence — Native Semantic Position-Key / History Hot-Path

Status: `AUDIT_ONLY_PASS`.

The complete authoritative Gmail attachment and provenance are preserved in [the F18 inbox record](../../inbox/2026-08-14_GenericChess-F18_Native_Position_Key_History.md).

## H18A baseline

The initial hard lock passed at F17 closure commit `4999be31b6fc91655d7d0df9c948ef3bbdb43408`; `origin/master` remained `4f1d03a308f5fd04a01bbd980c7411888ea1ed9d` and `origin/chat` remained `d6b0d5720efe23019a7a2b4cce72e05beee2e6c4`. The old Native key matched the Python canonical SHA-256 oracle over 196 frozen positions with zero mismatch.

The old already-packed public key median was 15.39µs in the baseline run, and the nested `make_checked` median was 30.01µs. The measured key value is a nested public-key measurement, not an exclusive internal cost claim.

## Candidate and authorization

H18A built a test-only candidate with immutable canonical ordering metadata, chunked exact canonical serialization, direct raw SHA-256 output, and raw-digest/direct-history versus hex-history probes. Candidate parity passed: 196/196 rows matched Python and old Native digests, including four Standard Shogi roots, depth-1/depth-2 children, and the generic corpus.

The candidate did not clear the frozen authorization gates. The best recorded candidate public-key median was 11.39µs versus the same-run baseline 13.56µs (1.19×, required >=1.67× / <=0.60×). The raw-digest/direct-history stage was 1.19× versus the required 1.20×. Therefore G2 and G3 failed.

## Closure

`H18B_CREATED = false`. The candidate source and test-only APIs were removed before final closure; no Native key/history optimization, F15 mirror, F16 runtime, F17 delta runtime, attack/check routing, legality routing, terminal routing, evaluator routing, or Native search was retained.

The selected next boundary is `NATIVE_POSITION_KEY_ARCHITECTURE_REASSESSMENT`. F18 does not implement it and does not begin F19.

See [ADR-035](ADR-035-native-semantic-key-history-hotpath.md) and the machine-readable evidence under `artifacts/f18_native_position_key_history/`.
