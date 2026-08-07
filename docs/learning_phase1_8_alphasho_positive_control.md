# Learning Phase 1.8: AlphaSho Positive Control & Learning-Direction Audit

## Question

Using the local AlphaSho shogi project as a **read-only external positive
control**, split the previous null learning result into four independent
variables:

1. rule correctness (standard shogi expressible by the generic schema?);
2. GenericChess search itself (same human material as a legacy engine?);
3. generic auto (rule-derived) material quality;
4. frozen TD learned-material direction (scale vs orthogonal vs human).

## Learner freeze

`tdleaf.py`, `features.py`, `selfplay.py` are byte-identical to Phase 1.6/1.7
(`1da38ee` baseline); native search is untouched.  No `if shogi` special
cases were added anywhere in Core; the shogi ruleset is expressed through the
generic schema v1.

## AlphaSho read-only audit (Stage A)

* Path: `C:\Users\icywo\PycharmProjects\alphasho`
* HEAD: `61c35fa70ca1f59264045ad1425d6757ad6666a2` (branch
  `codex/web-last-move-highlight`), working tree clean.
* Legacy control: `benchmarks/legacy_3262cc8.py` (exact frozen copy of
  commit `3262cc8`):
  * material-only negamax + transposition table (dict), iterative
    deepening, capture ordering, mate scores `±(MATE − ply)`;
  * `PIECE_VALUES = (0, 100, 300, 320, 450, 800, 1000, 520, 0, 520, 520,
    520, 520, 950, 1150)` in cshogi order
    (P L N S B R G K +P +L +N +S +B +R);
  * `HAND_VALUES = (100, 300, 320, 450, 520, 800, 1000)` in P L N S G B R
    order;
  * one non-material term: `score − 35` when in check
    (`EVALUATOR_NONMATERIAL_DELTA`).
* Current/full: `heuristicplayer/evaluation.py` adds piece-square,
  mobility, king safety, tempo and a check penalty, and the engine has
  mature ABP profiles (PVS/aspiration, SEE, LMR, null move, qsearch).
  The legacy/current distinction is kept strictly separate in this audit.
* cshogi is used by AlphaSho as its rules oracle; Python 3.13.2.
* Benchmark protocol (`docs/ABP_BENCHMARK.md`): 1s/move, 10 paired
  positions, max 256 plies, unresolved/fallback/timing-invalid excluded,
  paired scores with bootstrap CI.

## Generic shogi ruleset (Stage B)

`generic_chess/learning/shogi_rules.py` builds the standard shogi RuleSet
through schema v1: 9×9, all 14 piece types (P L N S G B R K + promoted
TP TL TN TS TB TR), promotion zone = last three ranks (optional; forced on
dead-rank destinations), captures to hand (base type), drops with static
per-square masks, anchor king, repetition 4-fold draw.

### Known generic rule-model gaps (`GENERIC_RULE_MODEL_GAP`)

| rule | expressible | effect |
| --- | --- | --- |
| nifu (double pawn) | no | pawn drops on a file with an unpromoted same-side pawn are legal in GC, illegal in shogi |
| uchifuzume (pawn-drop mate) | no | pawn drop delivering checkmate is legal in GC, illegal in shogi |
| perpetual-check repetition | no | 4-fold repetition is always a draw in GC; shogi makes the checking side lose |
| nyugyoku | no | king-entry win is not in the GC terminal model |
| stalemate | deviation | GC declares stalemate draw; shogi has no stalemate rule |

## Rule parity (Stage C)

