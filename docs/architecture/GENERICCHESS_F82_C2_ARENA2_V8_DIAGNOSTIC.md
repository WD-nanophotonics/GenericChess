# F82 C2 Arena2 v8 diagnostic closeout

- Published baseline SHA: `ab03a4d65de5091682d1a8a723fe8b65970d6b88`
- Prior run audited: `f82-c2-arena2-v7-df3c30d50cd3`
- v8 plan request: `GENERICCHESS-20260914-105156-31fcfd40`
- v8 plan SHA: `58ca39a7eb02dfb01b431ecfe33413277bf85ee9a8b4747d43dd051abd56678c`
- v8 normalized envelope SHA: `19a76a7df3eed83ba1f9aa6dcaa8afb5dfab8e2df8bac812e2aa552a60406367`

## Evidence and contradiction

The v7 Heavy completed at the monitor level but returned Arena `INCOMPLETE` with `completed_games=1`, `completed_pairs=0`, and `reason=stage_wall_seconds`. It ran from epoch `1789382367` to `1789382692` (about 325 seconds of outer wall time), despite the approved `per_game_wall_seconds=7200` and `stage_wall_seconds=7200`. The owner-1 file was not written.

The existing owner-0 checkpoint contains 380 plies and 380 search rows. Both roles used 97,280 nodes; all rows ended with `termination_reason=node_budget`. Native elapsed sums to 989.53 seconds (498.24 child, 491.29 parent), and the game ended in checkmate. This is valid one-sided evidence only and cannot decide C2 strength.

Source inspection shows the runner computes `stage_deadline = stage_started + caps.stage_wall_seconds`, passes the minimum remaining per-game/stage wall to each native search, and writes `game-XXXXXX-owner-X.json` only after `_play_one_game()` returns a terminal game. Any cap exception loses all in-game progress and telemetry for that owner. Thus the current resumable unit is a whole game, not a long-game prefix. The code contains no conversion that would turn 7200 seconds into 325 seconds.

A tiny native witness with `max_time_seconds=7200`, `max_nodes=512`, and depth 12 returned `node_limit` in 0.0024 seconds, confirming that the large wall value reaches native search and does not itself trigger an early deadline. Because owner-1 telemetry is absent, the 325-second/`stage_wall_seconds` contradiction cannot be resolved by existing artifacts alone; another brute-force wall extension would repeat an uninstrumented failure.

## Routing decision

The registered Supervisor rejected the v8 14,400-second extension under the anti-overengineering and large-compute boundary; v8 Heavy was not launched. No candidate, parent, corpus, seed, search parameters, effective workload, or promotion state changed.

The smallest strength-relevant alternative is a bounded long-game completion protocol: persist an atomic mid-game prefix (position/history, cumulative nodes, and per-search termination/elapsed telemetry) before a cap, then resume that exact owner-1 prefix or apply a pre-registered short-horizon/adjudication rule. This preserves paired role symmetry while making a cap diagnosable and avoids spending another multi-hour window without evidence. Any implementation or compute plan for that protocol requires a fresh Chat order and exact Supervisor approval.
