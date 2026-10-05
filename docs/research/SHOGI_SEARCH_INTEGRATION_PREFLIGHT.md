# Actual search integration preflight

Question: does production search with qualified physical inventory evaluation
reproduce the finite depth2 reference? This is numerical integration evidence,
not new outcome labels or strength. No search/transition/query performed here.

Inspected AlphaBetaPlayer accepts evaluator_override, TT/ordering controls and
SearchTuning; profile construction still happens with override. Disable disk
cache/native provider/build jobs in a future audit. Direct run_root_search
accepts an evaluator if no player/profile claim is needed.

negamax depth<=0 explicitly bypasses quiescence when qdepth_limit=0. Therefore
SearchLimits(quiescence_max_depth=0) gives static leaves, even when checked;
positive qdepth extends checked leaves and is NOT the saved static contract.
reference_minimax is terminal/declaration first, sorts successors and uses
side-to-move negation. These semantics must not be mocked away.

First audit: no TT, ordering, PVS, aspiration, staged picker, mate-distance
pruning, root tactical fallback or lazy successors. Require completed_depth2,
no budget/fallback termination, qnodes0, exact score and chosen action inside
the independently saved complete tie set. Equal-tie ordering need not match.
Evaluator signs inventory for current side and preserves base/current/held
transfer. Freeze rational-to-integer scale before execution; reject magnitude
near MATE_THRESHOLD. Declare any fixed hand parameters beforehand; a few
parameter points test integration, not all-parameter dominance.

Before execution freeze separate cost protocol/evaluator. The old48-event
study is closed: saved tree can supply a reference, but regenerated transitions
must be charged to the NEW integration question, never described as new
independent utility evidence or a reset goal budget. If full production use
cannot fit its declared cap, retain failure and qualify a saved-tree consumer.
Ordering-only follow-up can keep evaluator and tie set fixed while comparing
node counts under another prospective contract. Neither proves WDL calibration.
