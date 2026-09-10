# GenericChess F79: parent-anchored full-residual Arena4

Status: `DO_NOT_START_YET` pending exact Chat compute approval and resolution of
the signed order's `no Heavy` constraint.

## Decision under review

Run the frozen F78 candidate `f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4`
against fixed parent `d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4`
for four owner-swapped pairs (eight games), using the durable F78 corpus
`2923f457e56454520f89c682614b3b10d07da974f03040bfc6c3a831ab41da48`.
The first two pair scores must reproduce F78's frozen `[0.5, 1.0]`; the full
gate is mean pair score `> 0.5` and child-better pairs greater than child-worse
pairs. No retraining, candidate mutation, corpus generation, self-play, or
production evaluator changes are in scope.

## Compute decision note

- Published harness checkpoint: `a05bfaeda815dca37a50aacddb97781c94fbdf0c`.
- Plan: `.generic_chess_flow/f79-compute/plan-v1.json`, ID
  `f79-parent-anchored-arena4-v1`, version 1, SHA
  `a4678c56c31640c3a8aa35bdb9ab63b60955f821e1f7ddc9cff4d8ff87abfd90`.
- Resource envelope digest:
  `290b08318f1e06d7a8d013adbf31b22abd4b0e75a409af2946855331b4086f48`.
- Command: `.venv\\Scripts\\python.exe scripts/f79_parent_anchored_full_residual_arena4.py`.
- Budget: expected 45 minutes / hard 60 minutes; expected 1 CPU-hour / hard 2
  CPU-hours; one stage, one intended CPU lane, maximum one concurrent game,
  eight games, 131,072 nodes per game, 256 plies per game.
- Checkpointing: retain the fresh `f79-arena4` progress namespace after every
  game and replay the completed summary before classifying.

The cheapest sufficient alternative is to reuse F78's completed two-pair
result as a deterministic prefix regression. That cannot decide the signed
F79 four-pair gate. Running no new games preserves resources but leaves the
question unresolved; a four-pair, eight-game stage is the smallest new sample
that satisfies the order.

## Supervisor assessment

The registered Supervisor signed `DO_NOT_START_YET` for this exact plan,
envelope, and SHA. The scientific assessment is that four additional games are
a reasonable minimal confirmation of F78's positive but weak two-pair signal,
and that the immutable candidate/corpus, per-game checkpoints, caps, replay
gate, and single-stage design are sound. Approval is legally incomplete because
the current Chat order explicitly says `no Heavy` and does not contain the exact
`GENERICCHESS_COMPUTE_PLAN_APPROVAL`, `GENERICCHESS_COMPUTE_PLAN_SHA`, and
`GENERICCHESS_COMPUTE_ENVELOPE_SHA` bindings required by AGENTS.md §16 and the
compute gate. Therefore F79 computation is not authorized yet.

## Chat decisions required before start

Chat must either:

1. explicitly amend `no Heavy` so Heavy is used only as the safety/checkpoint
   wrapper for this already ordered Arena4, and return the exact approval fields
   bound to the unchanged plan, envelope, and current sandbox SHA; or
2. replace F79 with a smaller decision procedure.

Chat must also confirm that `workers=1` is intentional despite the order's
`max_concurrent_games <= 4`, and state whether deterministic early termination
is allowed once the final four-pair classification is mathematically forced.

Until those decisions are bound to the exact plan and envelope, do not start
F79 and do not create a replacement request.
