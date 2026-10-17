# Direct user route reset

Incremental TD/search bootstrapping now trains material weights; actual terminal
W/L/D evaluates strength. Older finite-grid/proof work stays historical control.
The current candidate is episode-frozen TDLeaf(lambda=.95), standard Chess first,
with no human material ordering or solver prerequisite. Exact1997 reproduction,
stable heldout improvement and same-total-cost WDL-grid comparison remain OPEN.
See task2492/README.md, task2497 and the segment86 report. Source/result snapshots
retain all failures, UNKNOWN, original caps, and the actual terminal-trace repair.
