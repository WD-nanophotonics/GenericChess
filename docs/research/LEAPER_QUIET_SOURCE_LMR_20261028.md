# Pure-Leaper source qualification and selective-search pilot — 2026-10-28

Status: scientific batches closed; delivery follows the verified Git commit. The source studies and fixed LMR batch are closed; all
16 games passed independent literal/Core/PV acceptance. LMR failed its frozen
quality gate and remains research-only. A later one-child source diagnostic
FAILED at a record serialization boundary and is retained as unverified.

## Decision and motivation

The priority is finite-resource decision quality on admitted pure-Leaper rules,
with complete histories and clocks. Quiet-defense coverage requires an actual
source witness before implementing a new controller. An absence of a two-ply
witness does not refute deeper quiet-defense mechanisms. After the finite source
checks below found no such witness, a separate conservative late-move reduction
(LMR) experiment tests resource allocation over the existing PVS reference.
Neither route expands to mixed rules, NNUE or a new solver.

## Source selection and new evidence

The first post-material-removal, non-check, mixed noisy/quiet state in each of
eight exposed development families was selected in original game/ply order,
before reply outcomes. Material removal does not assert a reciprocal exchange.
Seven exact old descriptors were reused and one was newly constructed. Six new
censuses plus two exact old censuses required 3,010 new Core reply transitions;
all eight had zero locally losing actions and yielded no coverage candidate.
An initial JSON-list loader error occurred before any Core query; the original
failure and unchanged selection/caps are preserved, rather than replacing it
with a successful return.

A changed-premise scan then examined all 2,130 saved pre-action histories from
30 already completed games, in original game order and reverse ply within each
game. All 881 eligible post-removal, non-check, mixed frontiers had at least one
noisy action with no terminal-loss reply at the tested one-reply horizon.
This is a sufficient negative certificate for this particular all-noisy-lose
criterion; it is not a winning-defense certificate. All 1,249 exclusion reasons
were checked. There were 5,716 new reply transitions, zero candidates, zero
UNKNOWN and zero unvisited slots. An independent literal reader verified all
2,130 history hashes and the 881 certificates with 16,270 Core transitions.
No new Player call, game, controller or WDL solver was used in this scan.

A separate finite-clock mechanism check froze the first actual max-ply terminal
game per family and its H-1/H-2 histories, preserving the original H96 rule.
All 16 literal terminal-only endpoint certificates completed (1,015 Core
transitions). Across 64 artificial wide-window direct queries, value mismatches
were Q4:14, first-Q0:16, D1/Q4:6 and D1/first-Q0:8, but there were **zero
suboptimal D1 root choices**. This is numerical boundary evidence, not an
observed quality repair or the causal explanation of an older root reversal.
The already-existing clock-cap route was not reimplemented.

## LMR mechanism, controls and frozen comparison

