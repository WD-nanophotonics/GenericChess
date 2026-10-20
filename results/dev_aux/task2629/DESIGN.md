# Task2629 fresh-root H=256 evaluation

Task2628 completed its frozen H=128 panel with 17/256 UNKNOWN endpoints, all
caused by the horizon; none touched its registered per-root node cap, and each
had at least 17,486 nodes of cap headroom. Those results cannot be extended or
replayed in place. A post-hoc history diagnostic found at least one position
with a repetition count of three in all 17 histories; the final position's
count was 1 in 11 histories, 2 in 5 and 3 in 1. Rules15 declares a repetition
limit of four and uses the default draw policy. This motivates testing a
separately registered H=256 evaluation on fresh exact-record-disjoint roots:
continued cycles may reach actual rule terminals, but no outcome is presumed.

The candidate model was already trained and audited in task2628. This task
reuses the exact frozen initial and TDLeaf weights, makes no training updates,
selects 16 new outcome-blind eight-ply roots from family range [300000,350000),
and excludes exact complete records from the prior inventory, task2627 pool,
and all task2628 training/evaluation query and episode histories. The
independent root audit verified zero exact-history intersections, full
GameSession replay and a legal hand-R unlock at all 16 roots. This does not
establish descendant, transposition or distributional independence.

The frozen evaluation has 256 slots (4 model seeds x 16 roots x 2 colors x 2
endpoints), H=256, the same D2 search, same foe, and the same per-root 20k/40k
combined two-side node caps. It is a new registration, not a top-up, and its
results must be analyzed separately from task2628. Every horizon/resource or
non-scoring endpoint remains UNKNOWN. A deterministic assignment gives eight
roots each the 20k cap and eight the 40k cap.

Measured root preparation and audit were 39.34s and 37.65s. The evaluation
hard cap is 1,800s; the conservative all-in bound including preparation,
root/evaluation audits and a 1,200s reserve is 3,540s (59 minutes), below the
7,200s Chat-assessment threshold and the existing 6,600s project cap. Task2628
measured 243.78s at H=128; this is a reference, not an H=256 runtime guarantee.

The one-shot plan SHA-256 is
`f05e148bef90c76ed7246a7fcc283a565b4aafb1eaf8d09444d5e634eadc4fb1`.
See the root pool/audit and run receipts for source bindings. No rule, model,
task2628 cap or prior result is modified.
