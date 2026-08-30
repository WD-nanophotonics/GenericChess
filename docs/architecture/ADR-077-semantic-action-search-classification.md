# ADR-077: semantic action search-classification parity

## Status

F24B is complete and passes its bounded classification, ordering, semantic
Standard Shogi, and search-smoke gates. The next boundary is
`F24C_MIXED_MECHANIC_RULESET_CERTIFICATION`. F24A remains deferred and
production evaluator-v1 remains authoritative.

## Decision

Use one small public-action-shape abstraction for the four existing action
classes: board/drop classification, source square, target square, promotion
target, and drop base type. The abstraction is shape-based and preserves the
actual action object, including `pattern_id` and `geometry_id` on semantic
actions. It does not redesign the Action hierarchy, convert semantic actions
to legacy actions, inspect game names or piece IDs, or analyze arbitrary
semantic side effects.

The bounded capture rule is a direct target occupancy check against the
pre-action position. Promotion is the public non-null promotion target. These
rules apply equally to `BoardMove`/`SemanticBoardMove` and do not classify
off-target semantic removals. Drops retain their existing main-ordering
behavior; only qsearch drop diagnostics distinguish checking and nonchecking
drops for both drop action shapes.

The runtime qsearch mirror uses the same helpers because semantic Standard
Shogi uses the runtime path. This keeps action classification aligned without
adding legality generation, successor generation, attack probes, effect
replay, or recursion.

## Evidence

The compact F24B fixture records the executable before/after matrix at
`tests/fixtures/f24b_semantic_action_search_classification.json`. Focused
tests cover quiet board moves, direct captures, promotions, capture-plus-
promotion shape, checking and terminal board moves, checking/nonchecking
drops, ordering stages, semantic identity, and no duplicate inclusion.

Current semantic Standard Shogi cases include a legal nonchecking capture, a
legal promotion, an ongoing checking drop, a nonchecking drop control, and a
runtime-qsearch capture. The F22 smoke ran 10 frozen positions at 128 and 512
nodes, twice per position/budget, with fresh search state. All declared node
budgets completed, runtime push/pop counts balanced, and repeated results
matched. Native availability was unchanged, so the recorded mode is
`PYTHON_AUTHORITY_FALLBACK`.

## Scope and next boundary

The production diff is limited to action helpers, qsearch classification,
ordering classification, and the runtime qsearch mirror; evaluator/profile,
rules compiler, semantic executor, SearchPathRuntime identity/repetition,
workflow, and promotion state are untouched. No playing-strength claim is
made by these classification counters or smoke results.

F24C must certify victim-type-specific capture disposition: Shogi-family
victims, including promoted forms, go to the capturer's hand as base type;
Western/Xiangqi-style victims are removed; disposition follows victim family,
only Shogi-family pieces are droppable, promotion eligibility remains
family-specific, and Xiangqi-style path constraints remain enforced.
