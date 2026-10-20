# Generic repetition terminal through public AlphaBeta —2026-10-20

## Question and decision

Does a generic repetition-limit terminal produced by a checked child transition
reach the public AlphaBeta score with a warm transposition table? This is a
caller-integration check, not a search-strength or isolated TT-key claim.

## Probe

`tests/product/test_search_path_runtime.py::test_public_alphabeta_scores_generic_repetition_terminal_with_warm_tt`
uses the existing deterministic four-cycle fixture. Same-board roots at ply3
(current-position count1) and ply11 (count3) are ongoing; their sole legal
children are respectively ongoing and repetition-terminal. With a constant
leaf score of77 and depth1, public AlphaBeta returns -77 and0. It compares one
shared TT in both root orders against fresh no-TT controls and checks the
selected action by applying it through `GameSession`.

The test forces both `RuntimeHistoryContext._record_digest` and
`RuntimeCountsSnapshot._entry_digest` to collide. Exact safety still holds in
this scenario, but the roots have different `ply_count`, and
`SearchStateIdentity` includes ply. Therefore the result does not show that
repetition-history fields alone separate these TT entries. Same-ply
different-history warm-TT behavior is covered independently by
`tests/product/test_no_progress_search_context.py::test_warm_caller_keeps_exact_history_even_when_history_digests_collide`.

## Evidence and limits

- New repetition caller test plus the existing same-ply no-progress caller test:
  3 passed.
- The focused evaluator, semantic-opportunity, Native-iteration, legacy adapter,
  search-runtime, no-progress and AlphaBeta module set completed with no failures;
  the quiet progress output did not retain an exact aggregate count.
- The full suite passed with exit0 in a run with required runtime/helper access;
  exact private logs and exit status are in ignored `.local_agent`.
- The earlier isolated static-opportunity assertion was not fixed by changing
  its expected price. Its legacy comparator was made explicit after tracing the
  changed default semantic profile; see the follow-up in
  `GENERIC_CLI_ACTION_INPUT_20261020.md`.

This closes a narrow public result-propagation test gap. No production search
change, general TT proof, generated-domain utility result, price change or
backend-selection consequence follows.
