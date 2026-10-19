# task2610 attempt 2 — Second finite root-panel evaluation

## Design and provenance

Evaluation-only second root panel using task2607 pre-outcome-classified roots. The frozen task2606 model result and outcome-blind task2607 selection were reused unchanged. The frozen four-ply prefix and root manifest are byte-identical to the registered plan. Each selected root's complete GameSession record (ruleset fingerprint plus four actions) was preflight-replayed before any evaluation record was written.

- Registration: `5c21875097d4107d900591d0e2544e42f8fe88c00a78ce9f689fdd112b3e5484`; root manifest: `042ef4ad447f63837c4a502ae05c7f640234e5c2906ac48ccb8b8540e9f08ca3`.
- Slots: 1536/1536; distinct roots: 64/64; runtime: 702.419s; nodes: 2,201,293; queries: 39,958.
- Actual terminal outcomes: 1437; horizon/other UNKNOWN: 99; incomplete searches: 0.
- All outcome records and query ledgers reconcile by slot; each final history and claimed terminal was replayed through the Generic rule runtime.

## Outcomes (learner perspective)

| Endpoint | Wins | Draws | Losses | UNKNOWN |
|---|---:|---:|---:|---:|
| initial | 234 | 8 | 244 | 26 |
| TD95 | 297 | 2 | 174 | 39 |
| LocalLambda | 299 | 5 | 174 | 34 |

Paired reward differences give every pair containing UNKNOWN the full [-2,+2] range; exact pairs use their observed reward difference.

| Contrast (left − right) | Exact pairs / 512 | UNKNOWN pairs | Mean difference bound |
|---|---:|---:|---:|
| TD95 − initial | 458/512 | 54 | [0.0469, 0.4688] |
| LocalLambda − initial | 458/512 | 54 | [0.0195, 0.4414] |
| LocalLambda − TD95 | 450/512 | 62 | [-0.2441, 0.2402] |

## Interpretation and limits

This is attempt 2 after a schema-only registration repair; attempt 1 remains a preserved pre-output failure. The frozen task2606 models were evaluated on the second exact-start-history-disjoint root panel; no model or parameter selection was performed using these outcomes. UNKNOWN was not converted to a draw.

The selected roots are disjoint from the 512 possible task2606 training-family start records, but descendants are not proven disjoint and task2606 training trajectories are not an independent generalization guarantee. Therefore this is a finite, fixed-model diagnostic panel, not a fully independent holdout or evidence of broad Generic transfer. The 99 UNKNOWN outcomes widen comparisons; LocalLambda's comparison with TD95 remains unresolved whenever its bound includes zero.

The runner and audit code are task-specific evidence tools; they do not change engine defaults, UI, or primary checkout.
