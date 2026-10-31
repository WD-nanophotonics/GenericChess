# Reuse of conditional response ordering — 2026-10-31

The generic mainline already has an opt-in conditional response hint. Reuse that
component if it is selected for a future single-policy test; do not implement a
second orderer or call this a port of Stockfish continuation history. Current
saved calls and the maintained learner did not enable it. This is source
capability/use analysis, not a new Player test or measured quality/speed gain.

Latest GitHub Pro7a812fd1acce803187ecdf3306199f67071a419b,
path20261031175948_JST_480b01b7.md,blobaa482c238f1edd4dccea66d18fdaa56b805972f9,
was privately saved/read in full. Adopt stopping cache/identity/observer expansion
and duplicate checks. It acknowledges the new local threat without strict
selected-quality evidence. This separate fallback follows the user's standing
instruction to perform useful scoped work; Pro did not dispatch an AUX algorithm.
PRIMARY keeps its new proof/continuation implementation and physical-call budget.

## What the mature reference actually supplies

The Pro-linked official Stockfish master was resolved to
ff7cee4244ec96ea488c402669e3674c0574dce6. Sources were read at that fixed revision:

- [search.cpp](https://github.com/official-stockfish/Stockfish/blob/ff7cee4244ec96ea488c402669e3674c0574dce6/src/search.cpp)
  conditions continuation feedback on earlier search plies and move context,
  rewards selected moves and penalizes other searched moves. Its worker history
  lifetime differs from one query-local scratch table.
- [history.h](https://github.com/official-stockfish/Stockfish/blob/ff7cee4244ec96ea488c402669e3674c0574dce6/src/history.h)
  supplies piece/target history tensors and bounded signed updates.
- [movepick.cpp](https://github.com/official-stockfish/Stockfish/blob/ff7cee4244ec96ea488c402669e3674c0574dce6/src/movepick.cpp)
  combines history with other terms, including Chess material/threat/SEE-specific
  information. This is not a price-free standalone conditional hint.

No upstream source was executed or copied into the project. Its constants,
dimensions, feedback weights and playing strength are not Leaper forecasts.
Do not import the Chess price/threat terms into the material learner's ordering.
[Source hashes and precise coverage](data/aux_continuation_reuse_20261031/source-assessment.json)
retain this distinction; the source files themselves remain private.

## Existing generic producer and consumer

SearchTuning.use_countermove already exists and defaultsFalse. The existing
semantic_probe_cost --countermove option forwards it; that historical cost
campaign is not reopened. Main negamax calls record_countermove(previous,action)
after a completed beta cutoff, when ordering is enabled and a previous
search-path action exists.

MoveOrderer and StagedMovePicker consult that hint while reordering the actual
legal action list. They do not insert a stored response into the legal frontier.
TT, captures and promotion precedence can shadow it. A stale or inapplicable
response does not become a new executable action. This is existing behavior,
not a request for another legality/identity guard.

It is a sparse single previous-fullAction response table, not the upstream
multi-ply history tensor or an experiential material-value model. A local
beta-cut event is a feedback event under its actual window/search evaluator,
not a certificate of full-history WIN.

## Actual lifetime is important

run_root_search creates one fresh Context and MoveOrderer per public choose
call. That table is shared across that call's iterative depths. It is not held
in the persistent Player object across choose calls, even when the TT persists.
Root negamax starts with previous actionNone; it does not seed the response
context from the last action in the played GameRecord. The relevant previous
action is normally a hypothetical search-path edge.

The maintained learning.mainline_search adapter creates a fresh Player and
SearchTuning with root tacticalFalse/fullPVTrue, without countermove. It does not
currently expose that flag through its search signature. Thus engine capability
YES does not mean learner adoption or learner acceleration. A future selected
learner comparison would need to forward the EXISTING option deliberately; no
adapter argument or default is changed here.

## When direct opportunity can first arise

Under an ordinary fresh, full-window iterative main search, with no extra
main-depth/research policy, no countermove-consuming Q path and distinct root
actions, and without same-depth retries, stopping all attempted main work
atD2 leaves no direct countermove
priority to consume. AtD1the root's previous key isNone. AtD2each child has a
different root-action key; a response learned for an earlier child is not yet
revisited at that key. Later iteration/work can reuse learned contexts.

SearchTuning defaults PVS and aspiration toFalse; the argument is deliberately
restricted to the ordinary unretried path, not a theorem about every enabled
PVS/aspiration combination.

This is a qualified source argument, not a universal timing/output-equivalence
claim. Extra bookkeeping can still cost time. Potential later opportunities
need not produce hits: the same response may already be the TT move, or be
illegal/not in the eligible quiet stage.

In particular a return with completed_depth2 can include an abortedD3or deeper
attempt and its feedback. A retained completed_root_win can come from such
work without completing a deeper uniform iteration. Therefore neither the
last completed depth nor a nonzero hit count alone identifies a final-choice
quality effect. Do not invent an activity gate from nominal depth labels.

## What the saved data can and cannot say

All223original kernel/signature returns have countermove_hits0:
96observer,64cold and63persistent returns. Zero alone would not establish
that a feature was disabled or ineffective. The frozen constructors also show
only localhash tuning, leaving countermove at its defaultFalse; this supplies
the disabled conclusion. No ON comparison or effect measurement exists here.

The hit counter records eligible quiet priority, not necessarily changed rank.
Existing product source tests explicitly distinguish TT precedence and the
actual legal-list invariant. Those test sources were read, not rerun or counted
as new passing Player experiments. No source question here justifies replaying
the old223calls, generating another family panel or increasing PRIMARY's budget.

## Decision

Conditional response feedback is already available as a small source-level
baseline component. A full continuation-history port would be another
implementation and intervention, so it is not adopted. If this one existing
mechanism is later chosen, use one declared flag and actual completed/partial
work under the same full service; do not silently add it to the current PN arm.
Costs and action quality would still need actual evidence.

No new Player, PN, Core expansion, game, training, build, rule generator, wrapper,
guard, timer or worker was created by this assessment. Source feasibility is
closed at this checkpoint. The next step is scientific review of this round's
new evidence or a genuinely new published mechanism packet, not more source
variants or an unbounded conditional-history project.
