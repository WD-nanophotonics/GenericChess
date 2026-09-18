# F121 Shogi Gumbel neutral-declaration CRN Arena4

## Decision

`SHOGI_GUMBEL_COMPLETED_Q_NEUTRAL_DECL_CRN_ARENA4_CONFIRMED`

F121 added the already-authoritative generic neutral-declaration value-zero
outside option to `SemanticGumbelMCTSV0`, then reran the exact F118 child in a
fresh common-random-number Arena4. The parent-vs-parent null gate passed, all
eight strength games were valid, and the child passed the strength gate. No
promotion is automatic.

## Frozen inputs and implementation

- Work order: `GENERICCHESS_F121_GUMBEL_NEUTRAL_DECLARATION_CRN_ARENA4`.
- Implementation checkpoint: `29a9e05ef27531ca86d991fd96c87b36468abca9`.
- Frozen value checkpoint: `f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4`.
- Frozen compact value model: `b4372d087d0e7760857efefd69413c97c8cf10b5b188dd704f5d1e308a4d32b6`.
- Frozen parent policy: `2357472be320e9df909136a31a5223ec24e79f998467bb0ef3114b7e3433b955`.
- Frozen F118 child policy: `45281f8ccccf557fdbe2edd74fc0822dedbff209c2178125dafab3c883aefdb3`.
- Search algorithm otherwise unchanged: 64 simulations, root cap 8,
  8→4→2→1 sequential halving, unchanged Gumbel/logit/Q ranking and
  completed-Q target.
- CRN search seed: `1210901 + 10000 * pair_index + ply`.

Neutral declarations are now treated as generic value-zero outside options:
board-edge Q statistics remain unchanged, backed-up node values are clamped
at zero when a neutral declaration is available, and the final board survivor
is replaced by the deterministic first neutral declaration only when its
empirical root Q is non-positive. Winning declarations retain immediate
terminal behavior. This run selected no neutral declaration in the Arena;
the new path was exercised by correctness tests.

## Null gate

The first opening was played parent-vs-parent with role-swapped owners and
common random numbers. The complete decision sequence—including board moves
and declarations—terminal status, winner, plies, seeds, root Gumbels, visits,
survivors, and neutral-declaration telemetry were exactly equal. The CRN seed
contract passed and the null pair score was exactly `0.5`.

## Fresh opening corpus

Requested seed: `1210801`; collision-free selection offset: `1`.

| Opening | Opening seed | Target plies | Final-position identity |
| ---: | ---: | ---: | --- |
| 0 | 1210802000 | 3 | `ac7f63db588bb22bbd37e49a7337d0311936b447f871ec31c7e9f8da1ae6fdf7` |
| 1 | 1210802100 | 3 | `bfa0a3ab612df45d4e5060ee4e8b3a1942d78f8b9317da4fd6024196cd47bbaf` |
| 2 | 1210802200 | 3 | `ed2d5072aa4baf9cc79f531135eda4c30a4e29778a687573cc7491cf89760f01` |
| 3 | 1210802300 | 5 | `85b19cf6798c9bf207269a52d99e1cf62c02d3f6ef60c9730c4b9fe22f3a57c6` |

## Strength Arena4

All eight games were valid. Pair scores were `[1.0, 0.75, 0.5, 0.0]`,
mean child score `0.5625`, with two child-better pairs, one tied pair, and
one child-worse pair. The game-level W/D/L diagnostic was `4/1/3`.

| Game | Pair | Child side | Result | Winner | Plies |
| ---: | ---: | ---: | --- | ---: | ---: |
| 0 | 0 | 0 | checkmate | 0 | 222 |
| 1 | 0 | 1 | checkmate | 1 | 105 |
| 2 | 1 | 0 | no-contest | none | 497 |
| 3 | 1 | 1 | checkmate | 1 | 147 |
| 4 | 2 | 0 | checkmate | 0 | 244 |
| 5 | 2 | 1 | checkmate | 0 | 252 |
| 6 | 3 | 0 | checkmate | 1 | 165 |
| 7 | 3 | 1 | checkmate | 0 | 162 |

Pair common-prefix diagnostics were `(0, 0, 4, 0)` actions; pair 2 first
diverged at ply 4 with common seed `1230905`. No declaration was selected in
the strength Arena.

## Correctness and replay gates

The focused F121 correctness suite passed alongside the prior search and
arena-integrity suite. It verifies Core/Native/session agreement for a
Standard-Shogi RESTART declaration, value-zero outside-option backup, positive
Q board selection, zero-Q declaration selection, deterministic telemetry, and
immediate winning declarations.

The F120 raw telemetry could replay only the root prefix of the failing game;
that root had no declaration, so the required internal tree state was not
serialized. The F120 replay gate was therefore recorded as
`SKIPPED_INTERNAL_STATE_NOT_RECONSTRUCTIBLE`, without treating it as strength
evidence.

Raw F121 telemetry is retained under ignored workflow evidence at
`.generic_chess_flow/f121-shogi-gumbel-neutral-decl-crn-arena4/report.json`.
