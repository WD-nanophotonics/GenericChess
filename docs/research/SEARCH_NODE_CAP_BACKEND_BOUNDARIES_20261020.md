# Search node-cap accounting at backend boundaries — 2026-10-20

## Question

Does one shared SearchLimits.max_nodes value imply the same work/completion
contract between AlphaBeta and Native on an unfamiliar rule?

## Bounded public probe

One seed-11 generated4x4 ongoing root used max_depth=3, qsearch depth0 and
the same numeric caps0/1/2/8/128. AlphaBeta disabled its optional root tactical
scan. The observed (nodes, qnodes, reason, completed_depth, fallback) values
were:

| Cap | Native | AlphaBeta |
| ---: | --- | --- |
| 0 | (1,0,node_limit,0,true) | (0,0,node_limit,0,legal root action) |
| 1 | (1,0,node_limit,0,true) | (1,0,node_limit,0,legal root action) |
| 2 | (2,0,node_limit,0,true) | (2,0,node_limit,0,legal root action) |
| 8 | (8,0,node_limit,0,true) | (8,0,node_limit,1,legal root action) |
| 128 | (128,0,node_limit,2,false) | (55,0,completed_depth,3,legal root action) |

Native counts its mandatory root before checking the cap, so max_nodes=0
still reports one root node and no child expansion. AlphaBeta can produce its
legal root-scan action with zero recursive nodes. Even when both report8
counted nodes, they retain different search depths.

## Decision and limits

Clarify the Native contract locally: one mandatory counted root is an explicit
zero-cap exception; additional Native visits obey positive caps. Keep runtime
semantics unchanged. The same input object and numeric cap do not equate
backend work, depth or fallback behavior; this agrees with
SEARCH_BACKEND_ATTRIBUTION.md. This single generated root is not a strength,
latency or general backend comparison and motivates no shared API redesign.
