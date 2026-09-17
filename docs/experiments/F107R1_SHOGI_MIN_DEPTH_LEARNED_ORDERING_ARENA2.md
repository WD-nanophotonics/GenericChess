# F107R1 Standard Shogi learned-ordering transfer Arena2

F107R1 executed the corrected F107 transfer order after the prior order’s model-hash typo was resolved against the tracked F78/F81 evidence. This note records the frozen result; the initial F107 mismatch remains classified separately as `SHOGI_MIN_DEPTH_ORDERING_IDENTITY_MISMATCH`.

## Frozen identity and isolation

- Sandbox baseline: `df6f90498117c7668811bdb4d48068fa0ce8b5cd`
- Ruleset: `B_CANONICAL_STANDARD_SHOGI`
- Parent/leaf evaluator: `d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4`
- Ordering-only checkpoint: `f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4`
- Ordering compact model SHA256: `b4372d087d0e7760857efefd69413c97c8cf10b5b188dd704f5d1e308a4d32b6`
- F81 provenance: `PARENT_ANCHORED_FULL_RESIDUAL_FINAL_CONFIRMED`

Both Arena arms used the parent checkpoint as the sole evaluator. The child checkpoint was supplied only as the learned ordering profile. No learned value, cutoff, filtering, top-k, root hint, or terminal rule was introduced. Search control was `ordering_min_depth=2`, `ordering_max_ply=-1`, complete legal-action sorting with deterministic ties, F102 cache/feature reuse, TT 8 MiB, root-window pruning, fresh engine per game, and a one-second move budget with a one-million-node search ceiling.

## Correctness gates

All gates passed: identical leaf bindings and direct leaf values, exact ordering checkpoint/model identity, ordinary parent-path parity, active learned ordering at remaining depth two or greater, remaining-depth-one skip telemetry, cache-on/cache-off action/score/PV parity, and legal candidate action with nonzero ordering telemetry.

The two fresh opening final-position keys were:

- `ed9c8b1d037d8be13d3ee0693ea5bdc6d1b643d51f296585b25e63d0866e4604`
- `7e15fc937f4413c9c64b9aea7466970dc901b524f6253d5777d8fcb82ba76949`

They were generated with seed `638701`, plies 2–6, and were disjoint from the tracked F78/F79/F80 corpus (the F79/F80 stages reuse the F78 corpus) and F81 corpus. Fresh corpus ID: `9959def9293c406a70047a54c8357506d64e36e320c4588ec2ab4c22f4f68ec8`.

## Equal-wall-clock Arena2

The candidate completed two role-swapped pairs / four games, all terminating by normal repetition with no contest, truncation, or node-ceiling event. Pair scores were `[0.5, 0.5]`, mean pair score `0.5`, better/tied/worse pairs `0/2/0`, and game W/D/L `0/4/0`. Candidate arm search telemetry recorded 433 searches and 96,183 total nodes; the child ordering searches recorded 6,515 ordering evaluations, 150 ordering nodes, 6,691 ordering actions, 12.5944444 seconds of ordering time, cache hits/misses/collisions `620/6515/1178`, and 1,883 remaining-depth-one skips. Candidate child search wall time mean/median/p95/max was `1.012139/1.011464/1.021275/1.034444` seconds, with 217/217 requested-time terminations and maximum overshoot `0.034444` seconds.

The candidate did not improve the frozen parent in this minimal Shogi transfer. Classification: `SHOGI_MIN_DEPTH_LEARNED_ORDERING_EQUAL_WALLCLOCK_REJECTED`. This rejects the Shogi ordering-only transfer at Arena2; it does not invalidate the independently final-confirmed F81 Shogi value/evaluator result. No Arena4, retraining, scorer change, timing/cache sweep, Chess tuning, or promotion is authorized by this result.
