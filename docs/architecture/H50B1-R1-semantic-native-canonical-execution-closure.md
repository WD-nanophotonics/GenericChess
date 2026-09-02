# H50B1-R1 semantic Native canonical execution closure

- Checkpoint: `H50B1-R1_F50_SEMANTIC_NATIVE_CANONICAL_EXECUTION`
- Work order: `GENERICCHESS-F50B1-CORRECTIVE-R1-NATIVE-DECLARATION-HISTORY-AND-CERTIFICATION-CLOSURE`
- Parent: `66f1186908a48692b0e5b514b34dc77c78c7ec09`
- Promotion: HOLD; no master mutation

## Decision

R1 closes the corrective gaps identified during H50B1 review. The semantic
Native path keeps `CompiledSemanticRuleset.ir + .support` and
`GCSemanticPosition` as its only semantic authorities. Declarations are
lowered as a complete C-owned contract and assessed through public Native
APIs. Python private declaration helpers are not part of the Native route.

## Certified boundaries

- Fresh positions carry one explicit history entry with sentinel actor `255`
  and `gave_check=false`; child positions append the actual actor and
  post-move check flag.
- Imported incomplete or non-sentinel event streams retain ordinary history
  only. Continuous-check and automatic adjudication paths fail closed unless
  the event stream is complete and exact.
- Automatic adjudication is represented as a complete record list. The
  Standard Shogi 500-ply record is evaluated from the full history and maps
  to `NO_CONTEST`; no first-ply special case is used.
- Western and Standard Shogi compile natively, preserve exact public action
  identity, and pass the targeted special-action and declaration matrices.
  A compiler-produced generic witness also passes without game-name branches.

The machine-readable evidence is frozen in
`tests/fixtures/h50b1_r1_semantic_native_execution.json`.

The final local Native build is 354304 bytes with SHA-256
`602984dfb9e0b1cc32cd68b9298143ca20bfa02a3cde5816d0b6a6b94c5c8fa2`.
The generated binary remains ignored and is not committed.

## Validation

The focused R1 contract, Western/Shogi semantic matrix, declaration, history,
attack/check, stress, and product tests pass. Historical validation also
passes after restoring the pre-existing evidence boundaries for F39-F41,
H49B, H50A, and F24G. The only known regression residuals are the established
F24F Kiwipete depth-1 mismatch (45 vs 48) and the unavailable external
AlphaSho `evaluation_positions.jsonl`; historical fixtures were not rewritten.

F50B2 remains `NOT_STARTED`. Iterative search, semantic TT, budgets,
cancellation, and production search routing are outside this checkpoint.
