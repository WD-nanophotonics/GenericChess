# GenericChess F75 Parent-Retained Arena2 Strength Triage

## Decision

F75 completed the exact bounded two-pair Arena stage and classified the F74
parent-retained output-weight candidate as
`PARENT_RETAINED_ARENA2_REJECTED`. The child scored 0 wins, 3 draws, and 1
loss across four game-atomic games. Its mean pair score was `0.375`, below
the registered survival threshold of `0.5`.

This candidate is stopped. No alpha change, retraining, seed sweep, follow-on
Arena4 stage, or promotion is authorized by this order.

## Provenance and durable inputs

- Work order: `GENERICCHESS-F75-PARENT-RETAINED-ARENA2-STRENGTH-TRIAGE`
- Baseline/source commit: `ec8167a056bac3206a39809abc4a13343c0a838c`
- Parent checkpoint: `d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4`
- F74 candidate checkpoint: `bafabe1a6eeedf30b0ebe34109e5c4efdad87fc434edf8e75e9030e958bca0bb`
- Candidate descriptor: `artifacts/f75_parent_retained_arena/candidate.json`
- Candidate alpha: `1.0`
- Candidate compact-model SHA-256: `f29d7f7108c35e85ed66aa9b77f3bea8fcce1f7e4a51ede5f1923107f5b2ea69`
- Opening corpus: `artifacts/f75_parent_retained_arena/openings.json`
- Opening corpus ID: `b4fa3ed5cfcc8432fb5f7fde8e003b1a801f10f6e91093463c99df1ed9204ad1`

The evaluator-neutral Standard-Shogi corpus used seed `750501` and eight
openings with two to six plies. Final position keys were unique and had zero
overlap with the 96 F62 source roots. The same corpus was reused for both
games in every pair.

## Arena contract

The stage used exactly two swapped-owner pairs (four games), fresh engine
state per game, one effective game lane, 512 nodes per move for both parent
and child, maximum depth 12, an 8 MiB transposition table, and product root
window pruning enabled. Execution caps were 256 plies and 131,072 nodes per
game, four maximum stage games, four maximum concurrent games, and 3,600
seconds for both each game and the stage. No Heavy job or automatic Arena4
extension was run.

The stage completed all four games and both pairs with no cap reason and no
contract failures. A single progress reload/replay validation returned the
same complete status, counts, and pair summary.

## Results

| Measure | Result |
| --- | ---: |
| Pair scores | `[0.25, 0.5]` |
| Mean pair score | `0.375` |
| Better / tied / worse pairs | `0 / 1 / 1` |
| Game wins / draws / losses | `0 / 3 / 1` |
| Bootstrap interval | `[0.25, 0.5]` |
| Total searches | `528` |
| Parent search nodes | `135,680` |
| Child search nodes | `134,656` |
| Root-pruning telemetry | true on all rows; 0 missing |

Search completion depths were parent `148 @ depth 1` and `117 @ depth 2`, and
child `132 @ depth 1` and `131 @ depth 2`; every recorded search terminated at
its node budget of 512.

The raw transient result is retained only under the ignored runtime directory
`.generic_chess_flow/f75-parent-retained-arena2-triage/f75_results.json`.
