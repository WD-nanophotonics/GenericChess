# ADR-059: Reference preference corpus R7 and V9 accounting

- Status: Accepted as F23P evidence; revised advancement gate not passed
- Date: 2026-08-30
- Work order: `GENERICCHESS-F23P-REFERENCE-PREFERENCE-CORPUS-R7`
- R7 plan SHA-256: `6c1b0bbc236a5ca2e65787c5771766c51710ad92464b8f6227cc2e5f0b75139f`
- V8 source SHA-256: `b35d5898bb4d3b3533802311e68541b9c602c65ccd2a77251bb9b24f8ff5cda7`

## Decision

Create V9 as one final bounded non-capture reference-corpus expansion. The
frozen R7 plan contains 24 candidates: eight drop/hand, eight optional
promotion, and eight semantic-guard constructions. Each source lineage ID is
derived from its canonical lineage key; the plan does not search or alter names
to target a split. The V3 exact solver remains authoritative, with the same
SMALL/MEDIUM/LARGE ladder and 8-second safety cap. Horizon checks are +2 and
+4; unknown horizon sensitivity is never counted as stable evidence.

## V8 diagnosis

V8 had 23 eligible DEVELOPMENT and 5 eligible HOLDOUT roots. Capture supplied
9 DEVELOPMENT roots (39.130435%); with capture fixed, at least 3 additional
non-capture DEVELOPMENT roots are mathematically required to reach the 35%
ceiling. HOLDOUT was short by 1. The observed cross-split behavioral collision
was retained as diagnostic evidence for the R6 semantic roots
`generic-f23o-r6-semantic-05` and `generic-f23o-r6-semantic-07`; no residual
eligible overlap remained after exclusion.

## V9 result

The generated artifact is `tests/fixtures/evaluator_v2_corpus_v9.json`, built
by `scripts/build_f23p_preference_corpus_r7.py`.

| Measure | Result |
| --- | ---: |
| New R7 planned | 24 |
| New R7 exact solved | 24 |
| New R7 preference-bearing | 11 |
| New R7 all-equal | 11 |
| New R7 no-witness | 2 |
| New R7 unresolved | 0 |
| Combined effective roots | 27 |
| Combined DEVELOPMENT | 22 |
| Combined HOLDOUT | 5 |
| DEVELOPMENT construction/mechanic families | 5 / 5 |
| HOLDOUT construction families | 3 |
| DEVELOPMENT multiply-dependent | 22 |
| Certified stable/natural DEVELOPMENT horizon roots | 1 |
| DEVELOPMENT partition signatures | 3 |
| Observed cross-split behavioral orbit IDs | 3 |
| Residual eligible behavioral/source-lineage leakage | 0 / 0 |

All eligible roots are W/D/L-diverse with complete root-action certificates,
balanced runtime accounting, and causal mechanic witnesses. R7 family counts
were drop 8 solved / 4 preference / 2 all-equal / 2 no-witness; promotion 8
solved / 1 preference / 7 all-equal; semantic 8 solved / 6 preference / 2
all-equal.

## Gate and next boundary

The corrected gate passes effective count, family coverage, partition diversity,
and residual-leakage requirements. It fails HOLDOUT minimum (5/6), the
DEVELOPMENT family concentration ceiling, and the conservative non-max-ply
minimum because 16 roots are horizon-unknown. The observed collision count is
kept separate from residual leakage and does not itself fail the gate.

The selected next boundary is `F23Q_REFERENCE_PREFERENCE_CORPUS_R8`. No F23Q
prototype is implemented by this ADR.

## Integrity and scope

V1–V8, F23F, F23K/F23L/F23M capability evidence, the F23O R6 plan, and
ADR-058 remain byte-identical. No production evaluator/search/Native or
workflow/governance file changed. Permanent tests cover deterministic V8
diagnosis, frozen R7 plan/lineage derivation, conservative horizon accounting,
observed-versus-residual leakage, exact certificates, witness coverage,
historical immutability, and the selected next boundary.
