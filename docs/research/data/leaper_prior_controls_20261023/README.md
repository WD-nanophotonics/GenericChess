# Curated ABC prior controls

Report: [ABC prior transfer and TDLeaf gradients](../../LEAPER_PRIOR_TRANSFER_AND_TD_GRADIENT_20261023.md).

The five gzip packets total 624,604 bytes. Full graph caches, repeated raw query
ledgers, account/Slack originals and temporary producers stay ignored.
Embedded producer sources are evidence strings, not automatically executed code.

| Packet | Scope |
|---|---|
| `new_context.json.gz` | All 512 new-context slots,64 prefixes,80 complete records;653 metadata-selected queries |
| `positive_controls.json.gz` | Only 256 NEW mobility/Static slots on the older64 prefixes;64 records and 1067 selected queries |
| `mechanisms.json.gz` |16 first-divergence trees,64 new public dyadic probes/two reused base queries,four residual D4/D6 trees,four new action interventions |
| `truth.json.gz` | Four new graph roots,133 source histories,3367 deduplicated query-history labels;all gaps and one-sided bounds retained |
| `next_step.json.gz` | Detached TD arithmetic/cost preparation and 16 new/16 reused diagnostic queries;no updated-policy games |

`positive_combined.json` references the exact hash of the already published
Unit/B2C1 validation packet in `leaper_natural_price_capacity_20261023/`.
Those 256 old outcomes and their paid costs are reused, not newly executed.
The original prospective validation remains unchanged; the added comparison is
exposed post-hoc evidence, not a new holdout or model-selection exercise.

Run from the repository root with the project environment:

```powershell
$d = 'docs/research/data/leaper_prior_controls_20261023'
.venv/Scripts/python.exe "$d/verify_games.py" "$d/new_context.json.gz" --output artifacts/prior-new-verify.json
.venv/Scripts/python.exe "$d/verify_games.py" "$d/positive_controls.json.gz" --baseline docs/research/data/leaper_natural_price_capacity_20261023/abc_validation.json.gz --combined-analysis "$d/positive_combined.json" --output artifacts/prior-positive-verify.json
.venv/Scripts/python.exe "$d/verify_mechanisms.py" "$d" --output artifacts/prior-mechanism-verify.json
.venv/Scripts/python.exe "$d/verify_truth.py" "$d" --source-from-git --output artifacts/prior-truth-verify.json
```

The truth reader needs the local fixed sandbox Git object when using
`--source-from-git`; it verifies the original compressed packet hash and census.
Its five NEW component rebuilds took546.487 seconds during ordinary concurrent
work. Summed entries include overlaps or potentially isomorphic components;
they are not independent state counts. All adjudication uses shared Core.

Every compact outcome and complete record is replayed. Only the published
metadata-selected game PV examples are publicly rechecked. Private full readers
checked all 21,700/19,796 queries and 84,325/77,700 PV edges; their receipts are in
`verification.json`. Reported physical node/time costs are reconciled metadata,
not independent CPU certification. No unknown root value is substituted with a draw.

The inherited selection prose in the positive-control producer mentions the
newer four-world mode. Its actual input bytes, complete RuleSets, prefix IDs,
explicit interpretation and reader bind eight older worlds and already frozen
prefixes. The original generated configuration is preserved, not silently edited.

The shadow endpoint arithmetic is reported preparation from hashed private full
target streams. Public readers bind its32 query PVs, not every omitted training
target. Changes in prices or two selected actions are not learning-strength gains.
