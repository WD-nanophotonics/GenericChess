# Independent closed-form Cannon distances under the frozen virtual law

The complete9x10 compiled census already existed. This new result independently
qualifies its full distance2/3/4 masses analytically; it does not repeat that
census, release a holdout or introduce another occupancy prior.

Fix target d and own screen b on one line of length L, with M perpendicular
lines. A firing square must lie beyond b away from d. Let their count be g.
If g=0 or b/d are unaligned, contact is unreachable: the final capture ray
cannot contain its required exactly-one occupied interior square.

For g>0, partition the LM-2 possible source squares:

| Source class | Count | Minimum own actions |
|---|---:|---:|
| Already on a firing square | g | 1 |
| Off target line, same perpendicular line as a firing square | g(M-1) | 2 |
| Other off-target-line square | (L-g)(M-1) | 3 |
| On target line, outside firing region, excluding b/d | L-2-g | 4 |

The second class makes one clear perpendicular quiet move before firing.
The third makes two quiet moves, first along its unobstructed off-target line,
then perpendicular into a firing square; one quiet move cannot change both
coordinates. The fourth must bypass b/d on another line: leave the target
line, move along the parallel line, return beyond b, then fire. Two quiet
segments cannot bypass an obstacle between collinear endpoints: a perpendicular
departure would still require a perpendicular return and an along-line change.
Three quiet segments suffice for any M>=2. The moving source vacates its old
square; it cannot act as a second stationary screen. These are physical
compatible-path arguments, not positive-support witnesses from different worlds.

For one line, eligible ordered b/d pairs number P=(L-2)(L-1). Summing g over
those pairs gives G=L(L-1)(L-2)/3, from sum_j 2*j*(L-1-j). Across M parallel
lines the four contributions are M*G, M*(M-1)*G,
M*(M-1)*(L*P-G), and M*((L-2)*P-G). Add the two axis orientations, whose
distinct b/d pairs do not overlap. All omitted worlds retain unreachable mass.

On9x10 this gives3840/32400/64800/5264 at distances1/2/3/4,598576 unreachable,
total704880. Every count equals the existing frozen compiled result. This now
independently qualifies BOTH predeclared Cannon duration moments in aggregate;
it does not establish per-world agreement at the other89 targets or qualify
the other diagnostic modes' full histograms. Existing source/royal/history and
diagnostic-only Xiangqi restrictions remain unchanged.

## Fresh bounded independent controls

Elementary ray scanning and BFS on3x3 and4x2 reproduce the formulas for840
ordered worlds, including unreachable and distance4 cases. The BFS calls no
compiled/event/cube code and uses no source-class shortcut from this theorem.
4910 expanded nodes are charged, below5000; elapsed0.016sec, zero compilations,
canonical compiled candidates, runtime pushes, public transitions/source queries.
No repeat is permitted merely to obtain a more comfortable cap margin.

Evidence: `data/cannon_distance_closed_form_20261006.json`, frozen protocol,
producer and formula. No new material-vector calculation or law selection.
The useful next constructor question is the other modes' independent aggregate
coverage, keeping context-law uncertainty distinct from semantic disagreement.
