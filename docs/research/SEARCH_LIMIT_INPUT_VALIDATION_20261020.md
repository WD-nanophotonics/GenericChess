# Shared search-limit input validation — 2026-10-20

## Observed public-call inconsistencies

The shared `SearchLimits` constructor accepted negative `max_nodes`. A bounded
4x4 `AlphaBetaPlayer.choose_action` call then returned a legal fallback with
`termination_reason="node_limit"`, depth 0 and zero searched nodes. In contrast,
`NativeSearchEngine.search` already raised `ValueError` for the same negative
node budget; `test_negative_node_budget_rejected` records that contract.

The same source-guided check found `max_depth=-1` was accepted by the shared
object. AlphaBeta performed its root scan and returned a legal fallback with
`termination_reason="fallback"`, depth 0 and seven nodes, while Native already
rejects depth outside `[0, GC_MAX_PLY]`. Zero is a meaningful immediate-search
depth on the shared route and remains valid; `None` retains the Core default.

## Change and verification

`SearchLimits.__post_init__` now rejects negative `max_depth` and `max_nodes`
before any backend receives the limits. It keeps `max_depth=0`,
`max_nodes=0`, `max_depth=None`, and `max_nodes=None` valid. No depth cap,
node-counting, deadline, qsearch, cancellation or fallback policy changed.

Regressions in `tests/product/test_ai_search.py` cover negative, zero and
default depth, plus negative and zero total-node budgets. The existing Native
negative-node regression remains. Both relevant modules pass 36 tests:
`tests/product/test_ai_search.py` and
`tests/product/test_native_search_budgets.py`.

A continuation of the same bounded contract audit tested the remaining qsearch
integer caps. On the same 4x4 public caller at depth 2, `quiescence_max_depth`
of -1 and 0 both completed with the same action/score and zero qnodes, while
the default depth 4 searched 271 qnodes. `quiescence_max_nodes` of -1 and 0
both produced a `qsearch_budget` fallback at depth 0; `None` completed depth 2
with 271 qnodes. The Native route already rejects negative qsearch settings
because it supports only depth 0 and node cap `None` or 0. The shared
constructor now rejects negative `quiescence_max_depth` and
`quiescence_max_nodes`, retaining zero and `None`. The two modules now pass 37
tests.

The same source audit corrected a misleading `SearchLimits` class docstring:
`max_depth=None` means AlphaBeta's finite default maximum depth of 64, while
`NativeSearchEngine` requires an explicit supported depth. `None` means no cap
only for the other applicable fields (`max_nodes`, `max_time_seconds` and
`quiescence_max_nodes`). Backend behavior was not changed.

The exposed `deterministic` field has no runtime reader in the current Python or
Native search implementations; only three existing training helpers pass
`True`, and no project caller passes `False`. A matched public 4x4 AlphaBeta
call produced identical action, score, PV, depth, node count and termination
for both values. The field is now documented as inert compatibility metadata;
no randomization, seed, behavior change or API removal is inferred.

## Fractional integer-budget validation

A focused typed-budget probe found that `max_nodes=1.5` was accepted and the
public AlphaBeta caller returned `nodes=2` before stopping, exceeding the
declared numeric cap. Fractional caps 0.5/2.5 similarly stopped at1/3 nodes;
integer caps 0/1/2 stayed within their budgets. `max_depth=1.5` instead fails
with a direct `TypeError` when iterative search begins, without returning a
decision. The shared constructor now requires all five integer-annotated
depth/count fields to be integral non-bool values, before backend work; valid
zero/`None` behavior remains. AlphaBeta and Native budget modules pass 47 tests.

The fractional-cap reproduction also justified checking field types at the
shared boundary. `max_depth=1.5` fails later with `TypeError`; the other four
integer-annotated fields did not all have the same consuming-path rejection.
The constructor now requires all five depth/count fields to be integral and
non-bool, while preserving integer subclasses and declared `None`/zero cases.
The public fractional `max_nodes=1.5` overrun is therefore rejected before
search. The focused AlphaBeta and Native budget modules pass 47 tests.

## Native zero-depth result semantics

The Native iterative API accepts `max_depth=0` and its C kernel deliberately
returns the ongoing root's static material score with no action/PV, completed
depth zero and one visited root. `NativeIterativeSearchResult.action` is
optional, and the documented legal fallback is for an abort before completing
depth one, so this is score-only evaluation rather than a failed move request.
AlphaBeta retains its distinct legal root-scan fallback at depth zero. The
Native iterative documentation now states this distinction, and a generated
4x4-rule regression checks the zero-depth result against the fixed-depth static
score and confirms the full session record is unchanged. The focused iterative,
AlphaBeta and Native-budget tests pass 62 cases.

A follow-up control matrix found that the zero-depth branch skipped the Native
node/time/cancel poll: `max_nodes=0`, `max_time_seconds=0` and a pre-cancelled
token all reported `completed_depth` and performed the score evaluation. The C
path now checks the existing controls after ongoing-root terminal detection and
before score work; an abort keeps the score-only/no-action shape, reports the
actual cause, and does not claim a move fallback. Terminal-first ordering and
the one mandatory root visit are unchanged. After rebuilding the extension,
the focused iterative, AlphaBeta and Native-budget files pass 65 tests;
including the static-profile evaluation module, all 87 affected product tests
pass.

## Limits

This aligns the demonstrated negative inputs, rejects non-integral/bool values
for the five depth/count fields, prevents the observed fractional-node overrun,
and checks stop controls before a zero-depth static score. The time limit is
still cooperative rather than a strict wall-clock guarantee. No claim is made
about unrelated fields, search quality or unfamiliar-rule utility.
