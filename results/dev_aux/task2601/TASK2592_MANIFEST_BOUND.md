# Task2592 static TRAIN-manifest coverage check

**Scope.** Read only the registered task2592 setup source and pinned task2565 trainer source. No task2592 games, query streams, outcomes, weights or evaluation records were opened for this check.

The registration source sets TRAIN_OFF=364100 and TRAIN_SPAN=500, so it materializes family IDs 364100–364599. Its plan declares max_games=4096 per arm. The trainer uses family = training_family_offset + index // 2 and has no guard against consuming family IDs beyond the registered span. For indices 0–4095, this expression can address 2,048 distinct families, 364100–366147; 1,548 of those are outside the registered range.

The plan also has a per-arm 100,000-node budget and a 2,400-second global wall cap, so this static range calculation does **not** establish that an actual run consumed an unregistered root. No execution records were inspected, and no runtime overrun is claimed. It does establish that the registration and runner do not themselves prove complete root coverage for every path allowed by the max-games declaration; the wall/node caps would need to be shown to make the later indices unreachable, or the future manifest/runner boundary must be aligned.

This is a prospective completeness risk only. It does not revise the previously reported task2592 overlap, W/L analysis, or any task outcome. No source code or old result was changed. For a future run, either preregister every root index that can be reached under all caps or add a frozen runtime guard that stops before consuming an unregistered root; report a cap caused by manifest exhaustion as a failure/shortfall, never generate a new root in-run.
