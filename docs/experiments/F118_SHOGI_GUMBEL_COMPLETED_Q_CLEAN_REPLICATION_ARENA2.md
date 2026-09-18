# F118 Shogi Gumbel Completed-Q Clean Replication Arena2

Status: `SHOGI_GUMBEL_COMPLETED_Q_CLEAN_REPLICATION_ARENA2_SURVIVES`

F118 is the first protocol-valid strength decision for the completed-Q Gumbel
policy-improvement loop. The algorithm is unchanged from F117; this run fixes
only the seed identity defect identified during F117 closeout.

Frozen inputs and result:

- baseline: `362d18671cd5b4fd16dc4efe6960d6ce443c96e4`
- value checkpoint: `f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4`
- parent policy: `2357472be320e9df909136a31a5223ec24e79f998467bb0ef3114b7e3433b955`
- F118 child policy: `45281f8ccccf557fdbe2edd74fc0822dedbff209c2178125dafab3c883aefdb3`

The executable seed contract passed exactly:

- genericity `1180001`
- self-play `1180101 + 10000*g + ply`
- training `1180111`
- consistency `1180201 + index`
- opening `1180801`
- arena `1180901 + 10000*g + ply`

Correctness gates passed: exact 64-simulation consumption, corrected 8→4→2→1
allocation, transformed-Q ranking, completed-Q fallback to root value,
full-support positive improved targets, deterministic behavior, generic smokes,
and Native/Python parity across 100 positions (maximum logit error
`4.440892098500626e-15`).

Fresh parent self-play produced 190 train, 64 dev, and 64 holdout informative
roots. Full-batch Adam used 100 steps, learning rate `0.001`, proximal
coefficient `0.001`, actual seed `1180111`, and selected alpha `1`.

| split | parent CE | child CE | parent KL | child KL |
|---|---:|---:|---:|---:|
| train | 3.298333 | 3.051674 | 0.735875 | 0.489217 |
| dev | 3.447483 | 3.384540 | 0.718383 | 0.655440 |
| holdout | 3.612668 | 3.459902 | 1.032316 | 0.879551 |

The completed-Q expected-value diagnostic was positive on every split, with
mean deltas 0.4155 train, 0.4235 dev, and 0.5631 holdout; this is a constructed
target diagnostic only, not the strength gate. The 24-root consistency probe
had 0.5417 action agreement and mean target KL 1.1294.

Arena2 used two fresh openings from seed `1180801`, two role-swapped pairs, the
declared arena seed formula, and the authoritative 512-ply safety boundary.
All four games were valid checkmates at 157, 146, 195, and 291 plies. Pair
scores were `1.0` and `0.5`; mean pair score was `0.75`, with one child-better
pair and zero child-worse pairs. The candidate therefore passed the declared
strength gate.

Complete actual-seed records, root telemetry, completed-Q targets, training
metrics, and arena evidence are retained in
`.generic_chess_flow/f118-shogi-gumbel-clean-replication-arena2/report.json`.
No automatic Arena4/8 or promotion is authorized by this work order.
