# Candidate16 TDLeaf panel: cost and scope gate

## Candidate scope considered

This is a pre-registration estimate only; no learner panel was launched. A
direct comparison over all16 task2633 generated rules would retain task2625's
per-rule conditions: four initializations, 250,000 candidate-plus-foe training
nodes per rule/seed arm, 120 audited training roots per rule, then four seeds ×
16 exact-disjoint evaluation roots × two learner colors × two endpoints at
H=128/D=2. That is64 training arms, a16,000,000-node training cap/target, and
4,096 evaluation slots. Every terminal W/L/D would remain an evaluation label;
UNKNOWN and missing slots would remain unknown/missing.

## Cost evidence

Task2625's source-bound all-in estimate was4,001.99s (66.70min) for four rules,
including a 50%-margin training projection, a conservative1536-slot evaluation
projection, and a1200s preparation/audit reserve. Fourfold linear scaling to
16 rules is16,007.95s (266.80min, about4h27m). This is a planning estimate, not
a runtime guarantee; movement rules can change branching and history
preparation costs.

The completed task2625 training and evaluation actually took1,750.237s and
555.656s for four rules, respectively. Fourfold scaling of those two compute
components alone is9,223.57s (153.73min), before preparing/auditing the new
histories, registration, analysis or publication. Even this measured-compute
floor exceeds the120-minute Chat-assessment threshold.

Sources: task2625 plan SHA-256
`9cca31fae284f8f88120a58c8128294455346f1a1bc4c813a30c12cf111e0b3f`;
training receipt SHA-256
`760bb829c2f0424b6e780f1541a6fe70fe7b824c998b0671e5c9794108b84304`;
evaluation receipt SHA-256
`e4ac648f12a4609d19e6176cb1a0c7406c24b6ed0e34f7f51f28f332481dd1f9`.

## Decision

The four-seed/16-rule study is not registered; its projected duration exceeds
120min and requires Chat's explicit necessity/scope assessment first. A
separate, smaller feasibility design can cover all16 candidates with one shared
initialization seed: 16 arms ×250,000 nodes =4,000,000 training nodes, plus
16 rules ×1 seed ×16 evaluation roots ×2 learner colors ×2 endpoints =1,024
evaluation slots. This keeps the same aggregate node/slot workload as task2625
and has the same source-bound66.70min estimate, but trades away seed replication.
It would be reported strictly as a finite one-initialization feasibility panel,
with no seed-stability, population, or full-domain claim. Use a hard all-in cap
below120min and preserve actual W/L/D versus UNKNOWN/missing distinctions.
Per rule it would have16 evaluation roots rather than task2625's64 roots per
rule across four seeds; the aggregate 1,024 slots stay fixed by spreading them
over16 rules. Per-rule finite-panel resolution is therefore four times lower.
The matched-contrast count remains512 overall (32 per rule rather than128 per
rule); a source-bound arithmetic check confirmed the10-channel adapter order,
4M-node training budget,1,024 slots and512 total pairs. One fixed initialization
seed (for example the already used1977) would produce the same initial weight
vector for every rule because their channels are identical; each rule's TDLeaf
updates remain independent.

This lower-cost all16 option does not split the four-seed study to evade review;
it is a different, explicitly narrower feasibility question. Either route
requires newly prepared, full-history exact-disjoint roots. The task2633/2635
histories are exposed and excluded from evaluation pools. No seed or rule is
selected using WDL or feature outcomes. The one-seed option is only proposed;
there is no registration or run yet.