The official [Stockfish search source](https://github.com/official-stockfish/Stockfish/blob/master/src/search.cpp)
is a mechanism reference, not evidence that its chess-specific constants work
here. The single prototype reduces a child by one nominal main ply only for a
late (zero-based index >=4), non-root, non-PV null-window quiet dispatch from a
non-check parent at nominal depth >=3; the child must be nonterminal, have depth
>=2 and have both window endpoints outside the mate band. It preserves actual
ply, history, clock, action order and existing quiescence policy. A reduced
result that can raise the parent's alpha is searched again at the original
child depth and window. Cancellation and exceptions propagate normally.

This is **selective**, not equivalent full-depth minimax. A reduced fail-low
can miss a deeper improvement, and a unit counterexample explicitly preserves
that risk. Selective TT results are owned by a fixed-policy Player, never
shared between arms or imported. A mate-band score is not an all-defense proof.
The prototype is confined to the research process and introduces no product
flag or default activation.

Before candidate results, a bounded observer ran eight OFF/ON/OFF D4 triads.
All 24 queries returned; all eight triads had exact result/work parity. Five
families had eligible actual dispatch samples. Logged dispatches are not saved
work. The observer added no online classification, evaluation or ordering calls.

The candidate passed its frozen feasibility gate: eight complete candidate D4
queries, five active families and aggregate wall/reference ratio 0.941899.
The 16 references are byte-pinned, already-paid, same-build historical brackets;
they are **not** newly interleaved controls and establish no causal speedup.
Nineteen policy controls, including actual cancellation/undo and sixteen clock
endpoints, passed; three observer controls and eight reader fault controls passed.

The next frozen gate is 16 games: one complete original root in each of eight
families, both seat assignments, both arms PVS ON, only LMR differing. Service is
1.5 seconds including construction/packing, 500,000 nodes, D64, ordinary Q4/hard8
with the existing initial Q0 iteration. Each seat has a fresh policy-owned Player
whose TT stays with that policy. Absolute original clock/repetition/history are
preserved. All eight roots remain in the panel; no result-based filtering,
refill or retuning is allowed. Per-game cap is 180 seconds, batch cap 2,700
seconds, whole-task cap 85 minutes from 14:04:25 UTC with eight minutes reserved
for closure. Missing/aborted slots remain UNKNOWN, never draws.

Proceeding requires all 16 timing-eligible Core terminals, at least four net
positive families and at least 55% raw points. A pass would justify further
investigation only. These are exposed development rules, not a holdout, and
PVS is enabled in both arms; this cannot demonstrate improvement over the
PVS-OFF desktop default or class-wide strength. This is separate from the
user-deferred earlier Native-service proposal.

## Review, reproducibility and delivery

The opening GitHub review at c42f006664e028cc9792a5bea40c711005ef23c9 was read
and adopted: decision quality and source falsification precede transport work.
Its remote-only view did not include these local results. The opening Dot
AGENT_REQUEST and one five-minute check completed; its two-ply quantifier and
stand-pat warnings were applied. A later source-route follow-up had no reply at
its single delayed check; absence of a reply is not a work gate.

The user-authorized review-only fast-forward to
6b62bf331484169301904db7748a0796bb423271 completed. The earlier per-document consent queue was superseded by the latest direct
USER2026-10-29 default-approval instruction. Four reviewed document-only
additions through c4d1cdca were fast-forwarded after exact diff/content checks.
Normal reviewed publication proceeds under standing authority;no force push,
history rewriting,AUX-state change or new worker is used.

Full rules/history inputs are in
[data/leaper_quiet_source_20261028/inputs.json.gz](data/leaper_quiet_source_20261028/inputs.json.gz).
Frozen plans, literal originals, source hashes, negative/partial outcomes and
independent acceptance will be sealed in technical bundles at batch closure.
Private Slack wrappers/account information are excluded from publication copies.

## Closed LMR outcome and decision

All sixteen games ended under actual Core rules: fourteen max-ply draws and
two repetition draws. There were no missing or ineligible slots. LMR scored
8/16 points and zero positive families, so the frozen gate **FAILS**. Do not
enable it, tune a replacement threshold or refill the batch from these results.
This is no observed benefit on this finite panel, not proof that LMR is useless.

The independent reader verified 1,360 literal original returns, 1,360 actual
submitted Core transitions and 5,188 PV steps; no final orphan originals remain.
Both arms made 680 returns. Actual ON activity was 33,092 reduction attempts,
31,934 kept reduced fail-lows and 1,115 full-depth retry attempts. Cancellation can interrupt a reduction or its
retry; these counters do not partition completed subtrees. Classification consumed 0.881429 seconds. ON service time was
1,008.518739 seconds versus OFF 1,006.912895 seconds; these are descriptive totals,
not a matched speed comparison because later histories differ. Maximum observed
service was 1.611998 seconds, below the frozen caller's 1.65-second eligibility
ceiling; requested allowance was 1.5 seconds, not a guaranteed atomic hard stop.
All eight cold original-root action pairs matched. All eight direct D4 candidate
scores/actions/PVs also matched their reference, despite reductions in five
families. Nominal depth and internal work never replace quality evidence.

## A narrower source limitation, and an honestly failed diagnostic

A prospectively fixed first-sixteen-per-family sample of 128 negative source
certificates completed: 120 children were in check and two were terminal.
This selected sample is not a population frequency estimate. It supports the
possibility that a checking noisy move postpones the threat beyond the tested
one-reply criterion; it proves neither later loss nor quiet superiority.

The first qualifying checking child with at least eight original clock plies
remaining was frozen at source index0/family0/prefix51. Its single bounded
three-more-ply terminal-certificate attempt FAILED after the first opponent
branch: the existing replay helper expects a JSON record, while this new caller
supplied a GameRecord dataclass at the next clone. The original source and
frozen plan are retained; no certificate or independent acceptance was produced,
no refill/retry was run, and no missing branch becomes a draw. The inferred one
completed extension submit is explicitly not a saved measured counter. No work
interval is credited for that failed invocation. The caller now converts through
the existing record-value contract and preserves future partial exceptions;
two JSON/public-record boundary regressions pass. A test import-path collection
error was corrected to the actual session.serialization module before that
acceptance. This interface validation is not verification of the failed tree.

## Next useful action already prepared

The next question is a baseline decision-error diagnostic, rather than another
LMR setting or draw-heavy game batch. Nine source-labelled H6 forks were
preselected in fixed source order, at most one per family, excluding immediate
root wins and requiring distinct values among nonterminal actions. The source
commit is 5584387c8de5b23a3b1524cce9c29bd694bee2d8; both literal input/truth hashes
were verified. This consumes published evidence without running AUX code or
changing its state. These are exposed, source-attributed shared-Core labels,
not newly proved truth or a holdout. The next opening must check strict compiler
admission and exact prior service/configuration matches, reuse exact existing
returns, and freeze actual query indices before any new 1.5-second PVS-only
Player call. At most twelve baseline calls are permitted by the prepared plan;
none has started. No new game, general solver, feature or default change follows.
A mismatch would still need independent action-value evidence before a defect
claim, and H6 results cannot establish H96 or class-wide strength.


Delivery/priority update2026-10-29: the new c4d1cdca autonomous review was read
in full and saved before integration. It independently prioritizes legal quiet
coverage,standpat/windows,parent-choice causality and finite cost. Its snapshot
could not see these just-closed local results. Adopt that next source-only
priority;the nineH6fork preselection is retained with zero new queries and
locally deferred,not a user stop. The old LOCAL_ONLY/awaiting approval statements
in sealed raw evidence describe its original capture state,not a current
permission gate. Routine project work is now explicitly approved by default;
record necessity/caps locally and escalate only serious errors,threats or
actual blockers requiring human intervention.
