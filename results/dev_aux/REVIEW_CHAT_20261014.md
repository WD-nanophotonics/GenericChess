# DEV_AUX method review — 2026-10-14

This is a bounded user-requested review, not a new research-duration sample. No new games, engine queries, training, holdout access or Slack sends were performed. The user-provided chat prose is advice; this document is the Agent's technical synthesis rather than a publication of that private input.

## Assessment

Adopt the central criticism: cheap outcome proxies have not established a reliable link to useful material values. Task742's quantity-at-cap reward can offset deterioration in actual terminal results. A further correction is that new seed families are new positions under standard Shogi, not newly generated rule systems. Earlier negative true-terminal trials restrict those tested distributions/optimizers; they do not demonstrate that outcome learning cannot work.

Segment38 already introduced few-piece NR/NRB true-terminal training, but that does not close the criticism. The terminal-density total and changing actions are insufficient; initialization-anchored, one-pass multiplier grids and fast-mate tie breaking also confound claims about a stable numerical ratio. The unit NR R180 and R360 candidates tied on both training objectives. In NRB, B90 and B32 likewise tied on both objectives; B360 tied on primary terminal return while differing in fast-mate return. These are direct reasons to report plateaus rather than an exact inferred price.

## New zero-query check

Task882 compares all 52 paired training cases in qualified task876 (104 physical games, B90 versus B328 with N90). Task877's physical audit passed; task882 binds the source JSONL SHA256. It reads no new holdout.

| Opponent | Physical games | Observed terminals | Paired terminal changes | Interpretation |
|---|---:|---:|---:|---|
| unit search | 52 | 1 loss | 1/26 | 25 pairs both unresolved; other pair unresolved to loss |
| uniform random | 52 | 22 wins | 10/26 | 5 new wins and 5 lost wins cancel; each price wins 11/26 |

Against search, all 26 full action sequences changed, while only one finite-horizon terminal contribution changed. Against random, 25/26 sequences changed, but aggregate J24 remained 11/26 for both prices. First candidate moves changed 5/26 and 2/26 respectively. Thus the previously reported 23/104 terminal density mostly measures wins against random; it does not justify immediately fitting the old NB distribution. This is evidence about two probes, not proof all prices are invariant. Two unresolved trajectories are not known to have the same eventual outcome.

## Decisions for the next experiment

1. Use actual W-L finite-horizon return as the primary objective. Keep actual draws and unresolved games separate, with every starting case in the denominator. Keep speed of mate as a separate target/diagnostic, not a hidden substitute for winning or evidence of precise material values. Do not restore quantity labels.
2. First improve and qualify the starting distribution. A prospective zero-prefix, closer-king NB grammar retains multiple interacting pieces, defense and exchange opportunities. Generate roots without screening on any price's success. Report terminal changes across families against the searching opponent, separately from random-player performance and action changes. Do not merely increase game count.
3. Fit one relative family coefficient on a shared, human-independent absolute grid. Assess seeded local optimization and the landscape together; report plateaus and sensitivity. Do not call identical exhaustive-grid argmax outputs from different starts independent convergence.
4. Freeze independent families, opponent policies and a small horizon/search-budget control subset before fitting. Report J12/J24/J48, censoring and sign reversals. No post-result selection of wins or extension of old frozen tests.
5. Connect NR and NB relations through an NRB transfer test before adding more coefficients. Family ties, promotion/drop semantics and evaluator/ordering consumers remain explicit limits. Human-reference comparisons are descriptive and occur after endpoint freeze.

Task883 records the concrete prospective design and producer cap. It is PREPARED_NOT_EXECUTED; exact generator/seed manifests must be frozen before queries. It supersedes the pending immediate NB-fit step, not earlier declarations or evidence. If the pilot remains weak, distinguish sparse terminals, weak price effects and flat finite-horizon objectives before choosing one changed-premise check. Small exact-state solutions are an optional costed alternative; a full tablebase or rewritten trainer is not a prerequisite.

The actual research question remains whether a mature search backend supports cheap, stable, behaviorally useful conditional material learning. Current modified YaneuraOu experiments do not yet prove success, nor do they settle unmodified Stockfish/NNUE or the project's complete generated-rule domain. Simplified-game success would justify the next transfer test, not directly adopt a full human-like price table.
