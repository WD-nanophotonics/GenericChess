# AUX mating-disproof scope: actual LOSS and DRAW —2026-10-28

A binary failure to force WIN cannot be converted into DRAW. Two independently
verified, legal full-history contexts from the new published7x7 packet show the
stronger full-game no-forced-WIN predicate with different actual WDL: one LOSS
and one DRAW. This is a concrete certificate-admission control, not a new solver,
new game, quiet-defense mechanism or PRIMARY algorithm implementation.

## Exact primary sources and applicability

[Kishimoto2010](https://ojs.aaai.org/index.php/AAAI/article/view/7534/7395),
DOI10.1609/aaai.v24i1.7534, addresses df-pn loops and proof/disproof-number
under/overestimation using TCA/SNDA. Its implementation relies on earlier
cycle-proof TT handling; general finite-DCG completeness remains a future
investigation, not a theorem established there. These are search-guidance and
progress results, not authority to merge GenericChess histories or treat a
budget stop as an exact game value.

[Kaneko2010](https://ojs.aaai.org/index.php/AAAI/article/view/7551/7412),
DOI10.1609/aaai.v24i1.7551, is the distinct parallel-df-pn paper. Its checkmate
objective, shared work estimates and use of interim results are not a full
three-valued GenericChess adjudicator. It separately refers to GHI treatment.
No parallel machinery or worker was implemented. Both Pro references exist;
there is no claim that the links/authors were erroneous.

Original PDF bytes were privately retained, not republished. SHA256:
7534 =719cfd195896f29a53fe3b313a9b7413fd00b1968bdf25ec4d055e52d9b5eb1e;
7551 =89f76fe1747aa4e4a70efcdc6a014565a3a8b785ac90b51dda399cd9640fe3ac.
This source read is distinct from the already closed2004GHI review.

## Project-specific deduction, not a paper claim

For these12 literal source rules, compilation confirms max_ply128, repetition4,
draw policy, and no automatic/consecutive/cycle-target/no-progress adjudication
or declarations. Current Core adjudicates terminal precedence before the hard
clock; every ongoing reachable context in this admitted scope has ply<128.
Every legal proof edge increments absolute ply. Thus the complete-history/clock
representation is acyclic, even when the board repeats. This observation cannot
be transferred to products with automatic PENDING continuation or an omitted
clock/history component.

The observed saved-record forest itself has12 roots and E=N-12, by its
conservative record encoding. That is an encoding fact, not proof that a future
engine has no semantic transpositions or that source-node detection is cheap or
unnecessary generally. No current TT identity, rule semantics or backend changed.

## Actual counterexample and precise authority

Pinned new packet source c42f006664e028cc9792a5bea40c711005ef23c9; qualified AUX
source70bbc33bc6b13d2893774c19151b80f40cf1f679. Both contexts name seat1 as the
attacker. The contexts belong to distinct literal RuleSets/initial layouts, so
these labels are never pooled or transferred between them.

* LOSS: the ply15 full-history subcontext of the already verified three-edge
  WIN-seat0 strategy. The existing verify_bound_tree checks a two-edge upper
  bound -1 for seat1, including every legal seat1 defense and a real terminal
  loss. Together with the trivial lower bound -1, actual seat1 WDL is[-1,-1].
* DRAW: a legal ply127 context under the other exact rule/history. All18 legal
  actions end in actual Core draws. A one-action lower0 certificate and complete
  eighteen-action upper0 certificate independently establish actual[0,0].

Both therefore satisfy the stronger full-game predicate cannot-force-WIN. They
still have different WDL. Even perfect full-game disproof would not distinguish
LOSS from DRAW; failure of a restricted checking strategy supplies still less.
No mating-search run or returned disproof is being fabricated here. No claim is
made that this pair is a legal quiet-WIN counterexample to checking-only search;
that would require a separate, actual witness and is not needed for this logical
admission decision.

The unchanged checker already requires exact rule/history/clock, a named value
seat, all required universal defenses, legal Core transitions, increasing ply
and actual terminal leaves. A bare disproof flag/number, cancelled search or
unproved leaf fails to supply that certificate. A restricted positive mating
proof can only support a full-game lower bound after its real defender action
coverage and rule terminals are independently checked. A restricted disproof
or exhausted budget remains UNKNOWN for the full three-valued objective.

Five new real-context controls plus the previous27 pass32tests: LOSS/DRAW
certificates, wrong named attacker, a changed history and an unproved leaf with
a claimed disproof flag. The existing checker is reused, with no new admission
framework or approval gate. Tests/fixtures/mate_disproof_not_draw.json.gz is a
small portable witness; full derived evidence/hashes are in the adjacent data
folder. Verification computes known supplied edges only, not new continuations.

Decision: adopt the papers as scoped algorithm background, reject any inference
that they themselves authorize WDL labels, omitted defenses/history or unlimited
progress. Current AUX proof admission needs no product change. This finite source
question is CLOSED; do not re-read the same papers or expand the witness merely
to occupy a work interval. The ordinary session remains governed by its actual
confirmed work ledger and proceeds to a distinct useful question.
