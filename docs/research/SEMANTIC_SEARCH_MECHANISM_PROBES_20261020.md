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

## Public AlphaBeta compound-shift action/PV follow-up

A focused lifecycle regression now exercises `weird_rulesets()[3]` with a
fixed 8x8 legal setup containing K/R/R and a two-ply public `GameSession`
history. A test-only evaluator rewards exactly the companion shift's two-piece
result so the search must carry the compound `Action` through the public
decision interface. At completed depth2, Native legality returned the exact
Core-generated `sem_00_move_and_shift_adjacent_friendly` action; both PV edges
replayed through `GameSession.submit`; the caller session record remained
unchanged during search, and the board contained the expected R pieces on e5
and d6. The target file and adjacent runtime-history/Native-repack
tests pass (63 tests across the three files). This test guards one concrete API
contract; the custom evaluator does not establish natural preference or
strength.

The same action was recombined onto generator-produced seed21/size6 hybrid
types K/P/X/A/B. The action and replacement K/P/A setup are synthetic and are
not emitted by the generator; the generator-produced type definitions,
promotion targets and compilation boundary are real. The default evaluator
completed depth2 with a legal two-edge PV (15 Native calls, zero fallback or
operational failure). A separate controlled probe forced the exact P action;
it returned the same `Action` identity at depth2 and replayed the PV through
Core. These checks establish only supported compilation/search and replay for
these two constructed roots, not native-generator action coverage or
all-generated-domain equivalence.

On the 8x8 fixture, owner0-normalized material-only evaluation was unchanged
(2000 before/after) across the actual compound transition, while the default
score moved 2044->2052. A synthetic main-move-only control moved 2044->2044;
feature ablation assigns the +8 companion increment to dynamic mobility
(dynamic-only +8, material-only 0, anchor-only 0). On a fixed two-ply root, a
depth3/q0/node2500 pair with dynamic-mobility weight2 versus0 completed both
arms and retained the same action and three-edge PV (scores2122/2070; nodes
2089/1724). This is one evaluator-sensitivity example, not a benefit or
strength result. It gives no reason to add an action-specific value term or
change default weights.

A separate existing castling fixture checks an action with a persistent auxiliary
right: bounded depth1 public AlphaBeta search selected the exact Core
`sem_00_king_side_shift` action, and replay moved both king and rook while
clearing the owner's right. Search left the caller's session record unchanged;
Native legality was used without fallback or operational failure. A test-only
evaluator targeted this transition. This is a fixed-fixture action/PV contract
check, not a utility or strength result.

A bounded history-dependent off-target-capture case uses the actual public
sequence P c2-c4 (setting the transient token), then P b4xc3. Core AlphaBeta
selected the exact token-guarded action and its full depth2 PV replayed through
`GameSession`; the captured pawn entered owner1's hand and the token cleared.
The caller record stayed unchanged. Native was deliberately not created:
`NativeSemanticLegalityProvider.try_create` declines action-base removal
semantics, retaining Core. An initial Native-call expectation failed and was
corrected after source inspection; this is an existing route boundary, not a
Native defect or general coverage claim. A separate depth2 call on the same
reachable root with the unmodified default evaluator also selected this exact
off-target capture (46 nodes; two PV edges), and the PV replay verified the
capture-to-hand/token-clear transition. This is one local choice, not evidence
of strength or optimality.

An adjacent rule-price projection audit holds the transient-token declaration
and double-step action fixed, removing only both guarded off-target capture
patterns. The full and control P inputs match exactly: the same forward-ray
signature, raw2.2299787158, normalized board1000/hand900, and semantic signature.
The full profile explicitly lists both captures as excluded for compound/state
effects. This says those omitted capture patterns do not alter this static
projection; it does not say their actual rule utility is zero. A broader
control that removed every semantic action changed hand classification because
the aux slot disappeared, so it is retained privately as a confounded attempt.


The same lifecycle now also forces the real semantic promotion at ply4 through
a depth1 public AlphaBeta call. Its exact action and PV replay preserve the base
R/current TP/promoted identity and set the auxiliary right; the probe evaluator
is test-only and the search leaves the caller history unchanged. This is a
reachable interface check, not a preference or strength result.

