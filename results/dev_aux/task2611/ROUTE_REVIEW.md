# task2611 route review — defer before registration

Status: design only. No task2611 registration, training, evaluation, or cap change.

## Evidence

- task2611 estimates a fresh-seed/fresh-root replication of task2606's TD-leaf comparison at 4,171.844 s (69.531 min), with unchanged 5,400 s training and 1,200 s evaluation caps. Root/seed/init artifacts are complete, source-bound, and preserve the 120 min assessment threshold.
- The source contract is narrower than the user's method reset: task2606 consumes complete root `Receipt.value` via TDLeafEpisode. It does not consume internal `Sample(lower, upper)` nodes for TreeStrap. Resource-cut results stay censored, so bounds are not mislabeled; they are simply unused.
- task2492 has a Chess TreeStrap smoke path (2 seeds, 3 methods, 120k nodes/arm, 85.01 s total), but its own claim says learning-signal feasibility only, with no held-out W/L strength comparison. Its focused one-sided-bound tests pass 13/13.
  Within paired seed arms at similar node counts, TreeStrap recorded 44,457 internal-bound samples versus 1,881 TD update samples total; runtimes were 14.51/14.16 s versus 14.23/13.86 s. This is denser signal at similar tiny-run cost, not equivalent targets or evidence of convergence/strength.
- task2594 provides a standard-Chess actual-W/L finite comparison for a TD-leaf variant, not TreeStrap. It is not a TreeStrap strength result.

## Decision

Defer task2611 before registration. Its possible result would clarify fresh-seed/root sensitivity of an already tested Generic TD-leaf contrast, but would not test the explicitly prioritized search-tree/bound-aware learning method. The more decision-changing next study is a standard-Chess actual-outcome comparison of TreeStrap and TD-leaf under paired initializations and equal total search-node cost, with fixed evaluation roots/foe/conditions and a predeclared finite-WDL control if affordable. Preserve task2611 unchanged as a feasible optional follow-up; reconsider it only if method comparison leaves seed/root sensitivity as the decision bottleneck.

No parameter/seed/root is selected from outcomes. No Chess human-price labels or human holdout were read. This route choice is based on the direct 2026-10-17 user decision, not CHAT_Comments. No training or evaluation was run in this review; science remains OPEN.
