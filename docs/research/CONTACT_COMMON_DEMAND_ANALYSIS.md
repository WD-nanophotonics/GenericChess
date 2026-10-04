# A complete fixed-frame demand law without a coefficient batch

2026-10-05. New analytical scope, BEFORE the proposed deep Lance witness.
Same source-only fixed-target task: owner0 source a7, passive own native P e7,
ordinary stationary enemy P target uniformly over the79 squares other than
a7/e7. Other squares empty, no opponent turns or dynamic/history adjudication.
Demand geometry is identical across queried modes; no per-type reachable-target
conditioning. This is ONE fixed source/background frame, not the board-wide
construction/deployment law, and its means are task statistics, not prices.

## Native Rook and current Dragon

Native R has11 direct targets: eight on the a-file and b7/c7/d7. The64 targets
off both source rank and file have a compatible two-action path via the a-file
on their target rank; Pe7 is off that rank. Direct exclusion establishes tau2.
The four remaining targets f7/g7/h7/i7 require3 actions. After a first R move,
its source lies either on the a-file or at b7/c7/d7. A promoted Dragon's added
diagonal steps cannot reach those four distant targets from such a first node,
and every aligned second ray from rank7 is still blocked by Pe7. A native
detour through rank6 supplies a length3 witness. Optional promotion cannot
invalidate these minimum counts. Thus the complete fixed-frame histogram is
{1:11,2:64,3:4}; this population extension is a geometry proof, not79 game runs.

Starting current TR adds direct b6/b8 targets, leaving the same four behind
the blocker at distance3 and62 others at distance2. Its histogram is
{1:13,2:62,3:4}. The shared-law preparation advantage over R is
2*(gamma-gamma^2)/79, positive on(0,1), not independent material usefulness.
Under the SAME79-target law with e7 excluded also in the clear world, native
R has{1:15,2:64}. The blocking mean difference is4*(gamma-gamma^3)/79.
Do not normalize the clear world over80 targets while comparing these means.

## Native Lance: promotion changes the reachable preparation problem

Current standard_shogi.py defines native L forward rays and TL Gold steps
(0,1),(+-1,1),(+-1,0),(0,-1), owner0, promotion zone ranks6..8. From a7,
a8/a9 are the two direct contacts. A quiet move to a8 can promote to TL;
a9 must promote because native L otherwise has no movement. For every other
target a native ray first ends at a8 or a9, or later repeats that same route.
There is no alternative board-current promotion type for native L here.

Gold distance in an empty rectangle is max(abs(dx),dy) for dy>=0, and
abs(dx)+abs(dy) for dy<0: forward diagonals combine one horizontal and one
forward step, while backward motion has no diagonal. Monotone rectangle paths
attain these lower bounds. Starting at a8 or a9, Pe7 cannot raise the bound:
for a backward-and-horizontal destination the two boundary paths (horizontal
then backward, or backward then horizontal) avoid that single blocker on at
least one route; one-coordinate routes are on the a-file or rank8/9, not e7.
The blocked destination itself is excluded. This is task-specific; the metric
does not ignore arbitrary blockers or real-game safety.

Using zero-based target coordinates(x,y), for x=0,y=7/8 native tau=1.
For x>0,y=7/8, tau=1+x. For y<=6, tau=8+x-y, excluding source(0,6) and
blocker(4,6). Promotion at a8 attains it; promotion at a9 is never shorter
except ties for rank9 destinations. Staying native at a8 before a9 cannot
improve the minimum. Hence exact fixed-frame mass at distances1..16 is
2,2,4,5,6,6,8,9,9,7,6,5,4,3,2,1, summing to79.

The longest example i1 has native-L minimum16: one quiet promotion a7-a8,
eight horizontal Gold steps to i8, then seven backward steps ending xi1.
Freeze a bounded intrinsic event witness before observation. Its lower bound
is the analytical metric/first-promotion argument, not a complete official
game search. Record base L/current TL and definite occupancy on every step.

## Why this is an actionable constructor lead

Each histogram defines sum(p_t*gamma^t) with a common79 denominator and exact
analytic coverage of this fixed frame. Do not turn these three task means into
an admitted mode vector, select gamma on exposed values or claim untouched
validation. Positions near a promotion zone can strongly affect native modes;
a wider independently motivated source/background law and independent use
evidence remain necessary. Source geometry formulas can reduce preprocessing
cost only after their hypotheses and compiled transition semantics are qualified.
The pending witness tests one changed semantic premise, not those missing laws.