A further action-interface check extends the existing capture/promotion/expiry
lifecycle. After real public-session history produced58 legal R drops, a bounded
depth1 AlphaBeta call with a test-only effect probe selected the exact R drop to
a1. The returned action replayed through `GameSession`, placed the rook, and
decremented hand count once; the caller history remained unchanged during
search. This is a reachable-state API check, not natural preference or strength.

The compact public evidence is in
`docs/research/data/compound_search_interface_followup_20261020.json`; full
experiment records remain locally available in ignored `.local_agent`.


## Stock generated-rule caller and reachable lifecycle sample

The ordinary `generic_chess.generation.generate_game` implementation constructs
its `RuleSet` from generated movement atoms and derived promotion/drop data; it
does not supply `semantic_actions`. A fixed 12-config sample (two presets,
board sizes 4/6/8, two prespecified seeds) confirms zero semantic actions in
every output. With the unmodified default evaluator, public AlphaBeta completed
depth 2 on ten roots and returned a rule-immediate win before iteration on two
4x4 roots. Across the 12 roots, 3,011 nodes and 22 returned PV edges were
recorded; every PV replayed and every caller record remained unchanged. Those
PV edges comprised 20 captures, no promotion or drop.

To exercise actual generated promotion/drop histories, the same 12 fixed
configs were advanced through deterministic legal histories, stopping at the
first available promotion or drop. Eight reached promotion and four reached a
drop within seven plies. A bounded depth-1 search with a test-only exact
successor probe selected the target in 11 cases; the remaining root had an
independent immediate-win result before a completed iteration. All 12 returned
PV edges replayed through `GameSession`, and all input records stayed unchanged.
This is selected-fixture interface evidence, not event frequency, strategy,
strength or utility. It distinguishes the stock atom generator from the broader
semantic/recombined rule target; the latter remains covered by the separate
fixture-level probes above, with their synthetic boundaries explicit. The data
records exact configs and per-root outcomes in
`data/generated_search_interface_followup_20261020.json`; raw attempts remain
in ignored `.local_agent/quality-20261020/`.


A separate end-to-end persistence check serialized and reloaded the fixed
compound-shift `RuleSet` before compilation and search. Exact `RuleSet` equality
and stable serialized bytes held; the public two-ply `GameSession` then returned
the exact compound action in a completed depth-2 search, and both PV edges
replayed after reload (110 nodes, 27 Native calls, no fallback). The focused
regression now includes this serialize/reload boundary. This is one fixed
semantic rule with a test-only evaluator, not generated-semantic coverage or a
utility/strength claim. Hash and details are in
`data/generated_search_interface_followup_20261020.json`.

The same persisted compound-shift route now also round-trips the two-ply
`GameRecord` before search and asserts exact equality on replay. This closes the
scoped serialized rule + serialized history interface check; it does not extend
the fixture/domain or utility conclusions.


## Interrupted compound-search result contract

On that same serialized, reachable compound-shift root, five deterministic
node-budget probes at caps30,50,80,110,150 all stopped with `node_limit` and
returned a root-legal action without mutating caller history. At caps30 and50 no
uniform iteration completed (`completed_depth=0`) and the PV was empty. At
caps80 and110 depth1 was retained; at150 depth2 was retained. In each nonempty
case the PV began with the separately returned action and every PV edge replayed
legally. Native legality was used without fallback. These bounded probes show
the current API distinction: callers execute `decision.action`; the PV is only
the last completed line and can be empty. They do not show strength, value of
the fallback, or all-rule interruption behavior. `PlayerDecision` now documents
that distinction, with a regression on the compound action. Compact rows are
in `data/compound_search_node_budget_20261020.json`.

The five-file targeted search/lifecycle suite passes 109 tests after this change.
A full-suite attempt completed with 74 setup errors and 3 failures: optional
Native fault-build fixtures could not read the runtime Python `libs` directory
and Zig could not find `python312`; two synthetic Git publication fixtures
could not push/read their temporary remote; a separate existing semantic
opportunity assertion expected the generic-v3 Western pawn value to equal 1 but
observed 361. None of these changed files are in this patch; the last is an
unresolved unrelated baseline expectation, not treated as an environmental
error. Full raw output is retained privately under ignored
`.local_agent/quality-20261020/full-pytest-local-basetemp.log`; no full-suite
pass is claimed.

