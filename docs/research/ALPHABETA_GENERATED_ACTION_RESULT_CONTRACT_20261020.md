# AlphaBeta generated-action result contract — 2026-10-20

## Question

Does the public AlphaBeta caller preserve a generated semantic capture-to-hand
action's identity, captured piece/owner effect, PV, and commit/replay behavior
before a later semantic drop? Does the optional Native semantic-legality route
actually run on this path and agree with Core-only legality?

## Bounded fixture and method

`tests/product/test_f24c_mixed_mechanic_certification.py::test_public_search_preserves_promotion_capture_to_hand_then_drop` uses one
generated mixed-mechanic ruleset. AlphaBeta selects the opaque A0→A1 semantic
promotion; the Black B0 capture is now also selected by a one-ply AlphaBeta
call rather than being inserted directly by the fixture. A fixed evaluator
prefers A0 in Black's hand. The test compares Native-legality and Core-only
decisions on action, score, completed depth, PV and node count, and verifies
that search does not mutate the session. It then applies/submits the selected
capture, advances C0, selects the semantic A0 drop, serializes and replays the
full record.

## Result

The selected capture is `sem_03_capture_B0_A0_leap`, with actor B0, at the
promotion's target square. The PV begins with that exact action, and the child
puts one A0 into Black's hand. Native and Core-only search results agree on
the checked tuple for both the capture and later drop. The Native decision
reports actual legality calls with zero fallback and zero operational failure;
the Core-only decision reports zero Native calls. Full serialized replay
matches the submitted final state and result. The focused test and the five
relevant F24C/AlphaBeta/promotion/drop/many-promotion modules pass.

This closes one generated mixed-mechanic result/transition path. It does not
establish all semantic action families, Native search-backend equivalence,
utility, or a product runtime change. No production code changed.

## Related bounded audits

The public `PlayerDecision` has a single selected action and scalar score, not
per-root-action scores; `run_root_search` returns one action/score/PV/reason
tuple. Therefore the saved promotion/king qfrontier same-score/different-action
diagnostic cannot be resolved through an existing public per-action score
field. No diagnostics API was added. The saved-data checker for the existing
candidate96 static_v2 panel reproduces 22 changed and 34 unchanged first
actions among 56 same-state shared-action pairs, plus eight pairs terminal in
both arms and two UNKNOWN outcomes. That post-hoc association is not a causal
price effect and does not justify another panel.

Public history/terminal tests also already cover root history-dependent
continuous-check wins, terminal result provenance, complete-history runtime
parity and TT history separation. The relevant existing modules pass; no
duplicate terminal/history regression was needed.
