# Prospective root-admission protocol for TD material-learning comparisons

Superseded as next-task guidance by results/dev_aux/task2601/ROOT_ADMISSION_PROTOCOL_V3.md. This original two-estimand draft is retained as historical design evidence; consult v3 for the current DEV_AUX recommendation.

This is a design note only. It creates no roots and does not reopen task2592 or task2595.

## Freeze the estimand first

Choose one of two targets before producing any candidate outcomes:

1. **Unconditional family distribution.** Keep terminal and repeated roots as sampled. Report their mass and effective unique-history count. If repeated histories are weighted as repeated draws, state that weighting explicitly; do not call the rows independent observations. Use paired comparisons on the exact same rows and summarize sensitivity at the canonical-root cluster level if making a population claim.
2. **Decision-bearing conditional distribution.** Define the target as four-ply histories that are legal, nonterminal and outside the complete planned TRAIN-root set. This intentionally changes the target distribution. Use deterministic rejection sampling, state the conditional target and candidate-family distribution, and report every rejected family by reason.

Do not discard terminal/duplicate candidates while continuing to describe the result as the unconditional root distribution.

## Pre-fitness registration

- Freeze rule IDs/source hashes, all TRAIN family IDs (including the full declared maximum under the cap), EVAL candidate interval, root-prefix PRNG, prefix plies, exact canonicalization, terminal/legal policy, required EVAL count, hard candidate bound, roles, foes and paired-slot weights.
- Materialize the complete planned TRAIN root manifest before fitness. Canonicalize the full serialized history (rule fingerprint, initial state, actions and history-sensitive fields), not only board occupancy or family IDs. Report duplicate counts and unique TRAIN histories; do not invent a uniqueness failure gate after seeing results.
- Generate EVAL candidates from a separately seeded, domain-separated stream. For the conditional target, accept a candidate only if it is legal, nonterminal, absent from the entire frozen TRAIN-history set and absent from an `eval_seen` set. The latter check is required even if family IDs differ.
- Freeze and hash the resulting EVAL manifest before any fitness begins. Apply the exact same roots, sides, foes and weights to every candidate and baseline.
- Exhausting the frozen candidate interval before reaching the target count is an admission failure. Preserve it; do not expand the interval, swap rule seeds or reuse a failed set after observing outcomes.
- Charge candidate generation, replay and audit work to the total budget. Keep all `UNKNOWN`, incomplete and missing outcomes censored; never impute draws.

## Lessons from the two audited registrations

Task2595's fixed 364005 roots failed its declared uniqueness, disjointness and nonterminal-count gates; the registered seed was retained and learner fitness did not start. Task2592 happened to have unique selected EVAL histories, but its selector did not enforce EVAL-to-EVAL uniqueness; its actual TRAIN overlap was already reported as 256 slots and is localized by task2600 to all 8 selected roots for rule 364004. Future code must gate on actual frozen histories rather than nominally disjoint family-number ranges.