The interrupted-return contract was also checked on the reachable en-passant
double-step root, whose action-base removal makes the Native legality provider
decline and leaves Core as the legal-generation route. At node caps1 and25,
`node_limit` returned root-legal ordinary fallback actions; cap1 had no completed
iteration and an empty PV, while cap25 retained a one-edge depth1 PV beginning
with the action. Both PV shapes replayed, caller history was unchanged, and no
Native call/fallback/failure was reported. The test-only evaluator was aimed at
the off-target capture, but these small-budget fallback actions did not select
it; no choice-quality claim follows. See
`data/core_only_en_passant_budget_20261020.json`.

The product consumers checked in `ui.controller`, `benchmark.runner`, and the
benchmark CLI submit or record `decision.action` directly; none derives the
move from `principal_variation[0]`. That matches the documented interrupted-
search contract.

Finally, the default player was checked on one fixed8x8 bilateral-random
generated root with 44 legal actions and no explicit semantic actions. Caps 1 and
64 returned legal actions at depth 0 with empty PVs; cap 256 retained depth 2 and a
two-edge replayable PV beginning with the selected action. All counters met
their caps, caller history stayed unchanged, and there were no Native
fallback/failure events. This single generated-root budget check adds finite
interface evidence, not generated-semantic coverage, utility or strength. Rows
are in `data/generated_root_node_budget_20261020.json`.

An explicit cancellation was then requested from the progress callback after
the first completed iteration on the serialized compound fixture. Search
returned `cancelled`, retained depth 1, returned the exact compound action as
the PV head, and replayed that line legally without mutating caller history
(53 nodes; one Native call, no fallback). This verifies the existing
completed-iteration contract for one compound-action case; it is not a
strength or broad cancellation claim. Regression and compact data are in
`tests/product/test_recombined_semantic_lifecycle.py` and
`data/compound_search_cancel_20261020.json`.

A deterministic fake-clock deadline was expired by the progress callback after
depth 1 on the same fixture. Search returned `time_limit`, retained the exact
compound action and one-edge PV from depth 1, replayed it legally, and left the
caller history unchanged (53 nodes; one Native call, no fallback). This is one
between-iteration deadline check, not real-time responsiveness or all-rule
coverage. The regression is in the same lifecycle test; compact evidence is
`data/compound_search_deadline_20261020.json`. The initial harness attempt
omitted `perf_counter` and produced no observations; that setup error and its
correction remain in ignored `.local_agent`.

One existing generated24x24 bilateral-random hybrid configuration (seed
2026101965,96 pieces) was also checked at a one-node cap. It had222 legal root
actions; search returned a legal depth0 fallback at exactly1 node with empty
PV and reported about15ms to first legal action, leaving caller history intact.
This makes clear that legal-root preparation is a distinct cost from counted
search nodes, while the measured single-case latency is not evidence of a
material general bottleneck. Exact row:
`data/generated_large_root_budget_20261020.json`.

To separate budget allocation from immediate-win protection, the same fixed
24x24 root was rerun at a 256-node cap with the default root tactical scan and
with only that scan disabled. The default spent 222 root-scan nodes, stopped at
the cap before depth1, and returned legal ongoing action `g2-g23` as a depth0
fallback with empty PV. The scan-disabled arm completed depth1 in223 nodes and
returned the same legal ongoing action, with a one-edge PV. Both left caller
history unchanged. This is a concrete budget/depth tradeoff on one root, not a
strength or policy result. Existing `test_root_terminal_wins.py` exercises the
scan's distinct purpose: retaining immediate terminal wins, including history-
dependent continuous-check wins, at the budget boundary. Given the single-root
comparison and that correctness role, no default or algorithm change follows.
The focused root-scan, generation-accounting and latency tests pass18 tests.
Exact compact data: `data/generated_root_scan_budget_pair_20261020.json`; raw
stdout and the corrected harness attempt are retained in ignored
`.local_agent/quality-20261020/generated-root-scan-pair-raw.txt`.

