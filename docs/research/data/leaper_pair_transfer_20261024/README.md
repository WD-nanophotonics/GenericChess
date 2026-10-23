# Paired rule/history mechanism packet

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m scripts.verify_leaper_h6_pair_transfer --packet docs/research/data/leaper_pair_transfer_20261024 --output .local_agent/pair-reader.json
```

The default reader regenerates actual Core closure checks, both-rule proof
prefixes, exact common-prefix coupling, payoff decomposition, support/forecast
coordinates, all 3,616 fresh-root rank/action checks, the short literal history
counterexamples and four H64 all-defense certificates. It replays the retained
36 search decisions/PVs and recomputes the exact opponent-policy laws.

Optional independent, longer checks:

```powershell
.\.venv\Scripts\python.exe -m scripts.verify_leaper_h6_pair_transfer --packet docs/research/data/leaper_pair_transfer_20261024 --literal --prefixes --rebuild --policy-literal --output .local_agent/pair-full-reader.json
```

These repeat analytical verification, not the closed search batch. Neither
reader launches new Player calls, sampled games, training or another worker.

- `manifest.json` binds scientific files and both unchanged source packets.
- `dual-prefixes.json.gz` records each actual old/new rule prefix and each
  independently verified or rejected rebound subtree.
- `coupling.json.gz`, `gain.json.gz`, `literal-gain.json` separate path overlap
  from payoff change and bind all 128 literal paired-path/risk controls.
- `coordinates.json.gz` separates stored graphs from common-μ closures, complete
  history counts, measure-selection terms and real frozen forecast contrasts.
- `order-proof.json` verifies the scoped finite-history value preorder.
- `blocked-fresh.json`, `blocked-prefix.json` bind the rank reduction to all
  supplied fresh roots/actions and all 81,096 actual pair history contexts.
  The latter includes two explicit ongoing same-Position/clock counterexamples.
- `history-counterexample-check.json` gives their ten-node literal checks.
- `mask5-domain.json.gz`, `mask5-truth.json.gz` contain the supplied H64 pair's
  new closure, four full-history WIN certificates and 41 proof-path decisions.
- `depth-inputs.json.gz`, `depth-results.json.gz`, `depth-validation.json` retain
  all frozen teacher contexts, query plans, actual public search receipts and
  literal PV validation. No refit, missing-slot refill or claimed natural μ.
- `depth-mechanisms.json.gz` gives literal shallow material maximizer sets.
- `material-feature-support.json` shows there is no active free material channel
  in this one-ordinary-type, fixed-scale, no-hand control.
- `policy-laws.json.gz`, `policy-validation.json`, `policy-literal-plan.json`
  compare uniform versus uniform/FLOOR on the same 128 starts per rule, with
  every one of the 512 laws independently checked through full GameState.
- `comment-scope.json` records the independent scope correction to a received
  75-edge mathematical claim; it is not a new rule generator/campaign.
- `execution-qualification.json` records source timing, actual search counts,
  tests, failures and limits. New source hashes are post-execution qualification.

The parent source packets remain at `../leaper_h6_initial_truth_20261023` and
`../leaper_single_parity_20261023`. No private pickle or ignored producer output
is required. See [the report](../../LEAPER_PAIRED_HISTORY_MECHANISMS_20261024.md)
for equations, exact supports, source SHAs and interpretation.
