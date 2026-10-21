# DEV_AUX current research

## Decision — user direction, 2026-10-21

Return to the selected learning question: can the same fixed-scale vanilla
TDLeaf/search-bootstrap learner learn useful values on standard Chess and then
on generated Generic rules? Preserve complete executable rules and GameSession
history. Actual terminal W/L/D evaluates strength; search values train.
UNKNOWN remains unknown, including horizon/cancellation/missing results.

User correction later on2026-10-21: use the latest committed sandbox
infrastructure as this branch's baseline; retain only DEV_AUX learner/research
differences, not parallel Core/search implementations. Current import is
`6a4f8868d767b41ffc07ff5ddbb7bce448417aaa`: all published generic_chess
source plus product/development/specification tests and their dependencies.
Own incremental learner, historical references and role-local state are retained.
Uncommitted PRIMARY work, its results/producers and operational state are not
imported. Each hourly recovery checks for newer committed infrastructure.
The learner's hypothetical searches now use that shared SearchPathRuntime;
played moves/records still go through GameSession. Public-session search remains
an explicit reference control, not a second rule implementation.

Stop task2636 audit/receipt expansion. Its unregistered 16-rule panel is retired
from the active backlog. Frozen plans and root pool remain unchanged for context;
they are not a runnable or approved experiment. There is no registration,
run-v1, training result or evaluation result. Do not reconstruct the audit chain
or extend its old caps to justify sunk engineering cost.

## What the saved evidence supports

| Evidence | Useful result | Limit |
|---|---|---|
| task2594, standard Chess | Vanilla TD(.95) minus initial: +100 reward sum over 256 matched pairs, mean +0.390625. | Four seeds use different root blocks; finite evidence, not independent replication or population strength. OutcomeGatedTDLeaf is a separate optional variant. |
| task2620, frozen Chess learner comparison | All 1536 slots completed: 1267 actual terminals, 269 UNKNOWN, no missing. TDLeaf-minus-initial bound [29/384,111/128]. | Other five contrasts span zero; no learner-method winner or causal budget comparison. |
| task2625, fixed-scale Generic TDLeaf | Four generated movement rules; 1024 evaluation slots, 980 actual terminal, 44 UNKNOWN. Saved finite TDLeaf-minus-initial bound [0.1191,0.2910]. | One rule slice unresolved; small rules only, no full-domain or population claim. |
| tasks2628/2629, semantic-action controls | Saved bounds [-0.15625,0.109375] and [-0.05469,0.02344]. | Both cross zero; no basis for extending the same panel merely to obtain significance. |
| task2636, unregistered design | Sixteen 8x8 movement/drop candidates and prefix-disjoint frozen root pool. | No learning/strength result; lacks complete Generic semantics. Retired before launch. |
| Reusable semantic pilot, 2026-10-21 | 119 training episodes, 106 updates; 95/128 evaluation slots, 52 actual terminals, 43 UNKNOWN and 33 missing. Full paired completion bound [-83/64,69/64]. | One exposed stress rule; no identified gain or independent rule/position holdout. No weight adoption or cap extension. |
| Prospective no-progress variant | 48 training episodes/48 updates; 46/128 evaluation slots,30 actual terminals,16 UNKNOWN,82 missing; bound[-3/2,25/16]. | Changed game/seed/budget, not a causal comparison. Full-history replay costs limit throughput; no weight adoption. |
| One natural8x8 sample | Default generator seed2026102101; initial D2 completes311nodes. One episode makes16 legal plies/one TD update, then a query time limit; UNKNOWN retained. | No strength/holdout claim; initial-root feasibility did not ensure later-query completion. |
| Last-completed-depth control | Fresh57-ply episode uses55 completeD2 and2 D1 fallback targets; independent TD delta/replay checks pass. Fixed-foe32-slot comparison: iterative13W2L1UNKNOWN versus fixedD1 6W6L4UNKNOWN; full bound[3/8,1]. | Eight exposed opening families; different realized work under equal allowances. Search-policy result, not a learning gain or population claim. |
| Natural8x8 TDLeaf | 70 training/65 nonzero updates; all64 eval slots,62 actual mates/2UNKNOWN/0missing. Trained29W1L2UNKNOWN versus initial28W4L; full bound[1/16,3/16].134 histories and all updates checked. | One exposed rule,16 opening families, fixed uniform D1 foe. Finite gain, no population/absolute-strength or universal-price claim; no default adoption. |

Historical detailed reports and closed payloads are available in Git history at
`7fe1a9d6e3ab2772e520afc0784627ebd7e7d9c4` and earlier revisions.
Unique uncommitted retired work has a verified private recovery copy; see
`docs/operations/CLEANUP_20261021.md`. Earlier task2622 launch failure,
task2623 interruption, partial caps and failed studies remain historical
evidence. Cleanup does not make their inputs unexposed or reset their budgets.

## Code to reuse