Source review then found one unmeasured cancellation boundary: when semantic
root legal-action enumeration aborts, the public fallback retries the same
request without a checkpoint so it can still return an executable legal move.
On the same size24/222-action root, a controlled cancellation at root checkpoint
poll100 caused two legality requests; the uncancelled fallback returned legal
`a2-d5`, with no search nodes/depth and unchanged history. Both attempts plus
fallback accounted for about26ms, and the API reported first legal action at
about16ms. This confirms the duplicate fallback path, not an unbounded delay or
a product defect; one 24x24 case provides no basis for changing the contract.
Exact compact evidence is `data/generated_root_cancel_fallback_20261020.json`;
raw output is in ignored `.local_agent/quality-20261020/generated-root-cancel-fallback-raw.txt`.

## Public AlphaBeta PassAction and generated-semantic root checks — 2026-10-20

On the existing pass-enabled4x4 legacy fixture with a draw after two consecutive
passes, a test-only board-preserving evaluator made the public `AlphaBetaPlayer`
select `PassAction` at depth1 for both sides. Each returned PV began with pass
and replayed to the same Core child used by `GameSession.submit`. The first pass
left the game ongoing; the second produced `ACTION_CLASS_DRAW`. Serialization
and record replay preserved the complete state/result, unchanged board/hands,
and both pass action signatures. A subsequent player call returned no action
with `TERMINAL`/`terminal_position`.

On the existing pass-enabled5x5 auxiliary-state fixture, Core and
`SearchPathRuntime` produced the same five-action root set, including PassAction
and `sem_00_mark_ephemeral`. Public depth1 probes selected each of those action
kinds; both were in the Core root set, began the PV, and submitted/serialized/
replayed to the same state/result. The selected semantic action set its guarded
auxiliary slot to1. A pre-cancelled4x4 call returned ordinary legal fallback
`a1-a2` at depth0 while PassAction was also present in the Core root set; the
caller state object/history remained unchanged. This confirms fallback legality
for the fixture, not that PassAction is selected as fallback.

The initial three public-route regressions are in
`test_generic_consecutive_action_adjudication.py` and `test_generic_pass_action.py`;
both files passed39 tests at that checkpoint. These checks
close only the named public-route contracts. They do not establish complete
generated-rule equivalence, fallback quality or utility, and no production
behavior change was warranted. Compact outputs:
`data/pass_alpha_beta_public_route_20261020.json`.

A parameterized public-route regression checks both sides of the qsearch
terminal-child boundary. On a4x4 position where each side has only PassAction,
the same depth2 search and test evaluator scores a terminal third pass as0 with
qdepth1, versus -1000 at qdepth0. With a draw threshold of four, the third pass
is still ongoing and qdepth1 retains -1000, excluding that nonterminal quiet
pass; the fourth pass is a Core draw. An instrumented one-off probe confirmed
the terminal third child is classified as `ACTION_CLASS_DRAW`. These checks
show the bounded legacy route includes terminal pass children but does not
extend quiet passes; they are not a value, strength or all-rule coverage claim.
The two focused files now pass41 tests.

The same threshold3 terminal-child control was then run through an
`ExecutableSemanticRuleset` built from the existing pass/mate fixture, retaining
both configured semantic action definitions while blocking all pieces that could
produce them. Core exposes only PassAction: qdepth0 scores -1000 and qdepth1
scores0 at the same completed depth2, with three qnodes. This supports parity
of the semantic-compiled execution route for a terminal pass, but the semantic
actions themselves were not generated in the blocked position. One product
regression preserves that distinction; the two focused files now pass42 tests.

A separate history-sensitive control uses the same blocked 4x4 legacy fixture
with repetition limit3 and no consecutive-action rule. The third pass remains
ongoing; the fourth returns `REPETITION` from the complete position history.
At depth3, qdepth0 scores1000 while qdepth1 reaches four qnodes and scores0,
with PassAction still selected. Thus the public legacy qsearch also includes a
terminal pass child whose result depends on repetition history, not only the
action-class terminal status above. The evaluator is intentionally adversarial
to stand-pat and supplies no utility/strength evidence. The focused pair of
files then passed43 tests.

