# F120 Shogi Gumbel common-random-number Arena4

## Decision

`F120_GUMBEL_COMMON_RANDOM_ARENA4_INVALID`

The common-random-number harness passed its mandatory parent-vs-parent null
pair, but the strength Arena did not meet the required all-eight-valid gate.
Game 5 encountered `GUMBEL_MCTS_UNSUPPORTED_NEUTRAL_DECLARATION` at ply 283
and remained ongoing. The result is therefore invalid for strength
interpretation; no child confirmation, promotion, or further Arena is
authorized by this run.

## Frozen inputs and protocol

- Work order: `GENERICCHESS_F120_SHOGI_GUMBEL_COMMON_RANDOM_ARENA4`.
- Implementation checkpoint: `6d96c90937b64408e7373ca8b47b931b3f68f9fb`.
- Frozen value checkpoint: `f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4`.
- Frozen compact value model: `b4372d087d0e7760857efefd69413c97c8cf10b5b188dd704f5d1e308a4d32b6`.
- Frozen parent policy: `2357472be320e9df909136a31a5223ec24e79f998467bb0ef3114b7e3433b955`.
- Frozen F118 child policy: `45281f8ccccf557fdbe2edd74fc0822dedbff209c2178125dafab3c883aefdb3`.
- Search backend: exact F118/F119 completed-Q Gumbel search, 64 simulations,
  root cap 8, sequential-halving schedule 8→4→2→1, and unchanged value/Q
  transform.
- Requested opening seed `1200801`; actual offset `0`.
- CRN search seed: `1200901 + 10000 * pair_index + ply`, independent of
  role, game index, policy identity, and child owner.

## Null-pair gate

The first opening was replayed in two role-swapped parent-vs-parent games.
The complete played action sequence, terminal status, winner, ply count,
per-ply selected action, root Gumbel vector, root visits, final survivor, and
search seed were exactly equal. The CRN seed contract also passed, and the
null pair score was exactly `0.5`.

## Opening corpus

| Opening | Opening seed | Target plies | Final-position identity |
| ---: | ---: | ---: | --- |
| 0 | 1200801000 | 3 | `ad3e009592d17f342a60c499fb303e88c35c1eea8eb1e5952f7628616fd5b630` |
| 1 | 1200801100 | 3 | `ddc9bbdbbf5429c46c82ef4bf6de3e808e2187826cc07ee549c60f49fbc3e7e7` |
| 2 | 1200801200 | 2 | `ac86d266f4eb77a91e80eb6b0632586fc72318bde2c440f55a833d3d2a48b235` |
| 3 | 1200801300 | 3 | `0901089981f05a5039ce3f6b7bb2d697fa9fe574447b43bb87edf151fe52dfc1` |

The corpus was checked against tracked prior Shogi identities and F115–F119
reports before either null or strength game was played.

## Strength games

| Game | Pair | Child side | Valid | Result | Winner | Plies | Error |
| ---: | ---: | ---: | :---: | --- | ---: | ---: | --- |
| 0 | 0 | 0 | yes | checkmate | 0 | 330 | — |
| 1 | 0 | 1 | yes | checkmate | 0 | 154 | — |
| 2 | 1 | 0 | yes | checkmate | 1 | 125 | — |
| 3 | 1 | 1 | yes | no-contest | none | 497 | — |
| 4 | 2 | 0 | yes | checkmate | 0 | 133 | — |
| 5 | 2 | 1 | no | ongoing | none | 283 | unsupported neutral declaration |
| 6 | 3 | 0 | yes | checkmate | 1 | 195 | — |
| 7 | 3 | 1 | yes | checkmate | 1 | 249 | — |

Seven games were valid. The provisional pair scores were `[0.5, 0.25, 0.75,
0.5]`, mean `0.5`, with one child-better pair, two tied pairs, and one
child-worse pair; these are reported only as diagnostics because game 5 made
the Arena invalid. The W/D/L diagnostic was `3/2/3` when counting the
no-contest results as draws.

Pair common-prefix diagnostics were `(0, 0, 0, 8)` actions for pairs 0–3;
the fourth pair first diverged at ply 8. These diagnostics do not alter the
validity or decision gate.

## Reproducibility and evidence

The deterministic regression contained eight repeated-search rows, each using
64 simulations and exact repeated-result agreement. Raw telemetry is retained
under ignored workflow evidence at
`.generic_chess_flow/f120-shogi-gumbel-common-random-arena4/report.json`.
