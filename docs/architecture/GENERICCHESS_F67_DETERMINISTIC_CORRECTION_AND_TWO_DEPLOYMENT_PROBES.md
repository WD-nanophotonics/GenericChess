# GenericChess F67 deterministic correction and two deployment probes

Work order: `GENERICCHESS-F67-DETERMINISTIC-CORRECTION-AND-TWO-DEPLOYMENT-PROBES`

Parent repository SHA: `3c7277c7b62984883265b2d44dcbddaf66b3bc6e`.

This work order materialized exactly one deterministic child from Gen1 and ran
exactly two new 2,000-node deployment probes. It ran no training, optimizer,
seed sweep, Arena, self-play, teacher search, external engine, or Heavy job.
The checkpoint and probe evidence are ignored runtime artifacts under
`.generic_chess_flow/f67-deterministic-correction-and-two-deployment-probes/`.

## Deterministic child

The child is derived from Gen1
`d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4` with
`beta*=0.9427756814147658`. Every field is inherited unchanged except:

`output_weights = output_weights_Gen1 + beta* * (h_t - h_a)`

where `a` and `t` are the cached root-44 Gen1 top and stable/ordinary teacher
target actions. The child identity is:

* checkpoint ID: `5a124b54b7d250440c4dd2e5840b2825e27c6a635d54f48a6b607b5a34c26f63`
* compact model SHA: `c7cd7f700db61dc7197b6d3e61e624dd7ae91bcf4841f9968750c1d57ccd250d`
* `training_updates_delta=0`, `games_seen_delta=0`, `positions_seen_delta=0`
* inherited training counter: `training_updates=1`
* `training_seed=null`

The construction identity binds the F67 method, Gen1 parent, F62 stage and
records identities, root-44 position/action identities, and beta. The child is
not committed as a large model artifact; the deterministic construction rule
and the ignored checkpoint evidence are sufficient.

## Cached algebraic recheck

Re-evaluating all 96 cached F62 roots with the materialized child reproduced
F66 exactly:

* changed top-action roots: `[44]` only;
* root 44 target: `P [0,4]->[0,3]`;
* high-confidence roots preserved: 24/24;
* child maximum cached residual magnitude: `20,513.10326173877`.

No algebraic mismatch occurred, so the two authorized deployment probes were
run.

## Deployment probes

Both probes used a fresh semantic Native engine/TT, 2,000 nodes maximum, max
depth 12, and 8 MB TT. Gen1 comparisons reuse the persisted F62 `root_2k`
results; Gen1 was not rerun.

| root | cached Gen1 2k action | child 2k action | intended result |
|---:|---|---|---|
| 44 | `G [4,7]->[5,7]` | `G [4,7]->[5,7]` | target `P [0,4]->[0,3]` not visible |
| 72 | `B [7,1]->[6,2]` | `B [7,1]->[6,2]` | cached Gen1 action retained |

Root 44's child search score was `-2,443,726` versus the cached Gen1 score
`-2,530,161`; root 72's child score was `-109,895` versus cached Gen1
`-108,807`. These score changes did not alter the selected deployment action.

## Final classification

`DEPLOYMENT_CORRECTION_NOT_VISIBLE`

The fixed-feature correction is visible in the cached evaluator ranking but
not at the authorized 2k deployment search on root 44. Root 72 showed no
collateral action change. Per the work order, no additional probes or Arena
were started. This is a routing classification, not a playing-strength claim.
