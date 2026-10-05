# Shared geometry makes the finite prefix feasible

The frozen Standard Shogi13-profile constructor qualifies126 simple board
patterns. Canonicalization of equal compiled paths yields18 geometric
primitives and1458 source tables, with2768 actual candidates instead of15368
raw per-pattern endpoint tests. max quiet variants32 stays below128. Owner0
preprocessing/compilation took0.125sec; ALL whole-law counts finished in0.359sec,
including that cost, below15sec. No Core transition, goal query or virtual event
was used in this arithmetic constructor. Remaining distance>=3 mass stays unknown.

| Current (correct origin) | Exact first | Exact second | Remaining |
| --- | ---: | ---: | ---: |
| P |5688|11154|495078|
| L |24840|25392|461688|
| N |8848|24250|478822|
| S |25912|67769|418239|
| G/TP/TL/TN/TS (each) |32864|55171|423885|
| B |63120|251006|197794|
| R |99360|409536|3024|
| TB |85872|289944|136104|
| TR |119584|389564|2772|

Every row totals511920 without outcome-dependent support selection. P/Gold
frontiers match independent earlier derivations; native R's three-class law
matches too. TR's extra diagonals are ONE-square leaps, not diagonal rays,
so they cannot rescue native R's blocked-axis distance3. Native B now has an
exact second frontier beyond the prior necessary-condition censoring. The new
S2=67769 explicitly retains optional quiet promotion to Gold; independent
blocked-coordinate target unions reproduce it for BOTH owners. Full compiled
path/promotion-mask reflection checks justify transferring owner0 counts; no
second candidate sweep is hidden in the measured budget.

Why factorization is exact for the qualified task: for each(s,d), all79 blocker
placements remain. A direct path succeeds unless the blocker is in its interior.
A two-action route fails if its first quiet path passes through d, its first
destination is d, or the blocker is the intermediate/any interior path square.
The original source is absent on the second path. Union all valid semantic/
promotion descriptions, then subtract direct-success blockers from second mass.
No graph-distance abstraction, midpoint, visited-choice truncation or separate
normalization is used. Unsupported guards/effects reject the whole profile set.

The fresh independent event qualification costs42 virtual materializations and
256 per-pattern candidates in0.094sec. All six first Silver options are saved
per owner; exactly S->TS b8 followed by c8 target capture completes in2 from
a7 with blocker a1. The R b2-c2xa2 control proves final cubes REQUIRE old b2
empty. It was already a direct-contact world, so it does not inflate T2.
These are virtual grammar checks, not official positions or game-value labels.

Five prefix tests check independent S2/reflection/budget/earlier counts and
fail-closed input; three saved-event tests check source pins, complete promotion
options, custody and vacated-square constraints without rerunning producers.
The kernel is a research approximation ingredient, not a complete normalized
generic prior or independently validated search advantage. Exact long horizons,
held-mode guard support and useful deployment remain separate next questions.