The repetition control also passes through `ExecutableSemanticRuleset` with
two semantic definitions configured and no pieces that can generate them on
the blocked board. With the consecutive-action policy removed, the fourth pass
is `REPETITION`; public depth3 qdepth0/qdepth1 scores are1000/0, and qdepth1
reaches four qnodes. This confirms the semantic-compiled route retains the
history-dependent terminal pass child. It does not test generated semantic
actions in qsearch; the exact limit is retained in the regression/data. The two
focused files now pass44 tests.

## Native semantic-search qsearch on a history-terminal child — 2026-10-19

The prior qsearch checks exercised the public Python AlphaBeta route. A separate
Native-kernel control now uses the existing deterministic4x4 F/G cycle, rebuilt
as a RuleSet and passed through `compile_legacy_ruleset_for_semantic_execution`.
There is exactly one legal move at each ply. Starting at ply8 with nine history
records, the depth3 line reaches an ongoing frontier at ply11; its only action
creates the fourth occurrence and a Core `REPETITION` terminal.

With a fixed test material profile K=0/F=500/G=100/Z=0, no TT, and the Native
root window disabled, qdepth0 returns400 while qdepth1 returns0 with four qnodes.
The independent Core route returns the same raw scores, action and PV at both
qdepths; both complete depth3 and leave the caller's ply/history unchanged.
This verifies one complete-history terminal child through the Native semantic
search kernel. The fixture is legacy-atom-derived semantic execution, not a
DSL-generated action or generated hybrid. Test-evaluator contrasts establish
neither playing strength nor utility, and no production behavior change was
needed. Regression: `tests/product/test_native_semantic_qsearch.py::test_native_semantic_qsearch_includes_full_history_repetition_child`.
The four focused qsearch/pass/history files pass63 tests. Compact data:
`data/pass_alpha_beta_public_route_20261020.json`.

## Public AlphaBeta dispatch with PassAction — 2026-10-20

Source inspection confirms `AlphaBetaPlayer.choose_action` always calls the
Python `run_root_search`; its optional Native component is a legality provider,
not `SemanticSearchEngine`. `SearchPathRuntime` appends the Core-checked
`PassAction` after a successful Native semantic binding query, and otherwise
builds semantic bindings in Core. Native semantic compilation explicitly
rejects coordinate-free pass rules.

On the existing blocked5x5 `ExecutableSemanticRuleset` with repetition limit3,
the public player returned a PassAction PV of length3, score0, completed depth3,
and four qnodes. The Native legality provider was unavailable for this
execution ruleset, with zero Native legality calls/fallbacks; the complete
caller history remained unchanged. This confirms the tested public entry stays
on Core and does not surface the standalone Native pass rejection. It does not
claim Native pass support or exercise the separate `CompiledSemanticRuleset`
provider path. A new typed-`CompiledSemanticRuleset` regression then exercised
that provider-construction boundary directly: Native was declined and the same
Core qsearch result/counters were preserved. No production code change is
warranted. The two pass-focused files pass45 tests; the four-file
pass/history/Native suite passes65. Regression:
`tests/product/test_generic_consecutive_action_adjudication.py::test_compiled_semantic_pass_rules_decline_native_and_keep_core_qsearch`.

The existing Native history qsearch test used `compile_legacy_ruleset_for_semantic_execution`,
so it did not cover generated semantic action IDs. A bounded4x4 cycle now
replaces the F/G legacy movement with four declared F/G up/down semantic
actions; Native compilation succeeds and exactly one semantic action is legal
at each ply. The ply0 and ply8 roots have the same board/side, but histories
contain1 and9 records. At qdepth1, both Core and Native score the short-history
root400; on the long-history root they score0 because the third mainline edge
reaches an ongoing q frontier whose sole generated-semantic child is the fourth
occurrence (`REPETITION`). qdepth0 remains400 on the long root; Native qdepth1
visits four qnodes and matches Core action/PV. This is a focused history contract
control, not utility/strength or all-domain evidence. The five-file
pass/history/Native suite passes75. Regression:
`tests/product/test_native_semantic_qsearch.py::test_native_qsearch_full_history_on_declared_semantic_actions`.

