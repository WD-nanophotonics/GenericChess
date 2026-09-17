# F97 Chess learned tree move ordering Arena2

Work order: `GENERICCHESS_F97_CHESS_LEARNED_TREE_MOVE_ORDERING_ARENA2`

Baseline: `6064a3d1dd683b90497b16e3f4c5d4d12db02ed5`.

## Frozen route

Scope was exactly `A_CANONICAL_WESTERN_CHESS`. The parent evaluator was bound
to checkpoint `55249ef226ce60e51da8b6172881ea331757de0c72dbf918e48d84779dea1d5`
for both Arena arms. The optional Native ordering-only profile was the frozen
F61R4 raw child checkpoint
`68136a6ea36fc9ab764bc7164e1fdb58c7cfbead718500dc9f51c0feedf0649f`, with
model SHA256
`855537bd5f473c557e22eba7b2fccd51142d5572599e4075d93dd127c2942950`.

At every internal node, Native enumerates the complete checked legal action
set, scores each child with the frozen ordering profile, converts child-side
score to mover Q by negation, and stably sorts descending score then native
action identity. The profile is not used for leaf values, filtering, top-k,
terminal handling, root hints, or Python calls in the node loop.

## Pre-Arena gates

The D1 source was reconstructed with two parent self-play games, source seed
`620100`, 2,000 nodes/move, depth 12, epsilon 0.1, TT 8 MiB, and a 24-ply cap.
The regenerated 24 root identities matched the frozen F61R4 order, and the
raw child/model identities matched exactly. The live F96 static-provider
parity gate matched the candidate first root action on `24/24` roots.
Shallow exhaustive correctness passed on four roots with zero score or
terminal mismatches and zero equal-score action changes. Direct leaf binding
passed. The cached 24-root / 161-action diagnostic used 2,000-node searches;
parent and candidate q20 top-action agreement were both `7/24`, with both
arms recording `48,000` nodes.

## Fresh Arena2

Envelope: `f97-chess-learned-tree-move-ordering-arena2-v1`.

The run used opening seed `628701`, two deterministic openings, two
role-swapped pairs / four games, equal parent and ordering-arm budgets of
2,000 nodes/move, depth 12, TT 8 MiB, one worker, and root-window pruning.
Opening keys were:

* `79b036538b4fbe187ea75387150a4c7081d124d4c5a25f9c2d02a730c3c86dcc`
* `05b14f3d31a32982dec69d9cdd1f6b16c372c71b0bb2331e45ecb00cbb6ed18b`

All four games completed without no-contest results. Game outcomes were
checkmate at 55 plies, checkmate at 46 plies, and two max-ply draws at 998
plies. Pair scores were `[1.0, 0.5]`, mean `0.75`, with one better, one tied,
and zero worse pairs; game W/D/L was `2/2/0`. Parent and candidate search
totals were `2,093,614` and `2,096,213` nodes. Ordering telemetry recorded
`4,092,563` action evaluations over `124,109` ordering nodes.

The completed run exposed a Windows QPC intermediate-multiplication overflow
in one ordering-latency telemetry field; it did not affect search scores or
actions. The Native clock conversion was corrected with overflow-safe
quotient/remainder arithmetic and the focused Native tests passed afterward.

## Decision

`LEARNED_TREE_MOVE_ORDERING_SURVIVES`: mean pair score exceeded 0.5 and the
ordering arm won more pairs than it lost. No broader Arena, Shogi, or
promotion decision is implied by this Arena2 micro-diagnostic.
