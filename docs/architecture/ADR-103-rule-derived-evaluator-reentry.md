# ADR-103 — Rule-derived evaluator re-entry

- Status: Accepted F37 audit result; production integration is not authorized
- Date: 2026-09-01
- Work order: `GENERICCHESS-F37-RULE-DERIVED-EVALUATOR-REENTRY`

## Decision

F37 decomposed evaluator-v1 exactly on every legal child of the ten frozen
Standard-Shogi roots, then tested three predeclared representations without
changing production. All local semantic/genericity contracts and all three
micro-cost gates passed.

R37A replaces the global union pseudo-control term with per-piece realized
activity divided by the same piece's empty-board potential. R37B replaces only
anchor escape with pseudo-control over the bounded anchor ring. R37C applies
R37A and R37B together. Material, hand inventory, promotion, check penalty,
perspective, weights, and search architecture remain unchanged in every audit
candidate. No coefficient or scale was fitted.

## Historical ledger and exclusions

ADR-066/067/068/070/074/075, the F24A result, and F31/F36 rank evidence were
consumed and hashed in the frozen manifest. F24A remains authoritative:
extremely cheap, top1 delta 0, no production integration. Its four-term
representation, the old full dynamic F23 leaf, fitted coefficients, game or
piece tables, legal-action generation, full attack maps, and history-linked
tactics remain excluded from F37.

## Evidence

V1 recomposition parity is exact for every measured legal child. Among the six
F36 `SEARCH_STABLE_VALUE_MISMATCH` roots, the largest v1 term delta was global
pseudo-control in 8 of 12 AlphaSho comparisons, anchor escape in 3, and
material was tied in 1; this is a measured decomposition, not a feature-name
inference. F31 forced-candidate context for those roots was 5 remaining worse
through depth 2 and 1 catching/equalizing.

Static rank gates were kept separate: v1 has AS0.50 gap 8/10 and AS2.00 gap
6/10. R37A produced 6/10 and 6/10 but only 2/6 stable strict improvements,
3/6 worsened, and lost control preservation, so it was not admitted. R37B
produced 3/10 and 2/10, with 5/6 strict improvements and 1/6 worsened.
R37C produced 1/10 and 1/10, with 6/6 strict improvements and 0/6 worsened.
Both B and C preserved all v1 top-three controls and passed the static gate.

Five-repetition independent evaluator cost ratios were approximately:

| Candidate | median/v1 | p95/v1 |
| --- | ---: | ---: |
| R37A | 1.41x | 1.37x |
| R37B | 1.27x | 1.23x |
| R37C | 1.48x | 1.43x |

R37B and R37C passed fixed-node search cost and signal gates. At 512 nodes
their median NPS ratios were 0.984 and 0.943; at 2048 they were 0.987 and
0.965. Hits at 2048 improved from v1 2/10 to 4/10 (R37B) and 6/10 (R37C),
with no existing v1 hit lost. The 2.00-second safety shadow had no new
fallbacks; depth regressions were 1/10 for R37B and 0/10 for R37C.

The exact lexicographic selection inputs were:

- R37B: gap sum 5, stable strict improvements 5, 2048 hit improvement 2,
  median cost ratio 1.248x.
- R37C: gap sum 2, stable strict improvements 6, 2048 hit improvement 4,
  median cost ratio 1.473x.

R37C therefore wins by the frozen ordering. The next boundary is
`F38_ACTIVITY_AND_ANCHOR_CONTROL_EVALUATOR_PROTOTYPE`. Even that prototype
requires a separate work order; F37 retains no production change.

## Scope and verification

F37 production diff is zero. AlphaSho, paired benchmark, AlphaChess, Native,
search policy, qsearch, runtime, rules, and promotion were not rerun or
modified. All six F37 flags are true. Focused F37 tests pass; the full
regression retains exactly the historical F13 (4), F14 (2), F21 (6), and F24F
(1) failures, with no new failure.

