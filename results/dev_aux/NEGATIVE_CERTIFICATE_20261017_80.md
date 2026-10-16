# Scoped negative certificate: avoiding forced WIN

This is an opt-in research prototype in task2320. It does not label a current
game DRAW/LOSS, replace actual terminal rewards, or change a player/default.
The motivating observed cost is repeated positive-only searches at positions
where no proof was admitted. A timeout is UNKNOWN, never a negative proof.

A certificate is a finite graph of COMPLETE typed Positions and public actions.
At a target-turn node it covers every legal action. At a defender-turn node it
supplies one legal action. Every successor stays inside the graph or is an
actual Position terminal whose winner is not the target. Edges may form cycles.
The root binds the exact current rules, GameRecord, full state and target. An
independent checker reconstructs every edge using public Core execution; a
separate cursor rechecks admission and observes actual GameSession transitions.
A repeated repetition identity is not permission to merge different full
Positions: owner/base/current/promotion/hands/side/aux/types remain authoritative.

The closure invariant is elementary: while the actual Session is ongoing, the
defender follows its recorded edge, and every target action remains in the graph.
If the actual Session terminates by ordinary repetition or finite max_ply DRAW,
it has avoided targetWIN. Otherwise the invariant continues until a checked
non-target-winner terminal. Finite max_ply guarantees termination. This yields
existence of a defender strategy avoiding targetWIN, not optimal-policy WDL or a
prediction that the fixed experimental foe will follow that strategy.

The safety argument requires the admitted2199 execution scope: Position-only
legality/effects/terminal structure, draw repetition and finite positive max_ply.
Declarations, non-draw perpetual rules, automatic/no-progress/consecutive/
repeated-cycle history conditions remain rejected. An actual ended root is
handled by its real result and is rejected as an ongoing proof query. The graph
cannot borrow a synthetic late-ply/repetition DRAW to close an otherwise live
node. Local canonical construction uses fresh ply0/history; it never substitutes
an artificial cutoff DRAW for missing edges. Actual checkmate/stalemate priority
is evaluated before ordinary history draws. A target mate exactly at max_ply is
still targetWIN and cannot be a negative leaf.

Unlike positive DAG lifting, this safety graph does not need a strictly decreasing
rank or an injective repetition identity: an early real DRAW is safe. It remains
conservative for finite-horizon-only refutations; canonical target reachability
outside the remaining horizon may prevent certification even if the actual
short-horizon game would draw. Unsupported history semantics stay UNKNOWN.

The untrusted generic builder enumerates the complete reachable Position graph
under a node/edge/time cap and computes the target-win attractor. Only a closed
graph complement can produce a candidate. Incomplete graph, incomplete attractor,
root in the attractor, failed verification or failed current admission stays
UNKNOWN. A second, explicitly reference-assisted constructor prunes defender
choices using the preexisting paid reference; it is not generic discovery or a
free deployment filter. Both still pay independent verification and current
admission. No online skip or reward integration is part of this segment.

External comparison: Dietmar Berwanger's author-hosted MPRI2009/10 notes,
[Graph games with perfect information, Section2](https://lsv.ens-paris-saclay.fr/~dwb/gtc.pdf),
define reachability attractors by existential moves for the reachability player
and universal moves for its opponent, and show that the complement supports a
positional avoidance strategy. This informs the finite graph construction; the
history/terminal/representation assumptions above require separate project
checks and are not supplied by that graph-game theorem. The notes were actually
read through Section2, including the attractor argument and counter algorithm.

Dot1792173669 reviewed the inline plan and fixedb612 Core terminal source only,
not80 code/execution. Its borrowed-DRAW objection motivated real max_ply1 mate
and missing-action controls. Twelve adversarial tests now pass, including four
actual closed-cycle rollouts, stale history/root/rule binding, incomplete budgets,
wrong merges, unsupported perpetual handling, and a REAL four-ply same-Position
history rebind followed by actual third-repetition DRAW. The old test-wrapper
failures remain saved; tests and source analysis do not establish all-domain
soundness or practical proof-discovery efficiency. The ALL14 context cost study
and its independent consumer determine whether further implementation is useful.


Scope check against the current PRIMARY handoff: its latest mainline reports
actual automatic PENDING checking histories continuing beyond a nominal rule
horizon. DEV_AUX only read HEAD/mainline at
a942e319c5e812dc998758fab95095a1b7a17d34, and did not rerun those results. Own
Core source confirms automatic PENDING precedes the max_ply test. Thus finite
max_ply alone is not sufficient across arbitrary generated rules. This prototype
rejects ANY automatic adjudication before graph checking; a new actual compiled
RuleAutomaticAdjudication fixture verifies that boundary. The claimed termination
argument is deliberately restricted to that admitted scope. No PRIMARY changes
or broad all-rule termination assertion follows.

An actual defender deviation outside the certified edge is also rejected by the
current cursor; a root refutation is never a global skip for later unrelated roots.
