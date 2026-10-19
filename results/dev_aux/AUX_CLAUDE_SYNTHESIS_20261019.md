# AUX_CLAUDE synthesis — DEV_AUX101–107 (2026-10-19)

Executor: Claude Code acting as AUX_CLAUDE in the DEV_AUX checkout (sidemission), at the user's direction, never at the same time as Codex DEV_AUX. Every number below is a finite paired W−L bound (UNKNOWN/missing = [−1, 1]) on a registered panel. None of them is a confidence interval or a population claim. Each segment was registered before fitness, fully audited (TD reverse-credit audit, unpruned witnesses, deployment audit), pushed with its SHA verified, and discussed with Dot in #generic-chess. Wording corrections from Dot are included.

## What was learned

| Seg | Question | Registered result | Key caveat |
|---|---|---|---|
| 101 | Chess: does SelfCandidate TD beat Fixednu at 2.5M/arm? | Pooled SC−Fx +.008 at 2.5M; the sign varies by foe, prefix and seed | An SC advantage was **not established on this panel**. SC has about 23% fewer TD terms per node. The strong form of "more traditional order ⇒ stronger" was refuted (3 of 20 order-up cells have lower W−L). |
| 102 | Generic 4×4 NEW rules 351001–4: does cold Fixed TD beat initial? | 100k [+.174, +.299]; OldRulesMean − initial [+.084, +.197] | **No gain was shown after 100k**, which is not the same as proven saturation. 16/32 EVAL roots were exposed in TRAIN; a post-hoc fresh-only check gave the same signs. |
| 103 | NEW rules 348001–4: does a warm start from OldRulesMean save dose? | **WARM_WORSE** (W100k − C100k [−.088, −.072]) | OldRulesMean − initial is strictly negative here ([−.033, −.014]), so the 102 transfer did not replicate. Directly paired W0 − C100 is 13/16 negative across both panels: the transfer line is **CLOSED**. Cold learning replicates (+.174 to +.189). |
| 104/105 | Widen ONE factor to 5×5 (types P/A/B, rule-derived channels) | **LEARNS_5x5** [+.041, +.123] after a registered completion of the 104 PARTIAL_CAP | This widens the generated domain, not board size alone. At equal nodes there are about 0.52× the TD terms of 4×4. U = 52 in total. The curve was still rising at 100k. |
| 106 | ONE pre-fixed movement change (allow_hybrid, 4×4, P/A/X), held-out roots | Pooled **LEARNS_HYBRID** [+.010, +.084]; **per rule 3 positive, 1 strictly negative** (363001 [−.328, −.156]) | The "3 positive" count merges foes (363003 against the uniform foe is −.0625). Pooled gains must not hide failing rules. |
| 106 diag | Why does 363001 fail? (existing 106 records only) | The terminal TD error is identically 0 (D2 sees the terminal). 363001 is heuristic-bootstrap dominated (ratio .78–1.41 vs .17–.46), with board X driven down on all seeds | Descriptive, from realized trajectories. Conflicts exist on every rule. |
| 108 | Second pre-fixed movement config (leap-only, 4×4) | Pooled **LEARNS_LEAP** [+.125, +.188]; per rule 3+/1− (364003 [−.086, −.039]) | Held-out rule failed for rule 364004 (TRAIN overflowed into EVAL families); post-hoc fresh-only check gives the same sign. Cross-panel, 20 NEW rules: **13 positive / 4 negative / 3 undetermined**. |
| 107 | Probe: λ 0.95 → 1.0 on 363001 only | **NO_FLIP** vs initial [−.164, −.070]; merged [+.055, +.195] better than λ .95 | Per seed: 1977 undetermined, 8173 +, 27182 strongly −, 31415 [−.125, 0]. 27182 is worse under λ = 1 than under .95. Compatible with the bootstrap/credit hypothesis, but the **mechanism is not isolated**. |

## Current best statement of the Generic learning claim

On the generated 4×4 and 5×5 panels tested so far (16 NEW rules), the same per-rule cold TD learner, run against fixed plain foes, improves pooled actual W−L over its random initial prices. Not every rule improves, though: one hybrid-movement rule (363001) clearly gets worse. In the analyzed 106 hybrid-panel records (only those), the terminal TD error was identically 0, and the outcome entered only through bootstrap steps whose target was a search that had already seen the terminal. On the failing rule there, heuristic-to-heuristic steps dominated. Reusing prices across rules (averaging over old rules) is not a reliable prior.

## Infrastructure added (reusable, small, diff-reviewable)

- `task2586/run.py`: a rule-file hook for the audited task2565 Generic code, which is otherwise unchanged.
- `task2587/{train,audit}.py`: copies of task2565 with exactly two edits each, for a plan-specified initial (warm start).
- `task2588/run.py`: rule-derived channels (as in task2525), set before importing the audited modules.
- Registered completion of missing EVAL slots (`task2589`) and held-out EVAL roots fixed before fitness (`task2590`).
- `task2590/credit_split.py`: an exact per-game reconciliation of TD credit into outcome-seen and heuristic bootstrap steps.

## Open questions for the next owner (Codex DEV_AUX or AUX_CLAUDE)

1. How common are per-rule failures? A second pre-fixed movement configuration would answer this; only do it if it changes a decision.
2. Does the outcome-poor bootstrap signal limit Generic learning in general? An outcome-weighted target variant would have to be registered as a different learner, not as the SAME-learner claim.
3. Codex's original NEXT_WORK Backup1 (full Generic transfer) is now partly covered by 102–106. Re-plan it from LOCAL_MAINLINE rather than resuming it verbatim.

## Dot review of this synthesis (107a reply, adopted) and round closure

- **Round closed** on Dot's recommendation (3): no new Generic learning experiments in this round. DEV_AUX108 (leap-only) had already run before that reply arrived; its result is kept, framed as counts only.
- **Rule sets:** the 16–20 NEW rules used here have been inspected repeatedly. They are now a **development/regression set**, not a fresh confirmation set.
- **Failure rate:** a per-rule failure *rate* needs a defined sampling population and distribution first. Neither 106 nor 108 estimates one.
- **Advice to the next executor:** before comparing a new (e.g. outcome-weighted) learner, state how it substantively differs from λ = 1, and what result would change the adoption decision.
- **Three things to keep separate:** (a) merged actual gains, (b) per-rule/seed/foe failures, (c) mechanism hypotheses.
