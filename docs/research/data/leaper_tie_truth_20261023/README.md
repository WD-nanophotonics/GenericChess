# Tie, history truth and free-prior evidence

[Report](../../LEAPER_TIE_TRUTH_AND_FREE_PRIORS_20261023.md).

`evidence.json.gz` contains complete inputs,planned/attempted/missing slots,
one-sided certificates,actual query/PV/game records,source-target checks and
inert executed-source text. `strongfoe-source.json.gz` is the exact committed
PRIMARY source packet at sandbox1ac1f97a;its source SHA256 is in manifest.json.
It is retained to independently reconstruct the96 frames/62 divergences and
verify the actual complete source critic. No embedded source is executed.

Run from the repository root:

```powershell
.venv/Scripts/python.exe docs/research/data/leaper_tie_truth_20261023/verify.py docs/research/data/leaper_tie_truth_20261023/evidence.json.gz --output artifacts/tie-truth-replay.json
```

The reader reconstructs selection,binds full histories,checks complete defender
WIN certificates,replays new literal PVs/actual games and verifies paired utility
bounds. It does not rerun proof searches,forward experiments or the expensive
bounded-time reachability predicates. Those original capped receipts stay data.
The single240-second cooperative replay guard does not grant new experiment
budget. An interrupted reader supplies no upgraded labels. The checked receipt
is verification.json;this is shared-Core reproducibility,not an independent
engine/WDL oracle or an independent-rule holdout.

UNKNOWN and unstarted slots are retained. No source game is newly counted as an
AUX forward execution: only the sixteen learner-path pilot games are NEW.
