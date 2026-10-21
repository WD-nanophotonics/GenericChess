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

Historical detailed reports and closed payloads are available in Git history at
`7fe1a9d6e3ab2772e520afc0784627ebd7e7d9c4` and earlier revisions.
Unique uncommitted retired work has a verified private recovery copy; see
`docs/operations/CLEANUP_20261021.md`. Earlier task2622 launch failure,
task2623 interruption, partial caps and failed studies remain historical
evidence. Cleanup does not make their inputs unexposed or reset their budgets.

## Code to reuse

- `results/dev_aux/task2492/learning.py`: fixed-coordinate Model and bounded
  AlphaBeta; `episode.py`: selected episode-frozen TDLeaf(.95).
- `results/dev_aux/task2621/fixed_scale.py`: dynamic board-current/hand-base
  channels, fixed coordinate 0 and scale 10, full GameSession authority.
- `results/dev_aux/task2625/train.py` and `evaluate.py`: completed finite
  experiment consumers; reference their behavior without rerunning old studies.
- `generic_chess/learning/tdleaf.py` is a different batch implementation.
  Do not silently substitute it for the validated episode learner.

## Next useful work

1. Move the selected fixed-scale learner/adapter out of numbered result folders
   into one opt-in reusable library path, preserving update and rule semantics.
   First inspect the existing learner regressions and dependencies; compare
   deterministic Chess/Generic updates, including censored terminal handling.
   Do not introduce another registration/auditor framework or product default.
2. Use that common path for one small, bounded Generic training/evaluation pilot
   whose result changes a stated choice. Include an actual semantic mechanism
   absent from the small movement panels; explicitly report unsupported scope.
   Save code revision, seed, configuration and compact outcome/cost summary.
   Put generated traces under ignored `artifacts/`; no duplicate audit JSONs.
3. Evaluate actual learned-vs-initial terminal play under the same resource
   conditions. A changed action, updated weight or zero initial material
   difference is not itself strength evidence. Preserve UNKNOWN and missing.

No new study is launched by this cleanup. Existing frozen experiments remain
frozen. Estimate total cost before a new run; expected >=120 minutes needs
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
Current cleanup communication is read-only. Preserve the uncertain Slack send;
do not resend. Administrative cleanup earns no research time. Resume the
existing session UUID and its confirmed 1505.826558 seconds after this bounded
cleanup; do not claim the unfinished research segment has completed.
