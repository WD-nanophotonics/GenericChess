# DEV_AUX current research

## Decision — user direction, 2026-10-21

Return to the selected learning question: can the same fixed-scale vanilla
TDLeaf/search-bootstrap learner learn useful values on standard Chess and then
on generated Generic rules? Preserve complete executable rules and GameSession
history. Actual terminal W/L/D evaluates strength; search values train.
UNKNOWN remains unknown, including horizon/cancellation/missing results.

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

1. Use the completed pilot's logs to explain one of its 23 candidate-action
   divergences. All 18 double-terminal pairs tie; other pairs are censored or
   missing. Identify a specific mechanism worth testing, not another larger
   seed/rule matrix. Treat the diagnosis as post hoc and do not reuse these
   exposed roots as a future independent holdout.
2. If that mechanism changes a learning decision, design one bounded test with
   separate training and natural-distribution validation. Keep the same learner,
   full rule/history semantics, actual W/L/D and explicit UNKNOWN/missing.
   Otherwise investigate the existing non-scoring-declaration search limitation
   with one real rule control; do not build a solver or audit prerequisite.
3. Complete Generic coverage remains open. History-dependent outcomes and
   non-scoring terminals need explicit scope; type-count gradients or action
   changes do not prove knowledge transfer, useful prices or playing strength.

The cleanup is complete. The new bounded semantic pilot used the common code
and stopped at its original 1800-second deadline; no frozen task was revived.
See INCREMENTAL_TDLEAF.md for configuration, exact result and limits.
Existing frozen experiments remain frozen. Expected >=120 minutes needs
explicit Chat mailbox assessment. Do not split runs to evade that threshold.

## Slack advice and ownership

Claude comment TS `1792546475.322549` was read live in #generic-chess;
current saved revision SHA-256 is
`f8a33829444b5b2ed55816fdc592163de49fe41f9036c733540b9b7702bf9866`.
Adopt the criticism of audit proliferation and stop its underlying work,
including the unregistered panel framework. Defer MCTS, Fairy-Stockfish/Elo,
SPRT and feature redesign: these suggestions do not supersede the user's
TD/search-bootstrap route. Reject replacing UNKNOWN with adjudicated draws
or numeric outcomes absent actual rule authority. Initial material features
being zero on symmetric starts does not establish that the features never
activate or that the rules are indistinguishable during play.

DEV_AUX owns only this checkout / sidemission. PRIMARY owns sandbox integration;
DEEPSEEK remains independent. No new workers or cross-role state changes.
The hourly research continuation resumed the existing session and confirmed
work; cleanup itself earned no research credit. New Chat theory comments at
TS1792556353.483249 and1792556421.498529 were read: adopt the distinction between
algorithm reuse and knowledge transfer, risk-proportional validation, and
mechanism-first choices. Defer their larger theory/solver experiments as future
questions. Normal periodic Chat protocol applies; the existing SEND_UNCERTAIN
report could not be confirmed by the complete read and was not resent.
