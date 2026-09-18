# F114 Shogi Native TreeStrap / bounded Arena2

Work order: `GENERICCHESS_F114_SHOGI_NATIVE_TREESTRAP_BOUNDED_ARENA2`

Baseline checkpoint: `f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4`

Candidate checkpoint: `ecb8d63d4e561b68302e3f7d6f382a588bfa68c0dd0a51fb09fd28e4a10f0250`

Candidate compact-model SHA: `91fc30b0ef70ed72d5a9d5bc9c186a0bd5357d42da8f230f866f727f4ff8a4bd`

## Result

Classification: `SHOGI_NATIVE_TREESTRAP_ARENA2_REJECTED`.

The frozen-parent TreeStrap fit produced a safe parent-anchored update at
alpha `0.25`, but fresh Arena2 was tied: mean pair score `0.5`, two tied
pairs, zero better pairs, and zero worse pairs. All four games were valid
checkmates within the 256-ply cap (217, 199, 103, and 117 plies). The parent
remains the active champion; the candidate is retained only as experiment
evidence.

## Trace and fit evidence

- One deterministic 64-move trajectory, seed `1140101`, Native AlphaBeta,
  512 nodes/move, depth 12, TT 8 MiB, epsilon `0.10`.
- Raw trace rows: `32601`; retained deduplicated rows: `30877`.
- Eligible rows: `30877`; bounds: EXACT `11075`, LOWER `18217`, UPPER `1585`.
- Eligible remaining depths: `0, 1, 2`; terminal, mate-band, and invalid /
  incomplete exclusions were all zero.
- Full-batch Adam: 100 steps, learning rate `0.001`, proximal coefficient
  `0.001`; parent objective `74.75556069194566`.
- Backtracking alpha `0.25` was the first safe update. It was finite, improved
  the bound-aware objective to `70.36237476406598`, preserved the protected
  24-state parent action set, and stayed within the residual bound.
- Trace-disabled versus trace-enabled parity passed on 24 roots; bound
  classification and candidate reload identity passed; no Policy binding was
  present.

The initial Heavy report used an overly strict zero-tolerance leaf comparison;
Native fixed-point quantization produces at most one `1 / 256` evaluator-unit
quantum. The F114 harness now records and checks that explicit tolerance over
100 replayed positions. This correction was not used to rerun or change the
completed Arena2 result.

## Route

Per the work order, this rejection routes the next experiment to the mainline
Gumbel/MCTS direction rather than further Policy-v1 tuning or TreeStrap
retries.
