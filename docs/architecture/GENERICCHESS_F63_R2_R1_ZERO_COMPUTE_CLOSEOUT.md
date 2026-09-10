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
| F62 root index | 20 |
| position key | `bc19eaa3b66990cb9ede36b9cfeecbaaee33d57b20b873967728452d74d6feed` |
| provenance | `F62_OPENING_20_9508ed917e0201d4e0b614967e26279094c24c366d938b80811463d1c7ce961a`, `development` split |
| reason | maximizes cached candidate top-action/order disagreement |
| 59011 | top `G g5 [3,8]->[4,7]`; top-two margin `1617.15` |
| 59012 | top `K g16 [5,8]->[4,8]`; top-two margin `4203.46` |
| 59013 | top `G g5 [3,8]->[4,7]`; top-two margin `17360.44` |

At this witness the complete cached order differs materially: 59012 puts the
king move first, while 59011 and 59013 put the gold move first, and 59011/59013
also differ in the remainder of the order. The full eight-action orders and
scores are in the immutable runtime evidence file.

## Smallest proposed next experiment — not run

Use the primary witness only, with one swapped-role pair for each of the three
behavior classes: representatives 59011, 59012, and 59013. This is at most six
new games, 2,000 nodes per move, and a 64-ply cap. A game reaching the cap is
`UNRESOLVED`, not a draw or a win. No reserve witness is added unless this
first test leaves a decision-relevant ambiguity.

Stop conditions are explicit: stop after those complete pairs; stop selection
if any pair is incomplete or unresolved; do not infer a winner from the
historical unequal R10 exposure; do not resume the stopped R10 run; and do not
expand to a larger Arena unless the smallest test remains decision-relevant
and a new work order authorizes it.

Status: `DESIGNED_NOT_RUN`; promotion: `HOLD`.
