# GenericChess F63-R2-R1 zero-compute evidence closeout

Work order: `GENERICCHESS-F63-R2-R1-ZERO-COMPUTE-EVIDENCE-COMPRESSION`

Parent repository SHA: `6292c3ef63dd0295e668b8db55d23be30724b2c6`

The pass used preserved R10 game files, preserved F62 action-spectrum rows,
the frozen F62 compact-model evidence, and the already-computed F63-R2 Stage-0
signatures. It started no Arena, Heavy, engine search, game, or new search
sweep. The machine-readable detail is retained in the ignored runtime file
`.generic_chess_flow/f63-r2-r1-zero-compute-evidence-compression/evidence_compression.json`.

## Preserved R10 evidence

`child_score` is from the candidate child perspective (win 1, draw 0.5, loss
0); pair score is the mean of the two swapped-role games. A missing role does
not form a complete pair.

| seed | persisted game files / completed game indices | complete pairs | pair score / child W-D-L / termination / opening identity |
|---|---:|---:|---|
| 59011 | 8 / `000000-owner-0,1; 000001-owner-0,1; 000002-owner-0,1; 000003-owner-0,1` | 0, 1, 2, 3 | p0 `0.00 / 0-0-2 / checkmate+checkmate / 25a3cf8f`; p1 `0.50 / 1-0-1 / checkmate+checkmate / e1187547`; p2 `0.00 / 0-0-2 / checkmate+checkmate / 1876bbda`; p3 `0.00 / 0-0-2 / checkmate+checkmate / 5b5fcfb1` |
| 59012 | 7 / `000000-owner-0,1; 000001-owner-0,1; 000002-owner-1; 000003-owner-0,1` | 0, 1, 3 | p0 `0.50 / 1-0-1 / checkmate+checkmate / 25a3cf8f`; p1 `0.00 / 0-0-2 / checkmate+checkmate / e1187547`; p3 `0.25 / 0-1-1 / checkmate+repetition / 5b5fcfb1` |
| 59013 | 0 | none | no R10 games |

The overlapping complete pair indices for 59011 and 59012 are `0, 1, 3`.
These unequal-exposure records are behavioral evidence only; they are not
winner-selection authority.

## Cached behavioral fingerprint

All three candidates selected the same action on all three named Stage-0 roots:
`D0_RANDOM_REACHABLE`, `D1_V2_SELFPLAY`, and `D2_V2_PV_CORRIDOR`. Those roots
remain explicitly marked as opening smoke roots, not D0/D1/D2 distribution
evidence.

On 96 already persisted F62 roots, candidate top-action agreement and cached
ordering differences were:

| comparison | top-action agreement | roots with ordering difference | rank disagreement total | effectively indistinguishable roots |
|---|---:|---:|---:|---:|
| 59011 vs 59012 | 89/96 (0.9271) | 36 | 107 | 0 |
| 59011 vs 59013 | 90/96 (0.9375) | 40 | 113 | 0 |
| 59012 vs 59013 | 95/96 (0.9896) | 29 | 86 | 0 |

The exact observable definition is the three Stage-0 selected actions followed
by the 96-root cached top-action sequence. Under that definition there are
three empirically distinguishable behavior classes: class 0 = 59011, class 1
= 59012, and class 2 = 59013. This is a routing result, not a permanent
elimination or a strength claim.

## Active witness

One primary witness is sufficient; no reserve is selected yet.

| field | value |
|---|---|
| F62 root index | 84 |
| position key | `ca4bc3b1d680f82ad2e24faf1ef97214300a2b7ab05278e56ded084a90688d20` |
| provenance | `F62_OPENING_20_9508ed917e0201d4e0b614967e26279094c24c366d938b80811463d1c7ce961a`, `development` split |
| reason | 59013-focused cached rank disagreement; no root made 59013 differ from both alternatives; root 84 maximized tied rank difference, then relevant margin, then lower index |
| 59011 | top `P g21 [6,2]->[6,3]`; top-two margin `67210.50` |
| 59012 | top `P g21 [6,2]->[6,3]`; top-two margin `48904.57` |
| 59013 | top `P g21 [6,2]->[6,3]`; top-two margin `61708.63` |

At this witness all three candidates share the same top action, but their
cached remainder ordering differs materially; the 59013-vs-(59011,59012)
combined rank disagreement is maximal among the eligible cached roots. The
full seven-action orders and scores are in the immutable runtime evidence file.

## Existing-game validation and routing deduction

The existing game-v1 validator was run against all 15 persisted R10 game
files. It verified the manifest-bound pair/owner identities, parent and child
checkpoint identities, common opening identities, equal 2,000-node role
budgets, legal replay, terminal semantics, telemetry, and complete-pair
status. It reproduced the reported complete-pair scores exactly.

This permits a zero-new-game routing deduction, without treating R10 as a fair
three-way tournament:

| seed | complete-pair scores | routing bound |
|---|---:|---|
| 59011 | `0.00, 0.50, 0.00, 0.00`; mean `0.125` | `HISTORICAL_STRENGTH_FAIL` |
| 59012 | `0.50, 0.00, 0.25`; observed total `0.75` | even missing pair score `1.00` gives `(0.75+1.00)/4 = 0.4375 < 0.5`; `HISTORICAL_STRENGTH_FAIL_LOCKED` |

The missing 59012 game was not completed.

## Single-candidate active witness result

The authorized test used only seed 59013 against Gen1 at the cached root-84
witness above. It ran exactly two swapped-role games, with 2,000 nodes per
move and a 64-ply cap. Both games reached the cap while ongoing:

| child owner | result | cap | wall seconds |
|---:|---|---|---:|
| 0 | `UNRESOLVED` | `per_game_plies` | `465.504` |
| 1 | `UNRESOLVED` | `per_game_plies` | `246.174` |

The pair is incomplete and has no score. New search-work was bounded at
`128,000` nodes/game and `256,000` nodes total. No Arena/Heavy continuation,
reserve witness, or larger stage was launched. Runtime witness and result
artifacts are retained under `.generic_chess_flow/f63-r2-r2-single-candidate-active-witness/`.

This unresolved pair does not establish a strength result for 59013; it only
prevents declaring the candidate route supported from this witness.

## Smallest proposed next experiment — not run

No further experiment is authorized by this closeout. The 59011/59012 tests
were eliminated by the validated arithmetic bounds, while 59013's one pair is
unresolved. Any follow-up must be a new Courier work order that first uses the
smallest decision procedure and a fresh resource estimate; it must not repeat
59011/59012, complete 59012's missing R10 game, or silently reinterpret the
two unresolved games as a score.

Stop conditions are explicit: stop after those complete pairs; stop selection
if any pair is incomplete or unresolved; do not infer a winner from the
historical unequal R10 exposure; do not resume the stopped R10 run; and do not
expand to a larger Arena unless the smallest test remains decision-relevant
and a new work order authorizes it.

Status: `59013_UNRESOLVED_SINGLE_PAIR`; promotion: `HOLD`.
