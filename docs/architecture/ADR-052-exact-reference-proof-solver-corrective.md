# ADR-052: Exact reference proof solver corrective R1

## Status

F23K corrective R1 completed. Solver correctness and horizon contracts are
sound on the fixed tests, but the capability gate still fails. The next
boundary remains `F23L_EXACT_REFERENCE_SOLVER_FOUNDATION_R2`.

## Soundness corrections

The versioned V2 solver no longer writes a TT entry when a node is unresolved
because of a node cap, depth cap, cycle, or unresolved descendant. This removes
the unsafe synthetic-zero bound path. Complete searches may retain typed
`EXACT`, `LOWER`, or `UPPER` entries, and a non-exact child is re-searched with
the full proof window before it can certify a parent or root action. Every
strong root still has an exact W/D/L for every legal root action.

The solver now supports `max_depth=None`, which derives the search horizon from
the compiled RuleSet's authoritative `max_ply` and current `ply_count`. An
explicit integer depth remains a diagnostic refusal cap. Both modes retain an
independent node safety cap and full future-relevant state/history keys.

## Capability-v2 benchmark

The five fixed non-control F23J representatives were rerun without changing
their states or choosing easier replacements. The frozen ladder is SMALL = 20
nodes, MEDIUM = 50 nodes, and LARGE = 100 nodes, all with authoritative
horizon mode. None resolved; all were explicitly classified as
`NODE_EXPLOSION` at the fixed budgets. The historical auxiliary control remains
covered by capability-v1 and by the F23K differential suite.

This is a bounded capability finding, not a correctness failure. The new
solver's legacy differential parity remains zero-mismatch for root values,
root-action values, and complete optimal action sets on all tested oracle
cases. Terminal winner mapping, including perpetual-check WIN/LOSS, remains
covered. V1–V6 and capability-v1 remain byte-identical.

## Decision

Do not expand the corpus, create V7, fit Evaluator V2, or weaken exact
certification. Continue with F23L exact-reference efficiency/history work to
make the fixed independent mechanics tractable under a declared budget ladder.
