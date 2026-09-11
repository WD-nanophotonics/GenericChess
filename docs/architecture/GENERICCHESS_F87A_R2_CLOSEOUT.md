# F87A-R2 closeout

Work order: `GENERICCHESS-F87A-R2-QUALIFICATION-STATE-AND-CALIBRATION-CLOSURE`

Published implementation checkpoint: `b388e59c9e0038ff7036373ad178eaf9cdf339d6`

Baseline: `7f1f7b5282f22d50c84d15b488ddf5741e9fad4c`

## State closure

The report now distinguishes measurement integrity, calibration expectation, and ruleset qualification state. The single reducer treats any required-layer `FAIL` as overall `FAIL`, while retaining separate PASS evidence for successful measurement and recognition of the frozen expectation.

- F86C legacy V4-3: `A PASS / B FAIL / C DEFER`; frozen F86C authority binds the exact fingerprint, results artifact, stalemate-dominated evidence, and structural reason codes.
- F86I full-reverse V4-3: `A PASS / B FAIL / C DEFER`; frozen F86L authority binds the exact fingerprint and zero complete terminal-template transport under the authorized census.
- F86N-R1 V4-3/V5-3: `A PASS / B DEFER / C DEFER`; structural backbone witness retained without admission.
- Built-in Western Chess/Standard Shogi: `A PASS / B DEFER / C DEFER`; semantic movement is marked `DEFER_SEMANTIC_MOVEMENT`, not heuristically failed.

The shared Layer-B report now retains each opening source’s reachable set size/fraction, SCC component id/size, file span, and owner-relative rank span for both owners and for anchors/ordinary types. F86N’s opening-source, movement-graph, SCC, reachability, and type-profile paths remain thin wrappers over the shared implementation. Owner 0 historical behavior is unchanged.

## Evidence and verification

Generated JSON remains ignored; synchronized local SHA-256 values are:

| Evidence | SHA-256 |
| --- | --- |
| `artifacts/f87a_ruleset_qualification/manifest.json` | `f5b79c8ee0f0a6c5cc89f34f6b999d6f736b3166a0f977a0207be185fe73a0e3` |
| `artifacts/f87a_ruleset_qualification/summary.json` | `7ce6185c6d0ac63f3e22f7e21f5b2c3b287f0548c54898d97a390aed0d88b137` |
| `artifacts/f87a_ruleset_qualification/reports.json` | `6d15bafbb5db40e440269f594a40688ecbd8162735a92165de8806fddd3e0cda` |

The tracked compact ledger is [GENERICCHESS_F87A_R1_CALIBRATION_LEDGER.md](GENERICCHESS_F87A_R1_CALIBRATION_LEDGER.md). Focused verification: `33 passed` across F87A, F86A, F86I, F86M, and F86N tests. Search nodes, Arena games, training steps, and Heavy jobs remain zero. Local `HEAD` and `origin/sandbox` matched the implementation checkpoint before this report commit.

F87B strength ladder remains HOLD; no C2, F85, Heavy, large Arena, or QD/MAP-Elites work was run.
