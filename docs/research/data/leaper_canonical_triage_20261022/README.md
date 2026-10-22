# Canonical Leaper history evidence

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe docs/research/data/leaper_canonical_triage_20261022/verify.py
```

The gzip capsule contains compact complete-history labels, original trajectory
actions/record headers, public learner receipts, proof trees, the exact price
intervention and safe closure, bounded-run statuses, prior metadata and executed
scientific sources. Bulk graphs and raw traces remain ignored.

The verifier replays all 369 distinct records/35,648 actions and their actual
action attribution; checks grid/prior arithmetic and exact reuse; verifies 29
original proofs and one separate intervention; rejects corrupted proofs and a
wrong intervention binding; recomputes clock/argmax/closure controls and selected
literal PVs. It does not independently re-solve the full WDL graph census.

Source/measurement baseline: sandbox e8f4abf94bde7b6de1ab1a9acc3abfd24533c002.
Closing reused interfaces: sandbox 44d346484b8927309bf3437b99d4816a36fd3cf0;
Core/rules/search/history unchanged. Original missing, partial and capped cases
remain explicit. No training, held-out or population-strength claim is made.
See [the report](../../LEAPER_CANONICAL_HISTORY_TRIAGE_20261022.md).
