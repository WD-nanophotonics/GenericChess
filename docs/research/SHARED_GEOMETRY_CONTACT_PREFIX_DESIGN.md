# Shared geometry, exact two-action contact prefix: prospective cost question

2026-10-05. The former naive Shogi first-pattern scan cost15368 candidates for
one owner, beyond5000. Changed premise: qualify simple board grammar by current
mode, canonicalize identical compiled geometric primitives, evaluate each
geometry/source ONCE, then combine one-blocker admissible sets algebraically.
This is a finite contact prefix, not a full graph or new game search. The cost
question is whether it supports Silver2 and a cheap rule-derived constructor
without exceeding the original128-pattern/5000-candidate/15sec source limits.

Accept only qualified target_empty/target_enemy leap/ray board patterns with
unit self move, target enemy removal (capture_to_hand/remove_from_game), no
other physical effects, guards, slot/zone conditions or postconditions, and
inherited promotion masks. Ray paths must be path_clear. own_anchor_safe is
the only explicitly omitted board invariant. Reject the whole requested profile
set on unsupported forms; no pattern/child is silently dropped. Drops and
official history/declarations are outside the existing virtual board task.
Preserve correct source base/current/promoted tags and promotion mask eligibility.

For fixed(s,d), eligible blocker squares lie among all squares except s,d.
A direct capture permits every blocker outside its interior path. A two-step
route first QUIETLY moves to u (u!=s,d), then captures d with its possible
promoted current mode. Reject a first path crossing d. Its forbidden blockers
are u plus both interior paths. The original source is vacant on step2, never
a permanent extra blocker. Alternative semantic descriptions and promotion
paths are a UNION of physical success: no duplicate contact rewards.
For each pair, direct eligible sets union; second eligible sets union; exact
distance2 excludes every direct-success blocker. Keep all remaining mass at
distance>=3/unknown, and separately retain existing reachability certificates.

Preprocessing reports raw per-pattern endpoint count versus canonical geometry
count, cached source tables, mode profiles and elapsed cost. Whole-law set/count
arithmetic is reported separately; it does not expand compiled event or engine
budgets. No virtual event materialization/PublicGame transition/goal query.
Do not hide arithmetic time behind preprocessing;15sec covers BOTH.

First native Standard Shogi set: P/L/N/S/G/B/R with correctly marked TP/TL/TN/
TS/TB/TR partners, owner0; reflect owner1 only after actual mask/geometry
equivariance controls. Freeze ALL counts, not favorable subsets. Compare P2
and Gold2 against independent earlier arithmetic; native Silver optional quiet
promotion is a NEW frontier. A later separately frozen Chess4-mode control may
compare native N/B/R/Q counts. Unsupported Chess EP/aux patterns remain unknown,
not erased. The interface is research-only and not a complete generic scalar
prior, goal-use test or Xiangqi holdout admission.
