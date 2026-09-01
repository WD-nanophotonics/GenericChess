# ADR-105 — F38 activity and anchor-control evaluator prototype

- Status: F38 audit PASS — parity diagnosis selected
- Date: 2026-09-01
- Work order: `GENERICCHESS-F38-ACTIVITY-AND-ANCHOR-CONTROL-EVALUATOR-PROTOTYPE`

## Decision

Freeze the independent holdout-selection protocol before any R37C candidate
scoring. H38A replays the already-frozen F30 R1 paired transcript in canonical
game/event order and selects the first AlphaSho board/drop action per game that
is legal, ongoing, 8–64 additional plies from the imported root, outside all
F37 ten-root/direct-child states, and not a duplicate selected canonical state.

Selection records provenance, exact replay state, state hash, played move, and a
legality witness. It never reads evaluator scores/ranks and never invokes
AlphaSho. The resulting descriptor contains 20 unique positions and meets the
minimum of 16.

## Authority and safety

The H38A manifest binds the actual SHA-256 identities of F37 first-pass/R1
evidence, F36 selection, F30 R1 paired/fresh evidence, the F25 ten-root
descriptor, and the production evaluator/profile/config sources. R37C is fixed
as the selected F37 candidate; no tuning from results is permitted; the
external holdout is validation data only; production diff is zero.

H38A was published before H38B scoring. H38B then found exact static score
identity on 290 F37 roots/children and equal generic Shogi/Western/mixed
witness scores, but the prototype did not reproduce the retained search at
either 512 or 2048 nodes on the original ten roots (0/10 exact identities at
each budget). The measured holdout static signal also failed: mean rank change
was -28.09%, top-3 was 8 versus 9, 10/20 positions worsened, and 5/20
worsened by more than three ranks. Cost passed at 0.688x median and 0.695x
p95; holdout search cost passed and 2-second safety had zero depth regressions
and zero new fallbacks, while the 2048 holdout signal was only 3 hits versus 2.

The audit therefore closes PASS with the measured boundary
`F38A_R37C_PROTOTYPE_PARITY_DIAGNOSIS`. R37C is not implementation-eligible;
F38 remains audit/prototype-only and does not modify production evaluator or
search code.

## Evidence index and verification

H38A protocol commit: `a0f76848cc119c6336a03ce0bf9e7bde76cb0f37`.
The frozen descriptor contains 20 positions; descriptor SHA-256 is
`a2be225db01c940d6c32181a713cd0398309ff4b630624d338d3b952ed4e9131`, and the
current H38A manifest SHA-256 is
`a97b87511f2ea5ad0d4a7c02288ee57adb7d99fd50a57265b336fad6aecf5f52`.

H38B durable evidence is recorded in the prototype audit script, the identity,
holdout-rank, micro-cost, holdout-search, and selection fixtures, and the
companion F38 tests. The generic-transfer contract passed all three independent
witness families (Shogi-like, Western-chess-like, and mixed-mechanic), while
the original ten-root search identity was 0/10 at both 512 and 2048 nodes.
The final selection fixture is the authoritative gate summary and records
`F39_IMPLEMENTATION_ELIGIBLE=false`.

Focused F38/F37 regression passed 11/11. Fresh full regression collected 1251
tests and passed 1238; the only 13 failures are the documented historical
F13 (4), F14 (2), F21 (6), and F24F (1) failures. The production scope check
remained zero throughout.