Adapter: GC Position ↔ SFEN, GC Action ↔ USI, and cshogi legal moves with a
documented convention (king-capture moves are game-terminating and excluded,
matching GC's uncapturable anchors).  Curated cases cover initial position,
normal move, optional promotion, dead-rank drop, promoted piece, white-hand
drop, nifu and uchifuzume.  Large differential uses deterministic random
legal play via cshogi (fixed seed).

## Material reference & geometry (Stages C/D)

`GC-Human` = GenericChess search + AlphaSho legacy material table (scale
normalized; the −35 check penalty is recorded as
`EVALUATOR_NONMATERIAL_DELTA`, not injected).  Geometry compares the
rule-derived Gen0 profile of the shogi ruleset against the human reference:
best-fit scale, cosine, Pearson, Spearman, pairwise ordering, per-piece
relative error, board-vs-hand relationship.

## TD scale decomposition (Stage E)

For frozen R2 checkpoints (seeds 7/8/9, Gen0..Gen3):

```
delta = w_g − w_0
u_scale = w_0 / |w_0|
scale energy fraction = |(delta·u_scale)u_scale|^2 / |delta|^2
```

Pre-registered thresholds: ≥ 0.75 DOMINANT, 0.40–0.75 SUBSTANTIAL,
< 0.40 MINOR.  A global rescale is strategically inert (Phase 1.7: global
scale 0.5–1.5 → 0% move flips), so a large scale fraction means the TD
update is partly wasted on a low-leverage direction.

## Gates

`SHOGI_RULE_PARITY = FAIL` blocks stages F–J (human-direction
interpolation/search, shogi training, random sanity, cross-engine matches).
Static audits that do not depend on the missing semantics (material
reference, geometry, R2 scale decomposition) still run.  This follows the
phase's decision tree: parity failure ⇒
`NEXT_PHASE_DECISION = FIX_GENERIC_SHOGI_RULE_EXPRESSIVITY`.

## Results

Full run (GC commit `a695fd6`, project `0.8.0a5`, native `0.3.0`; AlphaSho
HEAD `61c35fa` unchanged before/after).  Artifacts in
`artifacts/learning_phase1_8/*.json`.

### Curated rule parity

6/8 curated cases pass exactly (initial position, normal move, optional
promotion, dead-rank drop, promoted piece, white-hand drop).  Two diverge,
both mapped to `GENERIC_RULE_MODEL_GAP`:

* **nifu**: GC is legal for 7 pawn drops on a file that already holds an
  unpromoted same-side pawn (`P*5b..P*5h`) that cshogi forbids.
* **uchifuzume**: GC is legal for `P*1b` (a pawn drop that delivers
  checkmate) that cshogi forbids.

### Large rule parity (10,000 reachable positions, seed 20260807)

6,972 / 10,000 exact set equality; **3,028 divergences (30%)**, all with
`missing_in_gc = []` and `extra_in_gc` consisting of pawn drops that nifu
forbids.  First divergence at position index 57 (ply 58).  The static drop
mask cannot express "no second pawn on the file", so the gap is frequent in
real play, not just an edge case.

### SHOGI_RULE_PARITY

**FAIL** (curated divergences; the large differential confirms the gap is
not rare).  Root cause is generic-schema expressivity, not an encoding bug:
everything expressible by the schema matches cshogi exactly.

### Material reference & geometry

Legacy human material (cshogi order): P=100, L=300, N=320, S=450, B=800,
R=1000, G=520, K excluded; promoted P/L/N/S=520, horse=950, dragon=1150;
hands P=100, L=300, N=320, S=450, G=520, B=800, R=1000.  The legacy
`score − 35` check penalty is recorded as `EVALUATOR_NONMATERIAL_DELTA` and
is not injected into the GC material framework.

Rule-derived GC Gen0 profile vs human reference (20-dim vector):

| metric | value |
| --- | ---: |
| best-fit scale c* | 1.972 |
| cosine similarity | 0.989 |
| Pearson | 0.976 |
| Spearman | 0.952 |
| pairwise ordering accuracy | 0.965 |

The generic rule-derived material for shogi is already **very close to the
AlphaSho human material** (`AUTO_MATERIAL_QUALITY = CLOSE_TO_HUMAN`),
with the GC profile roughly 2× the human scale (scale itself is
strategically inert).

### TD scale decomposition (frozen R2 checkpoints)

| seed | Gen1 | Gen2 | Gen3 |
| --- | ---: | ---: | ---: |
| 7 | 0.686 | 0.689 | 0.692 |
| 8 | 0.286 | 0.305 | 0.319 |
| 9 | 0.600 | 0.599 | 0.599 |

Mean scale-energy fraction **0.531 → SUBSTANTIAL** (pre-registered
thresholds: ≥0.75 dominant, 0.40–0.75 substantial).  Seeds 7/9 spend ~60–69%
of the TD update energy along the globally-scaled Gen0 direction (which
Phase 1.7 showed is strategically inert), while seed 8 spends ~29–32%.

### Blocked stages

`SHOGI_RULE_PARITY = FAIL` gates stages F–J per the phase decision tree:
human-direction interpolation/search, frozen shogi training,
`TD_HUMAN_DIRECTION_ALIGNMENT`, random sanity, and cross-engine matches are
not run and are reported `INCONCLUSIVE` with the blocker reason.  A full
shogi benchmark would be a mislabeled "standard shogi" without nifu /
uchifuzume.

### Final verdicts

* ALPHASHO_AUDIT: **PASS**
* SHOGI_RULE_PARITY: **FAIL**
* GENERIC_SEARCH_CONTROL: INCONCLUSIVE (blocked)
* AUTO_MATERIAL_QUALITY: **CLOSE_TO_HUMAN** (cosine 0.989)
* HUMAN_DIRECTION: INCONCLUSIVE (blocked)
* TD_SCALE_COMPONENT: **SUBSTANTIAL** (mean 0.531)
* TD_HUMAN_DIRECTION_ALIGNMENT: INCONCLUSIVE (blocked)
* LEARNING_STRENGTH_SIGNAL: INCONCLUSIVE (blocked)
* BASIC_COMPETENCE_SANITY: INCONCLUSIVE (blocked)
* NEXT_PHASE_DECISION: **FIX_GENERIC_SHOGI_RULE_EXPRESSIVITY**
