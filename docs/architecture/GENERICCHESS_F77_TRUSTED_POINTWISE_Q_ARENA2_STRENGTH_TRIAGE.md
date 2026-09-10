# GenericChess F77 Trusted Pointwise-Q Arena2 Strength Triage

## Decision

F77 completed the exact two-pair Arena2 stage for the durable F76-R2
pointwise-Q candidate and classified it as
`TRUSTED_POINTWISE_Q_ARENA2_REJECTED`. The child won one game and lost three,
with no draws; pair scores were `[0.0, 0.5]` and mean pair score was `0.25`,
below the survival threshold of `0.5`.

This candidate is stopped. No alpha change, retraining, seed sweep, Arena4
extension, self-play, external-engine comparison, Heavy job, final-holdout
read, or promotion was run or authorized by this order.

## Candidate and corpus

- Work order: `GENERICCHESS-F77-TRUSTED-POINTWISE-Q-ARENA2-STRENGTH-TRIAGE`
- Baseline: `2eac3d2ac36519dfaab2b2cd6a6112d9404b5c00`
- Parent checkpoint: `d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4`
- Child checkpoint: `fb3d3113b7044de6ebbf17352d7e34f0713618afbaae6eb792ebb515b09f30db`
- Candidate descriptor: `artifacts/f76_r2_trusted_pointwise_q/candidate.json`
- Candidate model SHA: `318ba6ce996f99ae569d487d8b221675ebb13ccc123ab5a2c1c07effd0879893`
- Frozen corpus: `artifacts/f77_trusted_pointwise_q_arena/openings.json`
- Corpus ID: `259dea9b69ce536ebf126264e1bcfed0684c02aba19f28156991f2ca1ea68d3e`
- Corpus seed/count: `770501 / 8`

The eight Standard-Shogi openings used two to six plies, had eight unique
final position keys, and had zero overlap with all 96 F62 source roots or the
eight-opening F75 corpus. Only the first two openings were used for this
Arena2 stage; the full corpus is frozen for any future stage.

## Arena contract and integrity

The stage used exactly two swapped-owner pairs (four games), fresh
parent/child engine state per game, one worker/effective lane, 512 nodes per
move for both sides, maximum depth 12, an 8 MiB transposition table, and
product `root_window_pruning=True`. Execution caps were 256 plies and 131,072
nodes per game, four maximum stage games, four maximum concurrent games, and
3,600 seconds for both each game and the stage.

All four games and both pairs completed without a cap reason. A second call to
the same resumable entrypoint reloaded the progress directory and matched
status, game/pair counts, pair scores, game W/D/L, and the complete summary.
No contract failures were recorded.

## Results and telemetry

| Measure | Result |
| --- | ---: |
| Pair scores | `[0.0, 0.5]` |
| Mean pair score | `0.25` |
| Better / tied / worse pairs | `0 / 1 / 1` |
| Game wins / draws / losses | `1 / 0 / 3` |
| Bootstrap interval | `[0.0, 0.5]` |
| Total searches | `495` |
| Parent search nodes | `126,914` |
| Child search nodes | `126,464` |
| Max nodes per search | `512` |
| Root-pruning telemetry | true on all rows; 0 missing |

Parent completed depths were `128 @ depth 1` and `120 @ depth 2`; child
completed depths were `116 @ depth 1` and `131 @ depth 2`. Search timing and
NPS remain diagnostic only.

The raw result remains ignored under
`.generic_chess_flow/f77-trusted-pointwise-q-arena2/f77_results.json`.
