# H50/F58 corrective: auxiliary semantics and policy gate

Date: 2026-09-04  
Parent checkpoint: `e5ca5b2767e3e01d77cc2afa876cba3ca65d4780`

## Scope

This corrective work order fixed the semantic distinction between a physically
missing auxiliary entry and an explicitly supplied clear/`None` value.  The
compact nonlinear encoder now resolves a missing entry through the compiled
slot initial value.  The Native payload carries a `supplied` bit, so packing
preserves an explicit clear without materializing it into `Position`.

No search, transposition-table, root, transport, or model-retuning change was
made.

## Aux correctness evidence

- Western castling rights are declared with logical initial value `1`, while
  the initial physical `Position.aux_state` is sparse.  Python and Native now
  encode missing `w_ks` as `1` and an explicit clear as `0`.
- A generated semantic ruleset with `square_or_none` initial `(2, 1)` now
  encodes a missing entry as `(present=1, file=2, rank=1)` and an explicit
  `None` as `(present=0, file=0, rank=0)`.
- The focused Native/Python probe compares the same compact model prediction
  on both states and checks Native snapshots; all cases pass exact integer
  parity at the stated evaluator scale.

## Fresh Western capacity audit

Protocol: 384 development + 128 validation positions, evaluator-neutral
openings, 40k/80k frozen-teacher budgets, three training seeds, widths 16/32,
regularization `1e-4/1e-3`, and development-only selection.

- Corpus: `a79f9f8dcd04a2b8486e62c657063575d6b44cfc260c5657d733560af08a1423`
- Teacher stability: 430/512 (`83.984%`); stable ordinary validation: 105
- Parent validation MSE: `1,429,075.38`
- Child MSE: `1,947,526.25`, `1,970,028.83`, `1,968,862.13`
- Mean improvement fraction: `-37.3013%`
- Classification: `COMPACT_NONLINEAR_VALUE_CAPACITY_NOT_SUPPORTED`

This is accepted as the required negative Western result; no retuning was
performed.

## Full Shogi policy/runtime gate

The frozen 80k-teacher comparison used a fresh 512-position corpus:

- Corpus: `6c2201c1716c113616fc541aa4785899ea4e7b61d42dc3d6f28f2547b3af37ac`
- Teacher stability: 470/512 (`91.797%`); stable ordinary validation: 123
- Parent teacher-best-move agreement at 2,000 nodes: `60.976%`
- Child teacher-best-move agreement at 2,000 nodes: `22.764%`
- Agreement delta: `-38.211 percentage points`
- Parent/child move flip rate: `75.610%`
- Mean absolute score displacement: `932.61` Native fixed-value units
- Average completed depth: parent `1.9512`, child `1.9512`
- Average nodes: parent `2000`, child `2000`

The child policy gate therefore failed.  The conditional 8-pair arena and
evaluation-only AlphaSho check were correctly skipped; no strength claim is
made.

Runtime on the same 32 stable validation positions and 2,000-node limit:

| evaluator | NPS | average elapsed seconds | average depth | average nodes |
|---|---:|---:|---:|---:|
| v2 parent | 988.67 | 2.0229 | 1.9375 | 2000 |
| v4 child | 490.29 | 4.0792 | 1.9375 | 2000 |

The compact v4 evaluator is approximately 2.02x slower in this unoptimized
runtime measurement.  This is recorded as an engineering cost, not a reason
to alter the search path in this work order.

## Generated-ruleset and regression gates

Generated semantic fixtures `weird_0` and `weird_1` continue to pass generic
state-vector, Native search, and dynamic-leaf checks.  The generated
`square_or_none` fixture above additionally covers nontrivial aux defaults,
serialization through the Native boundary, checkpoint-model feature parity,
and explicit-clear behavior.

Validation completed:

- `tests/test_f58_compact_nonlinear.py`
- `tests/test_f50_generic_learnable_evaluator.py`
- `tests/test_h50b2e_semantic_search_engine.py`
- Result: 23 passed
- `git diff --check`: clean
- `scripts/build_native_zig.py`: Native extension rebuilt successfully

## Decision

Aux semantics are corrected and covered.  Western capacity remains negative,
and Shogi compact nonlinear policy fails the required teacher gate; therefore
the v4 checkpoint remains an experimental/offline child and is not eligible
for promotion as a stronger evaluator.
