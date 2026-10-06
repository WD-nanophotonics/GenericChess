# Horse target-fixed graph and independent second-distance mass

Frozen before new graphs/motif observations,2026-10-06. Changed premise:
target0/13/40/60 qualification is not a theorem for target-independent Horse
reverse BFS. The stationary target blocks a leg even before capture. No full
Horse census, completed target query or original compiled family is rerun.

For fixed target t and blocker b construct a directed graph: quiet edge s->u
requires on-board Horse offset, u not in{t,b}, leg not in{t,b}; capturing edge
s->t requires Horse offset with leg !=b. Reverse BFS from t over these edges
computes distances for ALL permitted sources for that SAME(t,b), never another
target. Old initial source becomes empty after departure; no source-hole edge
mask is retained. Passivity and no royal/history scope stay explicit.

Changed counterexample fixed BEFORE execution:9x10 s=0(a1),t=9(a2),b=1(b1).
Both outward Horse legs are occupied, so source has no first move. A target-free
leg mask can incorrectly admit a route. Also test its file reflection and
target/blocker transposition, preserving the distinct target capture role.
For independent graph qualification use ONLY3x3 and4x2 complete populations,
840 ordered source/target/blocker worlds, not9x10 whole census. Compare to a
separately written forward coordinate BFS; at most5000 forward popped nodes,
one fixed-target reverse expansion <=90 vertices in9x10 counterexample,
15sec total. Preserve failures; no increased allowance.

Separate analytic full-board tau2 mass: enumerate on-board Horse-edge pairs
s->u->t (<=508*8=4064 motifs). Require s!=t and passive target leg validity.
For each(s,t), a path fails only when b is in its forbidden set
{u,leg(s,u),leg(u,t)} minus{s,t}. At least one path works iff b is OUTSIDE
the intersection of ALL those sets. Count88 minus intersection size.
Two Horse edges preserve checkerboard parity; a direct edge changes it,
therefore these pairs cannot already have tau1. This gives exact tau2,
not a distance census or histogram beyond2. Compile/event/source-query0.
Direct mass stays508*87=44196; small-board full BFS checks the independent
tau1/tau2 formulas under the same <=5000/15sec qualifier budget above.

At most5000 edge-pair motifs (15sec shared family), no human reference or new
duration law. Freeze all source pins and one-shot raw output. After construction
compare only the frozen diagnostic census's H tau1/tau2 counts and the explicit
trap world's claimed slab metadata, not full ordered-world rerun. Then refine
both-law moment bounds using direct and exactsecond mass; remaining worlds
get lower0 and upperm(3), including unreachable. This is approximation-bound
qualification, not an exact H vector or Xiangqi strategic validity.
