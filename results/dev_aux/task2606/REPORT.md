# DEV_AUX task2606 — finite Generic-rule transfer

## Question and registered design
Does a local-terminal-target TD(lambda) update transfer better than frozen TD(lambda=.95) from the same initialization on four finite Generic-rule definitions? Registered arms: 4 rules × 4 parameter seeds × 2 methods, 312,500 combined candidate-plus-opponent search nodes per arm (10M total target); one frozen uniform opponent. Evaluation: 768 matched slots (initial, TD95, LocalLambda; same rule, seed, full-history root and color), actual W/L/D, H=128. UNKNOWN and missing pairs remain unscored and receive [-2,+2] paired-reward bounds.

The estimate was 58 minutes; registered hard caps total 102 minutes. The plan's “candidate-paid” label was incorrect: the runner charges both sides' searches to each 312,500-node arm. `execution-accounting-correction.json` preserves that correction without changing the registered run.

## Training and integrity audit
Training completed all 32/32 arms and exactly 10,000,000 nodes in 3,469.4 seconds (57.82 minutes). It recorded 11,917 games: 11,651 actual terminals and 266 UNKNOWN; UNKNOWN outcomes remained censored. The closed query stream contains 178,420 rows, all assigned-color roles/observation indicators reconcile, there are zero incomplete observations, and every arm's query-node sum matches its result. Candidate/opponent node totals are 2,827,699/2,172,301 (TD95) and 2,812,139/2,187,861 (LocalLambda).

The first independent audit attempt rejected training games terminal at the generated prefix because they correctly had zero query rows. I fixed this audit-only edge case to allow zero-query terminal games, reran it, and it passed. No training source, plan, or raw records were changed.

## Actual outcome evaluation
All 768 registered slots completed in 298.3 seconds using 945,280 nodes; 727 games reached actual terminal outcomes and 41 remained UNKNOWN.

| Endpoint | W | D | L | UNKNOWN | Reward sum on known outcomes |
|---|---:|---:|---:|---:|---:|
| Initialization | 116 | 3 | 126 | 11 | -10 |
| TD95 | 138 | 0 | 99 | 19 | +39 |
| LocalLambda | 152 | 0 | 93 | 11 | +59 |

Slotwise LocalLambda-minus-control mean reward bounds, with every pair sharing rule, parameter seed, root family and color, and each UNKNOWN pair conservatively assigned [-2,+2]:

- Versus initialization: 234 exact pairs, 22 UNKNOWN pairs; mean bound **[+0.1055, +0.4492]**.
- Versus TD95: 230 exact pairs, 26 UNKNOWN pairs; mean bound **[-0.1328, +0.2734]**.

Thus the frozen panel favors both trained endpoints over initialization in raw totals, and LocalLambda has a positive lower bound versus initialization; it does **not** establish LocalLambda superiority to TD95 under the conservative UNKNOWN bounds.

Training residual loss was also summarized from the learner's recorded per-game loss, weighted by observed residual terms and binned by within-arm node fraction. It did not decrease monotonically: TD95 was 0.03187, 0.03124, 0.03230, 0.03448; LocalLambda was 0.03253, 0.03386, 0.03375, 0.03417. This is in-sample, trajectory-dependent loss, not independent prediction accuracy or棋力 evidence.

## Root-overlap defect and interpretation
Post-run exact comparison keyed by rule identity and complete stored `initial_record` found only 31 unique rule-history roots among 32 registered evaluation root families: families 991000 and 991001 under rule 271001 are duplicates. Ten of those 31 unique evaluation roots also exactly match at least one actually observed training-game start history (11 evaluation family IDs affected). Family-ID separation therefore did not create a held-out history panel. This defect was discovered after the frozen run; the 768 slots and primary bounds remain unchanged and are reported as registered. Treat them as a finite, training-exposed descriptive comparison, not independent generalization evidence; overlap may affect the result in an unknown direction. The check compares exact canonical records without semantic normalization and covers observed game starts only, not every possible recipe or later search state.

## Scope limits and next step
Only four previously defined Generic-rule sets and one finite panel were used. No novel-rule/all-domain or population-confidence claim. The Generic FreeModel updates all six coefficients while standard-Chess Model pins one scale coordinate, so this is update-rule transfer under a free Generic parameterization, not strict fixed-scale replication. Search depth is 2, with no prover/qsearch/SEE; opponent is fixed uniform. Some final coefficients are negative and vary across seeds, so no stable item-price ordering is established. Training/evaluation source pins and registered hashes were independently verified before evaluation, including because `evaluate.py`'s pin-mismatch list comprehension does not enforce failure itself.

For the next transfer test, enumerate and deduplicate full-history training roots before starting, bind identity to complete rule plus normalized history, freeze the proposal and shortage behavior, and verify train/eval disjointness before any training. Keep the WDL grid as a cost-matched control. Do not choose individual rules, roots, seeds or coefficients based on these results.

The four raw JSONL streams are preserved locally. Compressed copies are published here as `queries.jsonl.gz`, `games.jsonl.gz`, `eval-queries.jsonl.gz`, and `eval-games.jsonl.gz`; `compressed-streams.json` records original/archive byte counts and SHA-256. Each archive was decompressed and verified against its exact original digest before publication.
