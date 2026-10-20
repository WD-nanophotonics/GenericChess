# Task2635 censoring advice relevance to task2636

Chat's optional rule271003 censoring suggestion has already been completed in
the local frozen-log analysis at
`results/dev_aux/task2625/CHAT_CENSORING_PROFILE_20261021.md`. The 1,024-slot
task2625 evaluation has 44 UNKNOWN endpoints; all are H=128 horizon endings,
with 39 on rule271003 and no node-cap censoring. Rule271003's finite paired
reward-difference bounds remain `[-44,34]` over 128 strata, so the sign is
unresolved. Task2629's H=256 result has a different root pool; it cannot
estimate a causal horizon effect and must not be pooled with task2625.

This advice does not change task2636's frozen one-init design. Its 16 generated
rules and prefix-disjoint roots differ from task2625, so the old censor rate
does not predict their UNKNOWN rate. Keep H=128 and the current resource
caps, report completed W/L/D, completed UNKNOWN and missing slots separately,
retain all512 predeclared pairs in any completion bounds, and stop at the
registered cap without outcome-driven horizon extension or resampling. If the
finite bounds cross zero, report the result as unresolved. No new game,
search, label read, or profile rerun was needed.