The terminal-policy source audit found no Native-supported consecutive-action
history class distinct from `pass` (the schema admits only that action class,
and Native compilation rejects pass-enabled rules). A separate still-open
history distinction is continuous-check repetition loss: current Native tests
check its terminal transition at an actual Shogi root, while qsearch history
tests cover ordinary repetition. One existing Shogi cycle now supplies a
bounded full-history check: from ply10, its next rook check and quiet king
reply produce `PERPETUAL_CHECK` for the checker at ply12. The root keeps11
history records with exact check events; the largest identity multiplicity is3
against repetition limit4. On that root, a depth1/qdepth1/hard-check-depth12
search with a zero evaluator completes in both Core and Native at score0 with
the same action and PV; Native reaches46 qnodes (Core40). Native reports
ordinary qdepth0 because the first iterative result reserves that policy, while
the checking hard extension is active. The returned PV avoids the certified
perpetual-check line, so this is full-history result parity around that line,
not proof that the particular terminal child appears in the PV or a traced
q-node. Source review confirms qsearch checks terminal status at node entry;
the near-threshold repeat multiplicity disables the transient quiet-history
deferral for this root, retaining checked full-history child transitions.

The bounded regression is
`test_native_shogi_check_history_search_result_matches_core`. It also checks
Native's imported history-event stream and Core's terminal outcome along the
certified continuation. No Core/Native decision divergence or production
defect was observed, so no backend change follows. Compact data:
`data/native_shogi_perpetual_qsearch_20261020.json`. This does not establish a
general Shogi qsearch theorem or playing-strength claim.

## Native qsearch with a generated-semantic promotion at the frontier — 2026-10-20

One existing `SHOGI_LIKE` 3x3 fixture from the F23V generated-rules helper was
reused without adding a game. From its custom root, two main-search plies leave
the side to move with a legal generated `SemanticBoardMove` promotion
`b2-b3=G` at the depth-two qsearch frontier. The Native semantic compiler
accepts this ruleset. A zero-dynamic test evaluator assigns P=100/G=1000; all
calls use no TT/order/root-tactical scan, a 1000-node cap and a 3-second limit.

At qdepth0, Core and Native both complete depth2 at score1000 with the same
promotion action and legal two-action PV. At qdepth1, both still complete depth2
at score1000 and both PVs replay legally, but Core selects that promotion while
Native selects `a3-a2`; qnode counts are11 and16 respectively. The equal score
and absence of exact root-action values leave a tie/order explanation open, so
the action difference is not classified as a semantic defect or utility change.
This records one finite generated-semantic promotion case only. No backend or
qsearch default change follows. Compact evidence:
`data/native_semantic_promotion_qfrontier_20261020.json`.

## Recheck of the saved generated-semantic promotion qfrontier — 2026-10-20

The prior 3x3 SHOGI_LIKE record was reconstructed with the same semantic rule,
material values, full valid history sentinel, and D2/1000-node/3-second/qdepth1
budget. Core again selected `b2-b3=G` (score1000,30 total nodes/11 qnodes);
Native again selected `a3-a2` (score1000,32/16). Native exact-root mode retained
a3-a2 (33/15). Making either move a legal root-order hint in exact-root mode
still selected a3-a2 with score1000; this does not distinguish a tie from a
strictly better quiet move.

A fixed-child D1 probe gave both engines equal values per action (promotion1000,
quiet100), but the engine's first completed iteration intentionally uses ordinary
qdepth0 even when qdepth1 is requested. Those values are therefore not the
same D2/qdepth1 action backups and cannot resolve the original discrepancy. The
public result exposes selected action/PV and iteration metadata, not all exact
root-action backup values. No utility, semantic defect, source change or default
change follows. Keep this as a bounded unresolved traversal/value question; do
not add a tracing API or another game panel for this one fixture. A new question
needs a separate changed premise and a decision consequence.