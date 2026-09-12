# GenericChess F94-R3 executor R1 CLI binding

Status: result-free CLI binding repair only. No R3 Arena, Heavy computation, or
protocol change occurred.

The executor input is now `--r3-prep`, defaulting to the frozen
`R3_PREP_PATH`; `--r3-depth-calibration` passes exactly that path to the R3
loader. R3 PREP generation is explicitly `--r3-prep-generate`, and retains
`--r3-source-prep` solely as the source R2 Stage-0 PREP input. The two path
roles cannot overwrite one another through default argument wiring.

The CLI regression test calls both paths with mocked entry points and verifies
that the executor receives R3 PREP while generation receives R2 Stage-0 PREP.
All frozen R3 identities, budgets, depth-64 direction semantics, and result
schema are unchanged.
