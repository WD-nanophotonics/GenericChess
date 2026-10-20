# attempt-2 bounded cost scan interpretation

The raw `result.json` is retained unchanged. Its eight arms all completed exactly 64 searches with 9,472–12,243 combined nodes, below the registered 100,000-node per-arm cap. The code initialized `ending` to `NODE_BUDGET_UNKNOWN` and omitted a post-loop `MAX_PLIES` assignment, so that field is inaccurate: the actual end for every arm was the 64-ply limit. No search was incomplete; no terminal W/L, learned weights or fitness was recorded. Treat only the paired search/update throughput and internal-sample counts as cost-path evidence. The corrected attempt-3 raises the ply ceiling to 1,024 with the same seed, root recipe, per-arm node cap and 900-second global cap, and explicitly reports a ply-limit exit.

{
  "attempt_2_result_sha256": "8ea1c876479c770be543fb793dbce53d7c5e15e04a564b516eaf5382655b564c",
  "arms": [
    {
      "seed": 5670,
      "method": "TreeStrap(eta=.05)",
      "nodes": 12243,
      "searches": 64,
      "wall_seconds_increment": 1.425713,
      "actual_end": "MAX_PLIES_64",
      "recorded_end": "NODE_BUDGET_UNKNOWN"
    },
    {
      "seed": 5670,
      "method": "TDLeafEpisode(eta=.05,lambda=.95)",
      "nodes": 12243,
      "searches": 64,
      "wall_seconds_increment": 1.392244,
      "actual_end": "MAX_PLIES_64",
      "recorded_end": "NODE_BUDGET_UNKNOWN"
    },
    {
      "seed": 181982,
      "method": "TreeStrap(eta=.05)",
      "nodes": 10224,
      "searches": 64,
      "wall_seconds_increment": 1.284388,
      "actual_end": "MAX_PLIES_64",
      "recorded_end": "NODE_BUDGET_UNKNOWN"
    },
    {
      "seed": 181982,
      "method": "TDLeafEpisode(eta=.05,lambda=.95)",
      "nodes": 10224,
      "searches": 64,
      "wall_seconds_increment": 1.321327,
      "actual_end": "MAX_PLIES_64",
      "recorded_end": "NODE_BUDGET_UNKNOWN"
    },
    {
      "seed": 449984,
      "method": "TreeStrap(eta=.05)",
      "nodes": 10386,
      "searches": 64,
      "wall_seconds_increment": 1.461815,
      "actual_end": "MAX_PLIES_64",
      "recorded_end": "NODE_BUDGET_UNKNOWN"
    },
    {
      "seed": 449984,
      "method": "TDLeafEpisode(eta=.05,lambda=.95)",
      "nodes": 10386,
      "searches": 64,
      "wall_seconds_increment": 1.415191,
      "actual_end": "MAX_PLIES_64",
      "recorded_end": "NODE_BUDGET_UNKNOWN"
    },
    {
      "seed": 714589,
      "method": "TreeStrap(eta=.05)",
      "nodes": 9472,
      "searches": 64,
      "wall_seconds_increment": 1.180209,
      "actual_end": "MAX_PLIES_64",
      "recorded_end": "NODE_BUDGET_UNKNOWN"
    },
    {
      "seed": 714589,
      "method": "TDLeafEpisode(eta=.05,lambda=.95)",
      "nodes": 9472,
      "searches": 64,
      "wall_seconds_increment": 1.251644,
      "actual_end": "MAX_PLIES_64",
      "recorded_end": "NODE_BUDGET_UNKNOWN"
    }
  ]
}
