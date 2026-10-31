# Proof-number mechanism scope and whole-decision cost — 2026-10-31

This is a source/literature assessment, not a new proof search, Player comparison,
game, training run, speed measurement or PRIMARY algorithm implementation.
The old same-board/history consumer line closed when the new Pro review arrived.
No more calls or verification on that old example are proposed here.

The useful next choice is whether a future proof-driven policy can improve the
actual public mainline player's decisions under one whole-service allowance.
Existing research PN components are reusable for proof generation and checking,
but their current chooser is not a drop-in mainline alpha-beta control. Textbook
df-pn memory/speed claims and PN node counts do not settle that choice.

## Source authority and actual coverage

Latest Pro596837f94d5002875e2bb7730956c00178827af4,
docs/reviews/chatgpt_patrol/20261031155737_JST_e4565fa3.md,
blob72d5df6729bf0ae6182b34484ded1819e3f5493f was fully read and ADOPTED.
It closes repeated history-existence work and prioritizes transferable decision quality.
PRIMARY retains its mechanism/producer/default ownership. User standing instructions
authorize this complementary scoped analytical work; they do not authorize new workers,
a new timing campaign, a second rules engine or restarting exhausted studies.

The original author-hosted [van den Herik and Winands2008 chapter](https://dke.maastrichtuniversity.nl/m.winands/documents/pnchapter.pdf),
DOI10.1007/978-3-540-70829-2_6, was downloaded and the relevant complete pages read.
PDF SHA256038921790db69f9984755f01e66bf62c7ed53cd2c5ce1bc80bf3261cabda8275.
See data/aux_pn_mechanism_scope_20261031/source.json for exact page/visual coverage.
The PDF and text originals remain private. This is the authors' chapter and its
reported LOA experiments; Allis1994 was located by DOI metadata but not read in full.
The publisher retrieval failed; no unavailable article is silently treated as read.

Project source is fixed at sidemission8406a540fb0a27c5d9b117425a372b7429547a4c.
Shared runtime is the committed baseline already reused; the new Pro commit adds
Markdown only. The read source hashes qualify local reads, not a new ID framework.

## What the paper actually establishes

Pages3-4 define a binary target: forced WIN is TRUE; LOSS or DRAW is FALSE;
unresolved leaves are UNKNOWN. Proved leaves carry(pn,dn)=(0,infinity),
disproved leaves(infinity,0), unknown leaves(1,1). At an OR node:
pn=min(child pn), dn=sum(child dn). At an AND node:
pn=sum(child pn), dn=min(child dn). These are proof obligations in the present
tree, not calibrated win probabilities, material values or root-action regret.

Pages5-7 discuss mobility initialization and memory-saving successors.
Pages6-7/12 explicitly discuss graph-history interaction; the PDS implementation
used in those LOA experiments ignores that issue. The chapter does not license
omitting GenericChess repetition, clock, Session-only results or legal defenses.
Nor does its df-pn discussion prove a general deployment advantage on arbitrary rules.

Table3/page10 reports a forced-win LOA set of488 positions:
alpha-beta solves383, plain PN356, PN-squared470 and PDS473 under the stated limits.
Plain PN is much faster on the314 positions solved by all four yet solves FEWER
positions than alpha-beta overall because of memory failures. A common-success
time subset and total success coverage are different outcomes. The chapter also
uses different node-count conventions for the methods. Its later df-pn/PDS-PN
comparisons acknowledge different hardware/data structures and call for a direct
matched comparison. None of these factors is a Leaper speed or strength forecast.

Page26 identifies dynamic selection between PN and alpha-beta during real play
as an open issue. A threat trigger is therefore a new policy hypothesis to test,
not a theorem supplied by the literature.

## Existing code already available

| Existing component | Actual behavior | Consequence for future reuse |
| --- | --- | --- |
| generic_session_win_proof_pn | Full public GameSession PN tree, complete typed choices, independent Session certificate output | Reuse proof semantics; no need to rebuild an AND/OR engine |
| generic_session_win_proof_batch_pn | Immutable full state/record forward nodes; eager public Core successors | Fewer inspected nodes can still pay the full generated batch |
| terminal_first/check_first variants | Preserve lazy declarations and ALL quiet/defender choices; reorder already generated children | These are existing controls, not a new invention or check-only proof |
| generic_session_win_proof_threshold | Retains the entire tree; accepts only a complete declared rule horizon | It is not a general depth-cutoff, memory-saving df-pn implementation |
| SessionStrategyCursor | Independently verifies then binds/observes actual complete Session edges | A logical certificate is distinct from a played terminal or TDLeaf target |
| SessionPhasePlayer | Separate proof/verifier/normal caps plus a whole deadline | Phase units and total service must remain separate in any comparison |
| SessionLogicalProofBank | Research-only historical logical reuse with explicit physical receipts | A cache hit is not current verification or a free normal-budget donation |

No component above was executed in this source study. Existing tests and prior
experiments are source evidence only; exhausted caps are not reopened.

## Two concrete adoption obstacles

First, SessionProofMaterialPlayer and SessionPhasePlayer default through
scripts/generic_proof_player.py::ProofMaterialPlayer. Its normal fallback is
a separate, simple material alpha-beta over SearchPathRuntime, not the mature
generic_chess.ai.alphabeta.player.AlphaBetaPlayer with its current public
GameSession/TT/q/ordering/result metadata. Comparing that default with a mature
mainline player changes more than the proof mechanism.

The optional normal_search callback takes(state,node_allowance,seconds,cancel)
and returns(action,used_nodes). That narrow return does not preserve the full
public PlayerDecision depth/PV/declaration/provenance contract. An adapter which
silently reconstructs a Session from a board would be invalid. A future PRIMARY
implementation must deliberately retain its actual Session/current mainline
search and rich decision metadata; this report adds no adapter or wrapper.

Second, the threshold prototype checks compiled.max_ply<=max_depth before search,
uses None for an unbounded threshold, and relies on finite open proof/disproof
sums. Artificial-depth UNKNOWN leaves are refused rather than treated as draws.
It retains all _Node children and full forward records; recursion avoids repeated
root descent but does NOT establish textbook df-pn memory reduction. Using it
with a shallower generic depth limit returns requires_complete_rule_horizon,
not a new efficient bounded solver. Existing tests already cover this refusal.
No extension, TT replacement or threshold patch is justified by this source read.

## Cutoff and disproof remain typed information

Current PN uses(pn,dn)=(infinity,infinity),closed for a nonterminal depth frontier;
node/time/cancel interruptions return UNKNOWN without a certificate. An actual
dn=0 proves the binary target false only under the explored complete proof
obligations; it still combines DRAW/LOSS and may include neutral Session endings.
The public API conservatively returns UNKNOWN rather than manufacturing a DRAW
or an opponent-WIN certificate. Existing AUX mate-disproof controls already
establish the LOSS/DRAW distinction; no new example or checker is needed.

For ordinary scored WDL games one may reason with two distinct predicates,
V>=1 and V>=0: the first true proves WIN, the second false proves LOSS, and
first false plus second true proves DRAW. This is an analytic decomposition,
not a feature of the current WIN-only Session certificate. Generic NO_CONTEST
is outside that numeric order. Existing one-sided bound readers can check
supplied finite move strategies in their admitted scored scope, but do not
support arbitrary declaration choices. Reuse those limits rather than pretending
a WIN verifier already validates nonloss/refutation or adding a duplicate framework.

Positive restricted attacker-choice search can still find a valid WIN witness
when EVERY defender response remains covered. Omitting defender quiet moves,
drops or owned neutral declarations can falsify a purported proof. Conversely,
disproving a restricted attacker subset does not disprove the full game.
The current check-first implementation orders quiet moves; it does not remove them.
A future threat heuristic should preserve these logical obligations and independent
verification; a low proof number or checking line alone is not a WDL label.

## Evidence that would change the decision

Use the actual mainline full-service baseline, not the old research fallback.
Freeze ONE intervention before any future call, including whether it is proof
selection, a trigger, or partial-proof ordering. Current PN returns a certificate
or UNKNOWN; it does not export a per-action partial-number ordering policy.
That is a real implementation distinction, not permission for AUX to add one.

A verified candidate WIN action has true actor-relative value+1 in a scored game.
Its advantage over a baseline action with interval[L_B,U_B] is
[1-U_B,1-L_B]. Unless U_B<1, strict quality improvement is not proved.
A changed root action or a certificate that the ROOT is winning does not by itself
show that the baseline selected a losing/drawing action. Retain useful partial
bounds and UNKNOWN instead of promoting a success count to strength.

All construction/admission, proof, certificate construction, independent
verification, fallback search, continuation checks and packaging must fit the
declared whole service. Proof visits, eager Core successors, verifier visits,
normal nodes and wall/CPU/RSS measure different work. Publish actual censored/
failed slots in the fixed denominator. No game or new producer is authorized
by this methodological assessment; PRIMARY owns any later frozen comparison.

## Source-derived independent verification work

For a COMPLETE ACCEPTED certificate consisting of ordinary Session actions, let
N be visited tree-node occurrences(root included), h0 the number of actions in
the authoritative root record, and d_i each node's depth from that root.
The present independent Session checker performs exactly

submit_calls = N*h0 + sum_i d_i.

It first replays the root(h0 submissions). Each edge replays its parent record
(h0+d_parent actions), then submits the edge once, paying h0+d_child.
Summing gives the identity. This counts occurrences, not distinct object IDs.
The source is generic_session_win_proof.py::verify_session_certificate together
with GameSession.replay. It is a SOURCE DERIVATION, not another old-certificate run.

For ordinary-action trees of maximum depth D:
N*h0+(N-1) <= submit_calls <= N*h0+min(N*(N-1)/2,(N-1)*D).
A65node chain with h0=0 implies2080calls; a65node one-level tree implies64.
With h0=32 these become4160 and2144. These are conditional abstract shapes,
not newly realized Leaper games or performance measurements. Equal node counts
plainly do not fix this replay work, and no CPU/time speedup follows from the count.

Partial/failing checks need different accounting. Root replay happens before
the first visited node, so a zero-node refusal can still pay h0 submissions.
A child is replayed/submitted BEFORE its budget.visit; a cap can be reached after
one such extra edge. A successful-tree formula must not be applied to a failed
return as if its node count described every paid operation. Declarations and
resignations are separate Session operations; custom initial-setup construction
and legal-frontier/terminal computation add cost beyond this outer-call count.

Likewise, eager Core PN may generate an entire board frontier before inspecting
its first child. A cap1 return can pay a whole batch while visiting only the root.
Current metadata distinguishes eager_board_successors,transitions,frontiers and
new tree nodes. Public atomic operations can cross a deadline between polls;
their actual elapsed work remains part of the outcome. None of this is a new
bug reproduction or authority to patch the checker; the point is correct
whole-service interpretation before choosing a mechanism.

## What a safe replacement can and cannot guarantee

In a scored WDL game at one fixed full context, a verified/adopted root action
winning for the actual actor has value+1. Against any legal baseline action with
value interval[L_B,U_B], its advantage is[1-U_B,1-L_B]. This is nonnegative, but
strict improvement needs U_B<1. A root WIN proof does not supply the baseline's
missing action upper bound. There is no need to demand complete WDL everywhere:
one useful one-sided bound can establish the relevant strict difference.

A baseline-FIRST policy can retain a completed legal baseline-prefix action,
try bounded proof in the remaining allowance, replace it only by a verified WIN,
and keep it on failure. Its root-action quality never decreases relative to
THAT retained prefix. This says nothing about domination of a separately run
full-service alpha-beta baseline, which may complete different later work.
The current research chooser is proof-FIRST and lacks that retained full-budget
baseline; its failed proof attempts can reduce fallback service.

For M fixed planned paired slots, split S into verified AND usable candidate-WIN
returns and F into all remaining/failed/censored slots. The finite root-action
difference is sum_S(1-Q_B)+sum_F(Q_H-Q_B), divided by M.
A conservative lower bound is[sum_S(1-U_B)-2*|F|]/M. For a missing action,
this is a bound over possible legal completions of its planned slot, not an
imputed observed action or WDL. An explicit protocol failure penalty would
define a different metric.
Without baseline upper bounds below1, successes alone do not certify a positive
whole-policy gain. Dropping F manufactures a success-conditioned objective.
This is deterministic partial-information algebra, not an IID/population model,
a new statistical acceptance gate or a reason to block cheap exploratory tests.

Finally, a root certificate promises a winning continuation EXISTS and supplies
one finite decreasing-rank strategy. Actual play must follow it, cover every
opponent choice and meet later resource/cancellation conditions. A returned
verified action, a dispatched/committed move and a later actual terminal win are
different observations. Cursor observation validates hypothetical copies after
the one physical commit; its time is not necessarily inside chooser.seconds.
Construction, packaging and commit/observer costs must be included in the
declared whole comparison envelope or explicitly bounded/reported separately.
A published1second search limit must not silently be renamed1second all-in time.

No new search policy, verification optimization, guard, framework, game or worker
was implemented from these deductions. The cheaper actionable next step remains
PRIMARY's own single frozen mainline mechanism comparison if it proceeds; AUX can
consume actual complete outcomes/bounds without reopening old studies.

## Existing mature any-win behavior is part of the baseline

The public mainline already retains a qualifying completed winning root child
if a later sibling aborts the whole iteration. stop_after_root_win=True optionally
stops earlier; False does not mean that all completed-child evidence is lost.
The public result retains completed_root_win versus main_iteration provenance
and the last actually completed uniform depth. A compatible warm winning TT
return has its own path. Existing product tests cover real three-ply wins,
mate-window equality, providers, cancellation/time controls and oversized static
scores. We read their source; we did NOT re-run their Player calls.

Consequently, salvaging a completed root WIN is baseline infrastructure, not a
new PN improvement. A new mechanism must add a useful search/allocation behavior
beyond the mature Player while keeping its actual full Session/TT/q/ordering
contract. The source search found no current direct full-PlayerDecision PN
chooser in generic_chess/scripts; the old research callback remains narrower.
This is stated source coverage, not a claim about another agent's unpublished work.

Conversely, a public mate-band return is not the exported independently verified
all-defense Session certificate type. Current TDLeaf correctly rejects a nonliteral
completed_root_win prediction rather than treating an ongoing root as a played
terminal. Root action quality, a literal PV target, a complete uniform depth,
a finite certificate rank and a deepest visited PN node are different quantities.
Proof rank does not establish shortest mate, and no ratio of PN rank to alpha-beta
completed depth is a meaningful speedup measure.

The original LOA study deliberately used forced-win positions. It therefore does
not estimate a threat trigger's online success frequency in a new mixed WIN/DRAW/
LOSS Leaper population. Unknown opportunity is a reason for one cheap frozen test,
not an approval gate or a reason to declare PN universally useless. A failed
WIN-only query also cannot choose between safe DRAW and LOSS actions merely by
returning binary false; that distinction is already handled by the existing
truth/bound contracts.

## Physical calls versus pairs in the prospective Pro suggestion

The Pro suggestion combines at most32one-second search-service queries with
paired comparisons. Those must be PHYSICAL calls arranged in pairs if the nominal
service sum is32seconds. For example8families x2layouts x2arms gives32calls and
16paired comparisons. It is not32pairs/64calls. This is arithmetic clarification,
not a frozen or launched AUX experiment and not a new task allocation.

Every attempted fixed slot keeps its status; a started failure consumes its
invocation even if its return is lost. The current round's failed5/4probe is
already preserved as exactly that error, not made successful by this advice.
Nominal limits can be crossed by atomic operations, so actual cumulative service,
censoring and the separately declared construction/verification/whole envelope
must be retained. Do not silently add retries, replacement roots or unplanned
seed repeats. These are evidence/accounting definitions, not a new scheduler,
registry, permission queue or defensive wrapper.

## Witness retention changes the paper's memory tradeoff

The chapter deletes solved subtrees to reduce stored nodes while preserving
logical proof/disproof summaries. The present exact Session route has another
consumer: certificate(node) recursively exports a concrete selected OR branch
and every required AND branch; SessionStrategyCursor later follows that tree.
Deleting a proved subtree merely because pn==0 would remove evidence needed by
this consumer. A TRUE summary is not the full typed legal-defense witness.

Keeping a compact witness or regenerating it can be reasonable space/time choices,
but each has construction/verification/continuation costs. This report neither
implements one nor infers a memory win from textbook df-pn terminology.
That is why the current retained-tree threshold scheduler must be described by
what it stores, not by the name of a superficially similar depth-first algorithm.

The distinction does not block exploratory work. It tells a future SINGLE small
matched experiment which outputs/costs to retain and which outcome can change the
next decision. No complete WDL map, calibration campaign, new registry or repeated
approval is required before a user-authorized bounded hypothesis test.

## Cheapest relevant control before a new mechanism

If the objective is ANY WIN, the existing public stop_after_root_win option is
a relevant cheap baseline. Comparing a candidate which stops at any verified WIN
against a baseline which continues sibling work for a whole iteration/shorter mate
can measure an objective/termination-policy difference already available without PN.
Choose and freeze the relevant ONE baseline before a future comparison, or label
the result as a combined-policy comparison. This does not add an arm/call, demand
a rerun, or invalidate a clearly stated combined-policy result.

An execution-kernel saving means equivalent fixed work becomes cheaper. A
decision-policy saving can instead mean that a correct sufficient endpoint permits
less work. A quality gain means different work under matched service chooses a
better action/outcome. These are all potentially useful, but evidence for one
must not be renamed another. Existing any-win retention and rich result provenance
help make that distinction without new middleware.

Fresh alternatives were examined at this checkpoint: extending the closed alias
or failed-call probe is rejected; implementing another wrapper/checker or launching
an unfrozen PRIMARY panel is deferred; original-source PN/baseline/service analysis
has now supplied its concrete boundaries. The next useful AUX work is an actually
new published mechanism packet or a specific source correction, evaluated under
the latest Pro/user plan rather than another copy of these old examples.

## Accepted segment boundary

Session389af24c safe_checkpoint finish was accepted at08:04:45UTC, same06:31:01UTC
origin and memo ENDED.3786.861988confirmed seconds minus120conservative mixed-work
reserve leaves61.114366effective minutes. Seven checkpoints and14offline tests
support the declared work; the clock is not independent cognitive telemetry.
All later publication/transport/closing intake is administrative and uncredited.
The original5/4q0probe failure remains a failure, with no refill or normal-duration
excuse. See accounting/session-ledger/finish for actual accepted receipts.

Closing remote15b17795 adds PRIMARY research source/data only. Its kernel report
and manifest were preserved/read as SOURCE_ONLY;194compressedmembers were not
consumed or independently remeasured. That source and the next executable memo
preserve the latest Pro quality direction without starting another packet-audit
or cache campaign in this completed segment.
