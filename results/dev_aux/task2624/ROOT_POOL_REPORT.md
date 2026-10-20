# Task2624 outcome-blind replacement root pool

This pool was prepared after task2623 exposed histories in its partial training
run. The selector read the prior evidence streams plus the complete task2622
and task2623 query/episode logs, and also scanned the earlier task2622 root
manifests, including its v2 pool. It used no outcomes, search values, or model
weights for selection.

The selected pool contains 120 training and 16 evaluation roots for each of
the same four development rules. Training selection rejected 986 exact prior
history matches after examining 1,856 rule/family pairs; evaluation rejected
132 after 249 pairs. Preparation took 41.468 seconds. Pool SHA256 is
`0cbc62f21395f98b60975ca17c7ba988066bb2c87c2003b28bba3c4a1bcb9a7e`.

Independent audit verified 43 prior-source hashes, replayed all 544 selected
full histories, checked active features and nonterminal status, and found zero
exact training/evaluation intersections in each rule. This is exact-history
separation from enumerated evidence; it does not establish descendant-state,
transposition, or distributional independence. The pool remains prepared but
unregistered, and no training or evaluation was run from it.
