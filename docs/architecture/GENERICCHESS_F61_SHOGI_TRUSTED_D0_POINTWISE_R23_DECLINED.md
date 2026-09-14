# F61 Shogi trusted D0 pointwise R23 — compute declined

## Scope

R23 requested the exact F60 `D0_RANDOM_REACHABLE` protocol: 96 fresh roots,
source-group-disjoint 48/24/24 fit/development/final-holdout splits, one
frozen seed-59013 width-32 `POINTWISE_Q` fit, and a conditional fresh
role-swapped Standard-Shogi Arena pair at seed 620710. The implementation is
published at sandbox commit `8ab9a724e2370d6199a021dd55257e52a2929a41` in
`scripts/f61_trusted_d0_pointwise.py`.

## Approval boundary

The exact compute-plan request was
`GENERICCHESS-20260914-010356-78d60536`. Chat returned
`GENERICCHESS_COMPUTE_PLAN_APPROVAL=HOLD`.

- plan SHA256: `9fa394e6fa99ccedfc984a06642c71d56bed6d20eb2749b2cd092a7aa5246200`
- resource-envelope SHA256: `1fce80a9a5b2bd6e336cf3334ee707894ceac68b34061a9f62a071e361f52918`
- sandbox SHA: `8ab9a724e2370d6199a021dd55257e52a2929a41`

No Heavy command was launched and no candidate or Arena result is claimed.

## Supervisor resolution

The registered Supervisor signed `RESUME_WORKER` for this exact worker and
request, with the ruling **R23 HEAVY DECLINED**. The resolution cites the
four-hour/ten-CPU-hour estimate as insufficient marginal decision value after
R20's localized upstream generalization failure and R21/R22's rejected
root-disjoint `POINTWISE_Q` rescue routes. It directs the worker to report the
decline through this session and obtain a cheaper order that changes the
learning/generalization mechanism or selects one using existing evidence.

This report is a scientific stop at the compute-approval boundary, not a
Chat `BLOCKED` status and not promotion approval.
