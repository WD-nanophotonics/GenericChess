# F17 Evidence — Native Delta Semantic Position Runtime + Transactional Undo

Status: `AUDIT_ONLY_PASS`.

The authoritative Gmail attachment is preserved in [the F17 inbox record](../../inbox/2026-08-14_GenericChess-F17_Native_Delta_Semantic_Position_Runtime.md), including message/thread provenance and `complete-authoritative-attachment` processing state.

## Baseline and boundary

The task ran on the sandbox branch from F16 commit `a9c63a02c07376fb61636607cf88f16867bb1cee`. `origin/master` remained `4f1d03a308f5fd04a01bbd980c7411888ea1ed9d`; `origin/chat` remained `d6b0d5720efe23019a7a2b4cce72e05beee2e6c4`. F4–F16 evidence and ADR-022 through ADR-033 were hash-identical before and after F17.

F17 H17A implemented a bounded, test-only transactional delta journal with Strategy B pre-view overlay. The journal was exercised against four frozen Standard Shogi prefixes, the Generic IR-v2 corpus, nested push/pop, invalid-action rollback, underflow, and 81×2 attack/check queries. The raw differential and rollback checks reported zero mismatches on the reachable fixtures.

## H17A measurements

The fresh probe measured `sizeof(GCSemanticPosition)=27296`, `sizeof(GCSemanticUndo)=27296`, and `sizeof(GCSemanticDeltaUndo)=656`. The bounded frame capacities were board 9, hand 10, and auxiliary 24 entries; a depth-512 delta stack is 335,872 bytes. The delta frame passed both size limits: <=2048 bytes and <=10% of the full position.

Action packing passed the >=5× reference gate at 8.84× versus the F15 rebuild reference. The measured Standard Shogi delta push+pop median was 31.39 µs (p90 32.09 µs), versus the required 18.0 µs and the F16-relative ceiling of 17.92 µs. G4 therefore failed.

## H17B decision and cleanup

Because G4 failed, H17B was not authorized. No production SearchPathRuntime, AlphaBeta, legality, terminal, evaluator, TT, or history authority was routed to Native. The temporary delta runtime interfaces were removed before closure; the H17A implementation, probes, and measurements remain preserved as audit evidence only.

The correct next boundary is `NATIVE_POSITION_KEY_HISTORY_OPTIMIZATION`: the delta mutation was bounded and differentially correct, but the SHA-256/history append remains the lifecycle cost center. F17 does not implement that boundary and does not start F18.

See [ADR-034](ADR-034-native-delta-semantic-position-runtime.md) and the machine-readable evidence in `artifacts/f17_native_delta_position_runtime/`.
