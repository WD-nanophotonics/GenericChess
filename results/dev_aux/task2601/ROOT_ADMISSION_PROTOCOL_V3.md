# Prospective root-admission protocol v3 — fixed decision-history panel

**Status:** method proposal; no task/seed is registered and no fitness starts here. It incorporates an evidence-based Dot suggestion from root 1792429300.156229. Dot advice is advisory; the adoption decision and scope below are DEV_AUX's.

## Primary estimand

The primary comparison is the equal-weight finite panel produced by a fixed, preregistered algorithm: the first N proposed complete histories that are (a) legal after the specified prefix, (b) nonterminal, (c) not identical to any root in the complete frozen TRAIN-root manifest, and (d) not already selected for EVAL.

This estimates performance on that algorithm-selected panel only. It is **not** a uniform sample over all legal nonterminal histories, not simply the source-family distribution conditioned on nonterminal/disjointness, and not overall population playing strength. The proposal stream, acceptance order, uniqueness rule and stopping rule jointly define the panel and its implicit weights. Give accepted panel rows equal weight for its declared finite-panel estimand; log proposal multiplicities and all rejections for audit, not as a posthoc alternate weighting choice.

The unconditional family stream remains a descriptive coverage/terminal-mass diagnostic. Do not launch a second fitness arm merely to compare estimands. A later question about source-distribution-average strength would require a separately designed weighted estimator, with overlap/leakage handled in advance.

## Freeze before rule exposure or fitness

1. Fix the rule/configuration, full candidate streams and caps, PRNG/domain separation, prefix length, target N, role/foe/order/cost conditions, canonicalizer, replay implementation/hash, terminal/legal predicates, rejection priority, and shortage behavior.
2. Materialize the complete TRAIN-root candidate manifest for **every method and seed across the entire declared budget**, including roots that later updates/episodes could consume. Runtime training must only consume this frozen manifest; it cannot generate beyond it. A nominal family range or expected episode count is not a completeness proof.
3. Build an identity key from the complete ruleset fingerprint plus normalized true game history. Preserve every field that can affect legality, terminality or history-sensitive behavior: auxiliary state, hands/drops, current/base piece types, ordered actions, repetition state and relevant ply/history. Exclude log IDs, row numbers and other nonsemantic metadata.
4. Replay candidates through the pinned rules/runtime and verify history legality and nonterminal status; do not trust saved booleans alone.
5. Use a separately domain-separated, bounded EVAL proposal stream. For each candidate retain overlapping rejection flags, plus one fixed-priority mutually exclusive rejection reason. Accept only when every admission condition passes and the canonical history is not in the EVAL seen-set. Freeze and hash the full accepted EVAL manifest before fitness, including its proposal index and multiplicity.
6. If the candidate cap cannot produce N accepted histories, retain the admission shortfall. Do not widen the stream, replace a seed, or inspect outcomes then fill the panel.

## Evaluation and claim boundary

Run each baseline/candidate on exactly the same accepted roots, sides, foes, seeds/order and per-slot budget. UNKNOWN/missing remains censored and receives only the preregistered conservative WDL-bound treatment; it is never imputed as a draw. Report terminal/duplicate/overlap/rejection mass and actual wall/node cost.

The guarantee is root-history separation only. Roots can share prefixes, equivalent boards with different histories, or occur as intermediate states along TRAIN trajectories. Do not call EVAL “never-seen states” unless that stronger exposure claim is separately audited. Root/history clusters, not role/foe slots, are the independent root units for uncertainty.

## Carry-forward failures

Task2595 remains closed as SEED_ADMISSION_FAILED; its generated rule/root set and absent fitness are immutable. Its train-only concentration follow-up motivates reporting duplicate weights but does not create a retroactive gate or authorize new roots. Task2592's 364004 overlap and 256-slot aggregate stay as previously reported.
