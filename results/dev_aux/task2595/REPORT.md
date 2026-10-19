# Task 2595 — frozen Generic-root admission failure

**Status:** `SEED_ADMISSION_FAILED`; learner fitness was never started. Scientific status remains OPEN. The only registered generator seed was 364005. Preserve this failed registration and do not substitute a rule seed, regenerate this rule, choose replacement evaluation roots, or run learner fitness on its frozen roots.

## Frozen admission result

The complete generated rule serialized, round-tripped, and compiled. The K anchor, A/P/X non-anchor set, promotion target, drop reachability for both players, and initial-position legality passed. The predeclared root gates failed: evaluation histories were 28 unique of 32; 17 evaluation histories overlapped TRAIN; and 22/32 evaluation roots were nonterminal/legal (minimum 24). `registration.json` and `admission-review.json` retain the exact counts and source/artifact hashes.

## Root-cause diagnosis

The four-ply family sampler in `task2565/train.py` draws legal moves uniformly with replacement from each family-specific PRNG stream and stops at terminal positions. The immutable TRAIN manifest contains 8,192 rows but only 3,702 distinct serialized histories (4,490 duplicate excess). There are 3,031 terminal/no-legal-action prefixes: 1,520 stop after one ply, 891 after two, and 357 after three; all of these short prefixes are terminal. Among four-ply rows, 263 also end terminal/no-legal-action.

A descriptive replay of only the fixed initial position found 16 legal first moves; 3 immediately end the game. These are zero-based coordinate moves `(0,1)->(1,2)`, `(2,0)->(3,3)`, and `(2,1)->(1,2)`. Their probability under the frozen uniform first-move sampler is 3/16, close to the observed one-ply fraction 1,520/8,192. This explains much of the early termination and duplicate concentration for this one generated rule. It does not show either learner works or fails, and it is not a population claim about Generic rules.

The admission script additionally reports 3,702/8,192 TRAIN uniqueness as a failure. TRAIN-root mutual uniqueness was not listed as a design gate; treat that field as a descriptive diagnostic, not a fourth registered failure. The three actual preregistered failures above suffice to reject fitness.

## Future protocol correction (not applied to task 2595)

Before any *new* task exposes rules or starts fitness, freeze a bounded deterministic root-generation/admission algorithm and its target distribution. Canonicalize complete history records; generate TRAIN and EVAL through separate predeclared streams; require EVAL roots to be mutually unique, legal/nonterminal under the declared estimand, and disjoint from TRAIN. If using deterministic rejection sampling, freeze the candidate-family range, rejection rules, target count, and hard stop in advance; report all rejected candidates and the resulting conditional sampling target. If the cap cannot fill the set, retain an admission failure rather than expanding the range. Report effective unique TRAIN histories and terminal fractions descriptively; do not retroactively turn these into gates. The older task2592 scan is not presumed sufficient: its source appends non-TRAIN candidates without checking uniqueness among EVAL candidates.

This correction is design guidance only. It does not reopen task 2595, authorize another seed, or make its rejected roots available for another attempt.

## Verification scope

`diagnose_training_roots.py` reads the registered rule, initial position, and TRAIN rows only. The registered EVAL root rows were not examined by this follow-up diagnostic; their already-frozen admission summary remains in `admission-review.json`. No rule was regenerated, no replacement seed or EVAL family was selected, and no training/evaluation fitness run was launched. No production code or defaults changed.
