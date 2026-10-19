# Targeted semantic search probes — 2026-10-20

These bounded prepared-root probes follow the initial-root smoke correction
in `SEMANTIC_SEARCH_INTERFACE_SMOKE_20261020.md`. They test concrete action
availability, transition, and one depth-1 search against the bounded plain Core
reference. They are not utility or population experiments.

## Compound shift

The existing `move_and_shift_adjacent_friendly` fixture requires an R at source
(2,2), a friendly R at owner-relative offset (0,1), and an empty shift target at
(0,2). One first setup put the companion at file 3/rank 2 due to reversing
file/rank; that setup produced no compound action and was invalid. With the
companion correctly at file 2/rank 3, Core generated exactly one target compound
action among 24 legal root actions. Applying it moved the actor to (3,3), shifted
the companion to (2,4), and vacated both original cells. Depth 1 completed at
25 nodes; the plain and public-bundle controls matched the completed 24-leaf
Core reference score. The target action was not the selected PV, so the claim is
legal-action generation, direct transition, and inclusion in the searched root
set—not PV selection.

## Screen-count capture

For the existing `ray_quiet_zero_capture_two_screens` fixture, the prepared
root placed the R actor at (2,2), two friendly screens at (3,2)/(4,2), and an
enemy R at (5,2). Core generated exactly one matching semantic capture among 27
legal actions. Applying it moved the actor onto the target, removed the enemy,
and added one R to the actor's hand. At depth 1 both controls completed at 28
nodes, matched the completed 27-leaf Core reference score, and selected a PV
containing the target capture.

## Guarded drop after real capture history

The existing `drop_zone_capacity_guard` fixture starts with empty hands. The
prepared position enabled R drops and placed an own R at (2,2) with an enemy R
at (3,2). The normal semantic action path captured the enemy R into hand; after
one legal opponent King reply, the R hand still contained one piece. Core then
generated exactly one guarded semantic drop to (0,1), satisfying the fixture's
zone-count guard. The resulting root had 78 legal actions. Both depth-1
controls completed at 79 nodes and matched the completed 78-leaf Core reference
score. The target drop was not the selected PV. A separate direct `apply_action`
check on the same prepared route confirmed
the R appeared at (0,1) and the R hand count fell to zero; this did not rerun
search.

## Expiring auxiliary state and promotion

The existing lifecycle fixture combines `drop_zone_capacity_guard` and
`promotion_grants_one_turn_right` after a four-ply legal route. The target
promotion action is `sem_01_promotion_grants_one_turn_right` because the
fixture has two semantic actions; filtering for `sem_00` would miss it. Core
generated the target action in a 45-action root. Direct application changed
the R to promoted TP and set its expiring auxiliary slot to1; one subsequent
legal opponent King move expired that slot back to0. At depth1 both controls
completed at46 nodes and matched the completed45-leaf Core reference score.
The promotion action was not selected in the PV.

## S3 no-legal-reply drop after real capture history

The existing `uchifuzume_ruleset` fixture has a pawn drop action guarded by
both `opponent_checked` and `no_legal_reply` at S3. Its stock initial position
has no pawn in hand, so it cannot exercise the drop directly. A reachable
history was prepared: side 0's P captured an opposing P, then side 1 made a
legal reply; side 0 consequently had P in hand. With the side-0 king at
(6,5), opposing king at (7,7), and a friendly P at (6,6), the S3 candidate
drop at (7,6) was absent from the 62 legal root actions while a non-checking
control drop at (3,0) remained legal. At depth 1, plain and public-bundle
searches each completed 63 nodes and matched the completed 62-leaf Core
reference; the excluded candidate was not in PV. This establishes that the
reachable hand/history root preserves the fixture's legality filter into
search. We did not instrument the hypothetical forbidden child's reply set,
so we do not claim an independently verified mate explanation or attribute
the rejection to one postcondition in isolation. The focused S3 conjunction
and Native probe regression cases pass (2 tests).

## Limits and decision

