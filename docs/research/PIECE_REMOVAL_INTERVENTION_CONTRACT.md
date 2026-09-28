# Piece-removal intervention contract: executable capture check

**Unknown.** Does a legal capture supply the same game-independent `R_t(s)` needed by the reachable-context interval diagnostic: make one focal resource unavailable while retaining a comparable full semantic context?

**Smallest observation.** Run the existing public-core and semantic-executor capture cases for Western Chess, Standard Shogi, and Xiangqi, then inspect only their postconditions. Command: `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp .local_agent/pytest-intervention tests/test_ruleset_capture_disposition.py -k capture_disposition_matches_public_core_and_semantic_executor`. Result on 2026-09-28: `3 passed`. The fixture states are hand-built legal-action contexts, not certified initial-state-reachable positions; this is a local transition-contract check, not a reachability census.

| RuleSet case | Victim after legal capture | Other mandatory state changes in the test |
| --- | --- | --- |
| Western Chess | Absent from board; hands unchanged | Attacker moves source to target; side to move flips; ply, repetition key, and history advance. |
| Standard Shogi | Promoted pawn `TP` leaves board; capturer gains unpromoted pawn `P` in hand | Same attacker, turn, ply, repetition, and history changes; the token remains available for a later drop. |
| Xiangqi diagnostic | Absent from board; hands unchanged | Same attacker, turn, ply, repetition, and history changes. |

The semantic executor and public transition agree in all three cases. This directly rejects **capture as a context-preserving, game-independent deletion operator**. In Shogi it is not even deletion of the resource from play. In Chess and Xiangqi a legal capture does discard the victim, but it also changes the attacker position, turn, and history. Holding those fields fixed while erasing the token would be a synthetic state edit, not this legal transition. Requiring that edited state itself be reachable from the standard initial setup is a further condition that the transition test does not establish.

Two plausible comparisons therefore describe different objects: `delete token from board and hands while freezing other fields` is an explicit intervention model, whereas `follow a legal capture` is a transition in which the opposing actor and time advance. Neither RuleSet semantics nor the adversarial interval construction identifies one of these as the unique marginal-value comparison. [FIDE's legal-position rule](https://handbook.fide.com/chapter/E012023) also makes initial-history reachability relevant; the [Japan Shogi Association rules](https://www.shogi.or.jp/match/taikyoku_rules/) include held pieces in the state relevant to repetition. These external rules support the scope distinction, not a general impossibility theorem.

**Decision.** Do not apply the previously defined `delta_t(s)=V(s)-V(R_t(s))` to real Chess or Shogi as if `R_t` were rule-given. Keep the finite interval counterexample as a conditional mathematical result. The tested observation does not rule out a declared synthetic intervention or a different scientifically justified valuation model.

**Next bounded question.** Can a comparison of *actual legal capture continuations* yield a useful context-specific ordinal loss-of-options certificate without inventing a removal state? Specify the same pre-action context and the response horizon, then check a single capture/recapture witness. Do not convert its existence or frequency into a static coefficient without an independent aggregation principle.
