# F96 Chess learned root policy prior Arena2

Work order: `GENERICCHESS_F96_CHESS_LEARNED_ROOT_POLICY_PRIOR_ARENA2`

Baseline: `1c7813b57a0c2eee1140668db82d9871e94ab9d7`

Scope was exactly `A_CANONICAL_WESTERN_CHESS`. The parent value evaluator was
frozen at checkpoint
`55249ef226ce60e51da8b6172881ea331757de0c72dbf918e48d84779dea1d5e` for
both arms. The policy scorer reused the frozen F61R4 raw child
`68136a6ea36fc9ab764bc7164e1fdb58c7cfbead718500dc9f51c0feedf0649f`, with
raw model SHA256
`855537bd5f473c557e22eba7b2fccd51142d5572599e4075d93dd127c2942950`.
There was no retraining, refitting, damping, alternate model, seed, objective,
or data.

## Production extension and policy construction

The reusable arena extension accepts an optional role-scoped root-order-hint
provider. On the policy side, legal actions are enumerated deterministically;
the F59/F61 static child features are computed with the root-player-Q
semantics, and the policy score is

`learned_total_q = parent_base_q + frozen_F61R4_residual`.

The highest-scoring legal action, with the existing action-key tie break, is
passed only as `root_order_hint` to semantic search. AlphaBeta still uses the
exact frozen parent evaluator. The policy identity was bound into resumable
arena identity and has SHA256
`74827c99f9d02c0b4a0b79e0022566fceee704a3393eb64e8ec5c79c3179f260`.

Pre-Arena checks passed: the disabled path preserved ordinary behavior; parent
and policy evaluator bindings were identical; every hint was legal; a zero-node
search did not apply a hint; and hint telemetry was deterministic. In the
live Arena2 run all 134 policy hint records were legal, hint applications
matched attempted root iterations (`418 = 418`), and every first iterative
action matched the requested hint. Search metrics recorded the apply count and
first actions rather than treating the hint as a final-move override.

Cached F61R4 diagnostics over 24 roots / 161 actions showed that the learned
hint differed from the parent static top on 9 roots. Parent static-top q20
agreement was `11/24`; learned-hint q20 agreement was `20/24`. Mean q20 regret
was `43.0` for the parent static top versus `0.4166666666666667` for the
learned hint.

## Fresh Arena2

The experiment used envelope
`f96-chess-learned-root-policy-prior-arena2-v1`, opening seed `627701`, two
deterministic openings with two role-swapped pairs (4 games), 2,000
nodes/move for both arms, depth 12, 8 MiB TT, one worker, root-window pruning
enabled, and resumable terminal immutability. Opening position keys were:

* `2a423b4872e49d9d161add6198f2de8f5c6c83f7cbb12fe3f6d5233a0d876ebd`
* `5ac5534f3516af07f8ecee68714dbf97ef7327825f12c8b93b50ed7c6ec3d0b5`

All 4 games completed with no no-contest or truncation. Parent and policy
search totals were both exactly `268000` nodes. Policy overhead was 134 hint
evaluations, 4,185 legal actions scored, and 617.2814603999432 seconds of
hint-generation wall time; this is recorded as overhead and is not an equal
wall-clock claim.

Pair scores were `[0.5, 0.5]`, mean `0.5`, with 0 better / 2 tied / 0 worse
pairs and game W/D/L `2/0/2`. The games were:

* Pair 0, owner 0: checkmate, 78 plies, policy-side owner lost.
* Pair 0, owner 1: checkmate, 40 plies, policy-side owner won.
* Pair 1, owner 0: checkmate, 104 plies, policy-side owner lost.
* Pair 1, owner 1: checkmate, 46 plies, policy-side owner won.

## Decision

The learned root-policy-prior route is rejected because the mean pair score was
not greater than 0.5 and the policy did not win more pairs. No Arena4, Arena8,
Shogi, or promotion run was started.