- `generic_chess/learning/incremental.py`: the selected fixed-coordinate Model,
  material-blind bounded AlphaBeta, frozen-episode TDLeaf(.95), full GameSession
  adapter and shared bounded training/evaluation play path. No imports from
  numbered experiments or proof scripts; no product default change.
- `scripts/incremental_learning.py`: one exploratory single-rule entry; keep
  traces under ignored artifacts/. Revision, seed, rule input and configuration
  replace the retired per-experiment audit framework.
- Older task2492/task2621/task2625 code remains a frozen reference/control;
  existing experiments are not rerun or rewired to new source.
- `generic_chess/learning/tdleaf.py` is a different batch implementation.
  Do not silently substitute it for the validated episode learner.

## Next useful work

1. The common opt-in D1→D2 path now has finite actual-learning evidence above.
   Original run ended PLANNED_EPISODES_COMPLETE in3569.874s, with1800.061s
   measured training phase; its intended1800s guard's small overrun is retained.
   All caps/results are closed. The next label-blind default rule, generator
   seed2026102102, is accepted on existing-filter attempt3 with56 opening moves;
   one uniform D1→D2 query completes443nodes/.527s. Its fresh episode with
   seed27187/random initialization completes11plies to actual mate,6686nodes,
   10.776s and one nonzero TD update. No first-rule weights were transferred.
   This establishes episode feasibility, not a learning gain or rule-population
   result. Next test the existing first-rule frozen trained and initial models
   directly under the same iterativeD2 path, then small fixedD3-foe calibration.
   D3 is not presumed to produce50percent wins. No new matrix/audit gate,
   training extension, default weight adoption or old cap reset.
2. The no-progress variant gives genuine rule draws but not identified learning
   gain. A same6-node D1 control requires5 versus170 underlying transitions
   because the reference replays history. Keep this cost explicit; do not bypass
   correctness or assume higher terminal coverage makes a useful training game.
3. A stronger fixed D2 foe would test a different strength/calibration question;
   defer it behind the next single-rule episode rather than adding Elo/MCTS.
   Prior diagnosis remains useful: the exposed capture preference changes at
   board-TP + hand-R = 0; about72% of the old TP fall comes from terminal-PV TD
   targets. D8 exhausted800k nodes without a result. No deeper retry, clamping
   negative prices, missing-terminal explanation or old-panel extension follows.
   Current play executes an already authoritative WIN declaration before search;
   neutral options without such a win remain UNKNOWN. General coverage is open.

The cleanup is complete. The first semantic pilot ended when its original
1800-second guard triggered (1800.026s measured); no frozen task was revived.
See INCREMENTAL_TDLEAF.md for configuration, exact result and limits.
Existing frozen experiments remain frozen. Expected >=120 minutes needs
explicit Chat mailbox assessment. Do not split runs to evade that threshold.

## Slack advice and ownership

Claude comments TS `1792546475.322549` and `1792558608.371949` were read live
in #generic-chess; exact originals and revision decisions stay private.
Adopt the criticism of audit proliferation and stop its underlying work,
including the unregistered panel framework. Defer MCTS, Fairy-Stockfish/Elo,
SPRT and feature redesign: these suggestions do not supersede the user's
TD/search-bootstrap route. Reject replacing UNKNOWN with adjudicated draws
or numeric outcomes absent actual rule authority. The later comment clarifies
that prospective rules may explicitly define repetition/no-progress draws;
adopt that distinction without modifying frozen games. Initial material features
being zero on symmetric starts does not establish that the features never
activate or that the rules are indistinguishable during play.
The existing Gumbel code was checked locally, without starting an MCTS study:
`policy=None, checkpoint=None` has uniform priors and zero nonterminal values.
A real continuous-check-loss history reaches winner1 in both Core and Native,
but its current Gumbel terminal mapping returns0 for that non-checkmate win.
Thus the proposed baseline needs semantic repair before use on that domain;
no Gumbel code/default, other checkout or benchmark scope was changed.

DEV_AUX owns only this checkout / sidemission. PRIMARY owns sandbox integration;
DEEPSEEK remains independent. No new workers or cross-role state changes.
The previous continuation preserved its existing session and confirmed work;
this segment started anew only after that segment ended. Cleanup and publication
earn no research credit. New Chat theory comments at
TS1792556353.483249 and1792556421.498529 were read: adopt the distinction between
algorithm reuse and knowledge transfer, risk-proportional validation, and
mechanism-first choices. Defer their larger theory/solver experiments as future
questions. Normal periodic Chat protocol applies; the existing SEND_UNCERTAIN
report could not be confirmed by the complete read and was not resent.
The intended900-second training-phase limit had a stale pre-opening time window;
strict old phase compliance is unmeasured. The runner now guards that deadline
and grants only post-opening remaining time. The measured1800.026-second total,
all old results, budgets and missing slots remain unchanged.
