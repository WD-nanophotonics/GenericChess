# Generic CLI action-input coverage — 2026-10-20

## Finding and decision

The existing CLI resolver crashed when a legal action set contained
`PassAction` and a user entered anything other than an exact action string.
`_resolve_action_input()` scans visible aliases after an exact-match miss;
`visible_action_alias()` treated every action with no source square as a drop,
then attempted to format the pass action's absent target square. This raised
`AttributeError` before the CLI could report an unknown or ambiguous input.

The scoped fix gives `PassAction` its exact visible token before coordinate/drop
projection. Exact legal-action matching, numbered selection, rules semantics,
session submission and record serialization are unchanged. No API, engine,
search, generator or price-model change is warranted by this caller defect.

## Evidence

- A valid pass-enabled semantic fixture has four semantic board moves and a
  `PassAction`. Before the fix, an exact action string worked, while an invalid
  command reproduced the target-formatting exception.
- The regression exercises the real `--ruleset` CLI: a shared coordinate alias
  reports ambiguity, invalid text reports unknown input, and exact `pass` is
  recorded and replays as the sole chosen action.
- A second production CLI regression selects one of two same-coordinate
  semantic actions by full string and verifies the saved action and auxiliary
  state after replay.
- Focused pass, semantic-action and Standard Shogi tests: 43 passed, including
  the durable semantic drop/promotion alias regression.
- A bounded diagnostic sweep covered 66 states and 1,605 legal actions across
  existing pass-enabled fixtures and 16 generated 6x6 hybrid rules. Exact
  strings resolved to their originating actions; visible aliases either chose
  their unique action or retained explicit ambiguity. Observed action counts:
  1,363 `BoardMove`, 236 `DropMove`, 4 `SemanticBoardMove`, 2 `PassAction`.
  The sweep was a bounded diagnostic, not a persisted exhaustive proof.
- A persistent Standard Shogi regression now exercises a real
  `SemanticDropMove` and promotion action through exact strings and visible
  aliases. The hand-P state has 71 semantic drop choices. This does not
  establish injectivity across every generated rule.

## Validation limits

The full default suite completed with one unrelated failure:
`tests/product/test_semantic_opportunity.py::`
`test_projection_is_not_legacy_atoms_or_full_semantic_mobility` expected the
static base pawn value to be 1 but observed 361. It reproduces alone; the
failing test and static-profile sources are outside this diff, and `git blame`
places the assertion in the 2026-10-08 test commit. The remaining full suite
passed. Keep this known failure visible; do not alter static prices to make the
CLI repair appear clean.

The demonstrated conclusion is only that the CLI now handles the observed
coordinate-free pass action without corrupting action identity. It is not a
claim of all-domain CLI equivalence or a change to the scientific price/search
choice.
