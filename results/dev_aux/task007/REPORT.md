# Observable false repetition and private candidate

One declared Chess-derived supported ruleset, repetition_limit2, ordinary initial
GameSession with exact witnesses; source b4108a68a7ee06327be39cb3a222939644085a52.
One deliberately injected snapshot.updated MemoryError per original/candidate.

Original: failed b1c3 leaves a private count. Same-instance real b1c3 retry has
count2 and REPETITION, while public apply_action gives ONGOING. Boards and
two-record played histories are identical. Retry pop does not remove the stale
entry. Unfaulted original push/pop is ONGOING and restores the actual table.

Candidate: AST-only removal of bridge_key-is-not-None conjunct, retaining
child_occurrence_added and removed_history==0. The fault restores the actual
table; retry count1 is ONGOING and equals public authority; retry pop and the
unfaulted push/pop restore. Product source is untouched.

This finite counterexample violates the source's strict exception-safe undo
contract. CALLER_SCOPE.md traces MemoryError through the real player to the GUI
error boundary: inspected production caller creates a fresh runtime next time.
No normal timeout, live exhaustion frequency or actual user-game error follows.
Dot independently read pinned Runtime/search source and supported this split,
plus testing existing n>0 counts; Dot did not execute the candidate. Task008
provides that additional finite existing-count/bridge/nested collision evidence.

Initial CoreBoard fixture construction stopped before any fault push because
the imported static unit evaluator requires the original Western fingerprint.
development_failure.json preserves it. Ordinary GameSession supplies the same
declared rules and legal initial board without that unrelated evaluator gate.
No limits or result condition changed.

Reproduce: .venv/Scripts/python.exe results/dev_aux/task007/witness.py
Result: witness.json. No Native execution, timing comparison or deployment claim.
