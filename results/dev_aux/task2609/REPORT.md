# task2609 — Exact-start-disjoint finite evaluation

## Design and provenance

Evaluation-only follow-up to task2608's preserved pre-first-slot runner failure. The frozen task2606 model result and outcome-blind task2607 selection were reused unchanged. This corrected registration explicitly includes the four-ply prefix omitted from task2608. Each selected root's complete GameSession record (ruleset fingerprint plus four actions) was preflight-replayed before any evaluation record was written.

- Registration: `43292987a3e18fa2b342ec78f154c273fc676206c8bae174dc87b669033e388f`; root manifest: `6c62717a45a1384240e0e5862f8173f2e7171679521ed37fccca237b9b028c37`.
- Slots: 1536/1536; distinct roots: 64/64; runtime: 691.419s; nodes: 2,167,464; queries: 38,940.
- Actual terminal outcomes: 1443; horizon/other UNKNOWN: 93; incomplete searches: 0.
- All outcome records and query ledgers reconcile by slot; each final history and claimed terminal was replayed through the Generic rule runtime.

## Outcomes (learner perspective)

| Endpoint | Wins | Draws | Losses | UNKNOWN |
|---|---:|---:|---:|---:|
| initial | 244 | 5 | 233 | 30 |
| TD95 | 286 | 0 | 194 | 32 |
| LocalLambda | 306 | 2 | 173 | 31 |

Paired reward differences give every pair containing UNKNOWN the full [-2,+2] range; exact pairs use their observed reward difference.

| Contrast (left − right) | Exact pairs / 512 | UNKNOWN pairs | Mean difference bound |
|---|---:|---:|---:|
| TD95 − initial | 457/512 | 55 | [-0.0488, 0.3809] |
| LocalLambda − initial | 461/512 | 51 | [0.0430, 0.4414] |
| LocalLambda − TD95 | 457/512 | 55 | [-0.1406, 0.2891] |

## Interpretation and limits

This corrects task2608's implementation failure without replacing or deleting its registration and zero-row evidence. It evaluates the already frozen task2606 models on exact-start-history-disjoint roots; no model or parameter selection was performed using these outcomes. UNKNOWN was not converted to a draw.

The selected roots are disjoint from the 512 possible task2606 training-family start records, but descendants are not proven disjoint and task2606 training trajectories are not an independent generalization guarantee. Therefore this is a finite, fixed-model diagnostic panel, not a fully independent holdout or evidence of broad Generic transfer. The 93 UNKNOWN outcomes widen comparisons; LocalLambda's comparison with TD95 remains unresolved whenever its bound includes zero.

A post-hoc exact-record audit additionally compared all logged task2609 query `record_before`/`record_after` histories with all logged task2606 training-query pre/post histories. It found 27,537 unique evaluation histories across 77,880 query-state occurrences and **zero exact full-history intersections** with the recorded training states, for each rule and all 1,536 slots. The audit uses only complete records (rule fingerprint plus ordered history), not outcomes, scores, or weights; details and input hashes are in `history-overlap.json`. This excludes reuse among the logged decision-state histories only: unlogged interior Alpha-Beta states, semantic/transposition-equivalent positions, and broader distributional generalization remain untested.

Post-hoc subgroup bounds, with every frozen rule and seed reported and no selection, show finite-panel heterogeneity:

| Group | LocalLambda − initial | LocalLambda − TD95 |
|---|---:|---:|
| Rule 271001 | [+0.0703, +0.1953] | [+0.0313, +0.0938] |
| Rule 271002 | [+0.6953, +0.6953] | [+0.2031, +0.2031] |
| Rule 271003 | [−0.5625, +0.8750] | [−0.7656, +0.8906] |
| Rule 271004 | [−0.0313, 0.0000] | [−0.0313, −0.0313] |
| Seed 1977 | [+0.0234, +0.4297] | [+0.0078, +0.3516] |
| Seed 8173 | [+0.0703, +0.6328] | [−0.1797, +0.3203] |
| Seed 27182 | [+0.1641, +0.3516] | [−0.2344, +0.1094] |
| Seed 31415 | [−0.0859, +0.3516] | [−0.1563, +0.3750] |

These are descriptive bounds on overlapping subgroups, not confidence intervals or independent replications. Rule 271003 is especially unresolved because 46–53 paired comparisons contain UNKNOWN; rule 271004's finite LocalLambda-minus-TD95 bound is slightly negative. Per-seed bounds also do not show a consistent advantage over TD95. Full values and unknown counts are in `stratified-effects.json`.

The runner and audit code are task-specific evidence tools; they do not change engine defaults, UI, or primary checkout.

The raw evaluation JSONL streams remain locally preserved; compressed copies are published here for independent inspection. `compressed-streams.json` records each original and archive byte count and SHA-256. Both gzip streams were decompressed and verified against their exact original digest before publication.
