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
