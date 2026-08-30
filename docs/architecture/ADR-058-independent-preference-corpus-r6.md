# ADR-058: Independent preference corpus R6 and combined V8

- Status: Accepted as F23O evidence; advancement gate not passed
- Date: 2026-08-30
- Work order: `GENERICCHESS-F23O-INDEPENDENT-PREFERENCE-CORPUS-R6`
- R6 candidate-plan SHA-256: `60574b17c45cd16533ce25b11287fef56b2f498020ac7966f25e2b76c725407f`
- V7 source SHA-256: `57d0d40ad4e74815ca1c542c2fa680750ea8a6411e47249a3892f23954dd064b`

## Decision

Retain the 12 valid V7 preference orbits and add a frozen R6 plan with 32 new
family-native candidates. R6 covers the four underrepresented families from
the V7 diagnosis, eight candidates per family, with six or more source
lineages per family. The plan records exact states, candidate ordering,
lineage IDs, solver ladder, split algorithm, and candidate count before any R6
solve.

The R6 split reuses the established deterministic contract:
`int(sha256("F23N-V7|" + source_lineage_id)[:8], 16) mod 4 == 0` means HOLDOUT;
all other lineages are DEVELOPMENT. Siblings in one lineage stay together.
The V3 exact threshold/runtime solver is the authority at SMALL (2,000 nodes),
MEDIUM (20,000), and LARGE (100,000), with `max_depth=None`, each using the
compiled `max_ply` horizon and an 8-second wall safety cap.

## V7 diagnosis

The deterministic diagnosis is implemented by
`scripts/audit_f23n_v7_family_diagnosis.py`.

| Family | Planned | Solved | Preference | All-equal | Unresolved | Effective | DEV/HOLDOUT | Main diagnosis |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| ordinary anchor movement | 8 | 8 | 8 | 0 | 0 | 8 | 6/2 | none |
| capture/recapture | 8 | 6 | 4 | 2 | 2 | 4 | 4/0 | all-equal, unresolved, split thin |
| drop/hand | 8 | 2 | 0 | 2 | 6 | 0 | 0/0 | all-equal, unresolved, diversity/split thin |
| promotion choice | 8 | 8 | 0 | 8 | 0 | 0 | 0/0 | all-equal, diversity/split thin |
| semantic guard/auxiliary | 8 | 0 | 0 | 0 | 8 | 0 | 0/0 | unresolved, diversity/split thin |

The diagnosis was used only to choose R6 families. It does not declare any
family unsuitable based on V7's particular state grid.

## V8 result

The generated artifact is `tests/fixtures/evaluator_v2_corpus_v8.json`, built
by `scripts/build_f23o_preference_corpus_r6.py`.

| Measure | Result |
| --- | ---: |
| New R6 planned | 32 |
| New R6 exact solved | 32 |
| New R6 preference-bearing | 18 |
| New R6 all-equal | 12 |
| New R6 exact/no-witness | 2 |
| New R6 unresolved | 0 |
| Retained V7 preference orbits | 12 |
| Combined physical preference roots | 30 |
| Combined canonical/effective roots | 28 |
| Combined DEVELOPMENT effective roots | 23 |
| Combined HOLDOUT effective roots | 5 |
| DEVELOPMENT construction families | 4 |
| DEVELOPMENT mechanic families | 4 |
| HOLDOUT construction families | 3 |
| DEVELOPMENT multiply-dependent roots | 23 |
| DEVELOPMENT roots not materially max-ply-dependent | 16 |
| DEVELOPMENT W/D/L partition signatures | 3 |
| Behavioral/source-lineage leakage excluded | 1 / 0 |

R6 family results were: capture 8 solved / 7 preference / 1 all-equal;
drop 8 solved / 4 preference / 2 all-equal / 2 exact without witness;
promotion 8 solved / 1 preference / 7 all-equal; semantic 8 solved / 6
preference / 2 all-equal. New preference roots had mechanic witnesses wherever
they were eligible. Combined signatures are `DRAW/WIN`, `DRAW/LOSS`, and
`DRAW/LOSS/WIN`.

## Gate and next boundary

The combined gate passes the effective-count, four-family, four-mechanic,
three-HOLDOUT-family, deep-proof, partition-diversity, and max-ply criteria.
It fails because HOLDOUT has 5 rather than 6 effective roots, capture is over
35% of DEVELOPMENT effective roots, and one behavioral orbit crosses the
combined V7/R6 split and is excluded. Source-lineage leakage is zero.

The selected next boundary is `F23P_REFERENCE_PREFERENCE_CORPUS_R7`. No F23P
prototype is implemented by this ADR.

## Integrity and scope

V1–V7, F23F, all F23K/F23L/F23M capability fixtures, and F23M V4R1 full and
summary evidence remain byte-identical. Production evaluator/search/Native
behavior and repository governance are unchanged. V8 is reference-only and
does not inspect external scoring, feature, or reference sources. Permanent
tests cover the frozen plan SHA, deterministic lineage split, complete exact
certificates, runtime balance, witness coverage, all-equal exclusion, combined
leakage, historical immutability, and next-boundary selection.
