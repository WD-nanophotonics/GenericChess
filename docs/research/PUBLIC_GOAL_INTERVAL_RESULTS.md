# Public goal intervals: bounded acquisition and complete-choice scope

Research segment started 2026-10-04T06:45:35Z. This is a qualified goal-label
acquisition primitive, not a static material prior. It advances the partial
goal-risk contract by replacing hypothetical intervals with an executable
observer on public legal transitions, without consulting a search evaluator.

## Phase 1: board-action acquisition

`PUBLIC_GOAL_INTERVAL_PROTOCOL.md` froze four existing Chess controls before
the run. `scripts/public_goal_intervals.py` propagates owner-zero intervals
over exact public GameStates. Ongoing depth frontiers are [-1,1]. Budget/time
interruption explicitly adds an unknown child to the parent; empty ongoing
legal sets fail. Max/min combines lower/upper bounds. The goal range allows
an exact +1 max-node/-1 min-node shortcut without full action enumeration.
Fresh terminal_result must agree with the cached state; full history/counters
are preserved. No TT, material values, quiescence or static leaf evaluation
is involved. A time cap is cooperative and may overshoot inside a public call.

The initial Chess position remains [-1,1] at depth1 after 20 materializations,
21 visits and 20 unresolved leaves. The existing immediate-mate root becomes
[1,1] after 24 materializations/25 visits, while ten encountered nonterminal
leaves remain unresolved. Its range shortcut is justified by a genuine legal
win, not an assumption that those ten leaves are draws. Existing checkmate
and stalemate child controls give [1,1] and [0,0] at depth0 with no transitions.
Rules/root construction took about0.032s; ongoing controls took about0.046s and
0.032s respectively; selecting the two existing terminal controls used another
24 public transitions. The hashed detailed record is
`data/public_goal_intervals_20261004.json`. These are familiar diagnostic roots,
not new independent material-performance observations.

An independent complete tiny-game oracle checks every depth0..3,
transition budget0..5, visit budget0/1/3/6, both owners/action orders and all
three leaf outcomes. The returned interval always contains the complete value.
Fake-clock cuts check interruption without sleeping. Cached-terminal mismatch,
censoring, no-contest and malformed limits have explicit controls. The first
six tests passed; this was a checkpoint, not the end of the segment.

## Phase 2: observed declaration coverage gap

Inspection of Core declarations and GameSession found that legal_actions alone
omits optional Shogi claims. A board-action observer cannot claim full Session
choice coverage. `PUBLIC_GOAL_INTERVAL_DECLARATION_ADDENDUM.md` froze a narrow
extension before running it; original protocol bytes were retained.

PublicGame now includes available_declarations in its choice stream, reassesses
each choice on the exact parent and produces an immutable virtual outcome leaf.
WIN supplies the actor's +/-1 label, DRAW0. RESTART remains [-1,1], because a
replay has no specified W/D/L in this target. Parent state/history is untouched;
no public board transition is fabricated. Report choice transitions separately
from public board materializations. LOSS declarations and resignation are
dominated by an ordinary choice with value in [-1,1]; they cannot improve the
acting owner's minimax value. Terminal Session states disallow declarations.
Depth0 does not query new choices and therefore remains unknown when ongoing.

Existing Shogi score31/score24 declaration fixtures were checked for both
owners. WIN gives [+1,+1] or [-1,-1] with one choice and zero public board
materializations. RESTART stays [-1,1] even after the one-choice budget; it
does not certify a draw or a loss. Session assessment and unchanged parent
state agree; stale declaration assessments fail. These are existing rule-bound
point thresholds, not inferred piece values. Eight observer tests plus existing
declaration semantics/integration tests pass (41 total at this checkpoint).

A ninth observer test then pinned protocol/addendum/observer hashes and the
compiled Chess ruleset fingerprint. With five partial-risk tests, the relevant
combined run passes47. This preserves provenance rather than generating a new
performance corpus or repeating the old score comparison.

## Mainline consequence and limits

The generic range arithmetic is now backed by a bounded public adapter and
choice-scope checks. Soundness remains conditional on the executable RuleSet
and its complete choice contract. Censoring an artificial max-ply terminal only
widens that label; it does not specify an official uncapped game's continuation.
Shogi's unqualified stalemate convention must be separately censored or qualified
before any official-goal dataset is admitted. Restart/no-contest is unresolved.
No sampling measure, complete cross-game game values or prior is established.

Earlier V2H provenance/applicability closure and service/count-transfer failures
stand. No old global deployment labels, human values or Xiangqi material holdout
were read. Next address the independent candidate/strategic deployment premise,
not repeat mate roots or expand the observer search to obtain a desired score.