These are hand-prepared roots using existing fixtures, with one run per control
and no repeat or game-utility evidence. The screen-count capture was selected in
the PV; compound shift, guarded drop and promotion were legal root actions
included in the depth-1 node totals but not selected. The S3 candidate is
excluded and its control remains legal, but the hypothetical child's reply set
was not instrumented. None establishes general Native parity, arbitrary-rule
coverage, performance, or utility. Exact compact records are in
`data/semantic_search_mechanism_probes_20261020.json`; verbose diagnostic
output remains private in `.local_agent`.

## Search accounting and cancellation boundary

Source inspection shows S3 reply candidates call the same cooperative
checkpoint at pattern and candidate boundaries. Search's existing
`legal_generation_seconds` times the full semantic successor-handle iteration,
so it includes the reply scan; there is no dedicated S3 trial counter. This is
an accounting-scope observation, not a measured cost estimate. A focused
regression injects cancellation on the third checkpoint inside
`_exists_s3_reply` and confirms propagation; together with existing early-exit
and nested-S4-disabled tests, all three targeted cases pass. No cancellation
swallowing or omission from the public timing boundary was observed, so no
diagnostics/API change is justified.

Source review confirms search timing wraps full semantic successor iteration and
S3 reply scans poll cancellation/deadline cooperatively; a regression now verifies
cancellation propagation, alongside the existing early-exit and nested-S4 tests.
S3 internal reply candidates do not increment AlphaBeta node counters, however,
so a node cap bounds searched nodes but not all legality work. This is an
interpretation limit, not a measured defect: no search counter/API change is
made yet. The next test is a small, fixed-root paired measurement of an S3
reply-scan case versus its no-S3 control, recording node counts, legal-generation
time and cancellation behavior to see whether equal node budgets conceal a
material cost difference.

## Fixed-root S3 cost pilot

For a single reachable root, a legal side-0 P capture and legal side-1 P reply
produce a side-0 hand containing P (two history plies). The S3 treatment uses
the fixture's `opponent_checked + no_legal_reply:S3` action. The diagnostic
control removes only `no_legal_reply` and retains `opponent_checked`; this is
not a globally behavior-equivalent ruleset, but on this exact root its sorted
legal-action set matched the S3 treatment (64 actions), and its reply-probe
count was zero versus seven for S3. This isolates one bounded reply-scan path;
it does not establish all-rule equivalence or a population cost.

Eight alternating paired depth-1 searches used identical root histories,
node/time limits, evaluator, no TT/order/root tactical, and q-depth zero. The
first two runs per arm were excluded as warm-up. Each remaining run completed
65 nodes, generated 128 actions in two explicitly timed legal-generation calls,
and chose the same action. Upper medians were 10.393 ms total / 1.639 ms legal
generation for S3 and 9.483 ms / 0.898 ms for control. The observed legal-time
difference is about 0.740 ms on this microfixture; it is small, unreplicated
across positions, and may include Python timing noise. Both arms completed
before the 5 s deadline; this pilot did not inject cancellation. The separate
focused cancellation regression remains the cancellation evidence (3 targeted
tests pass). No decision-relevant defect or need for an API/counter emerged;
retain node-cap versus total-legality-work as an interpretation limitation.
Full per-run values are in `data/semantic_search_mechanism_probes_20261020.json`.

The formerly uninspected candidate child was then reconstructed from the same
two-ply capture/reply root by applying the target P drop at (7,6). The child is
checked, produces zero legal replies, and the existing `_exists_s3_reply`
returns false (meaning no S3-or-lower reply exists), matching the guard's
forbidden condition for this concrete reachable state. This closes that
specific explanation gap; it does not validate other positions or all rule
families.

The fixture inventory found an existing combined drop-capacity/promotion
lifecycle route. At its five-ply promotion checkpoint the auxiliary right was
active; a depth-1 product `AlphaBetaPlayer` call completed at6 nodes, selected
an executable legacy King action, and its PV replayed legally. The root had5
legal actions. This confirms search accepts that state and returns a legal
line, but the selected line did not exercise promotion/drop transitions, so it
is only an interface check and adds no mechanism-utility or performance claim.
