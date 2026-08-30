# ADR-057: Independent exact preference corpus R5

- Status: Accepted as F23N evidence; advancement gate not passed
- Date: 2026-08-30
- Work order: `GENERICCHESS-F23N-INDEPENDENT-REFERENCE-PREFERENCE-CORPUS-R5`
- Candidate-plan SHA-256: `2d55c020699ea629bad74f5312a3ac0c485ca7cf3878e43e7fef6a46497cb263`

## Decision

Create `evaluator-v2-corpus-v7` as a new, independent exact-reference corpus. The
frozen plan contains five construction families, eight candidates per family,
and 40 planned candidates:

1. `ordinary_anchor_movement`
2. `capture_recapture_tactics`
3. `drop_hand_tactics`
4. `promotion_choice`
5. `semantic_guard_auxiliary`

Candidates are grouped by `source_family_id` before splitting. A source family
is HOLDOUT exactly when
`int(sha256("F23N-V7|" + source_family_id)[:8], 16) mod 4 == 0`; otherwise it
is DEVELOPMENT. The proof ladder is the V3 exact solver at SMALL (2,000
nodes), MEDIUM (20,000 nodes), and LARGE (100,000 nodes), with `max_depth=None`
and the compiled `max_ply` as the authoritative horizon. Each attempt has an
8-second wall safety cap.

Only roots with at least two distinct exact W/D/L action values are preference
strong. All-equal exact roots are retained in a separate non-preference set.
Eligible roots retain all root action values, optimal actions, proof depth,
solver statistics, a mechanic witness, and a conservative behavior-certificate
fingerprint. The fingerprint includes ruleset identity, exact root action
values, proof depth, witness, and terminal adjudication counters; it is an
exact proof-certificate identity, not a claim of full semantic equivalence.

## Result

The generated fixture is `tests/fixtures/evaluator_v2_corpus_v7.json`, built by
`scripts/build_f23n_preference_corpus_r5.py`.

| Measure | Result |
| --- | ---: |
| Planned candidates | 40 |
| Exact solved | 24 |
| Preference-strong roots | 12 |
| All-equal roots | 12 |
| Unresolved | 16 |
| Effective DEVELOPMENT representatives | 10 |
| Effective HOLDOUT representatives | 2 |
| DEVELOPMENT construction families | 2 |
| DEVELOPMENT mechanic families | 2 |
| HOLDOUT construction families | 1 |
| DEVELOPMENT multiply-dependent roots | 10 |
| DEVELOPMENT roots not materially max-ply-dependent | 10 |
| Behavioral/source leakage | 0 / 0 |

All effective roots have WDL-diverse complete root-action certificates, valid
mechanic witnesses, balanced runtime push/pop accounting, and proof depth class
`MULTIPLY_DEPENDENT`. Partition signatures present are `DRAW/WIN` and
`DRAW/LOSS`.

The advancement gate is **not passed**. It fails the minimum effective counts,
family coverage, family concentration, HOLDOUT family coverage, and the
three-partition-signature minimum. The next boundary is therefore
`F23O_REFERENCE_PREFERENCE_CORPUS_R6`; no F23O prototype is implemented by
this ADR.

## Integrity and scope

V1–V6, the F23F candidate specification, F23K/V1–V2, F23L/V3, and F23M/V4
capability artifacts remain byte-identical. No production evaluator, search,
Native, or governance file is changed. The corpus is evaluator-blind and uses
the V3 exact solver as its authority; V2 is not a substitute for an unresolved
V3 result. Permanent tests cover the frozen plan digest, source-family split,
witness validity, exact certificate balance, leakage exclusions, historical
fixture hashes, and production/reference independence.
