# When a target-free quiet graph can be reused

2026-10-05. A proposed cost reduction for COMPATIBLE_CONTACT_TASK_DESIGN.md,
not a claim that an arbitrary movement graph gives compatible capture times.
This local theorem and its rule applicability audit are our deductions.

LaValle describes shortest paths on a state-transition graph with cumulative
nonnegative action cost; that requires states and transitions of the declared
planning problem. His planning-graph discussion explicitly distinguishes
overapproximated reachability from extraction of an actual plan. Neither result
licenses dropping occupancy guards. See [optimal graph planning](https://lavalle.pl/planning/node44.html)
and [planning graphs](https://lavalle.pl/planning/node63.html).

## A sufficient unit-cost contract

Fix passive own blockers, source base/current mode and owner, and one stationary
enemy target. Let A be the actual virtual quiet graph and Q the target-removed
quiet graph, embedded in the same finite source-mode/square node universe.
Terminal set C contains only nodes with a validated actual one-action target
removal; terminal queries still use the target-present world. The source-on-
target node is invalid and cannot itself be a terminal query. Contact costs1.

Require (i) every A edge is a Q edge; removing the target never disables a
quiet transition, including guards and promotion successor mode; and (ii)
every Q edge absent from A has its tail in C. Thus the first target-induced
invalid quiet step can be replaced by a contact at the same or earlier cost.
Missing coverage, unrepresented history or an unsupported effect is unknown,
not satisfaction of the contract. Preserve base origin in both graphs.

Then the minimum length of a Q path to C followed by contact equals the minimum
length of an A path to C followed by contact, including unreachable infinity.
Proof: A inclusion gives relaxed distance<=actual distance. For any relaxed
solution, either every quiet edge is actual, or stop at its first invalid
edge. The valid prefix reaches a tail in C, hence contact produces an actual
solution no longer than the relaxed solution. This gives the reverse inequality.
This is a sufficient contract, not a necessary characterization of equality.
Weighted or stochastic actions require a new cost/continuation contract.

## Rule audit: eligibility is conditional

Ordinary symmetric quiet/capture leap and clear-ray patterns are promising:
landing on the target, or attempting to pass it on a clear ray, has an earlier
direct capture. This still requires checking matching target/source zones,
promotion eligibility, target-type tests and other effects. Rook/TR in the
new Shogi task are candidates; the measured pair alone does not certify all
nodes, modes, blockers or an implementation of this optimization.

Current western_chess.py has distinct straight Pawn quiet moves and diagonal
captures. A forward target can invalidate a quiet edge without allowing a
capture at its tail. Its double-step also writes an auxiliary token; it is not
a source-square-only transition. En-passant requires history/auxiliary state.
The generic contact adapter must not silently admit these omitted dependencies.

Current xiangqi_diagnostic.py gives Horse leaps an empty leg-square guard and
Elephant leaps an empty eye-square guard. A target on that leg/eye can disable
a leap without being a legal one-step capture. Cannon quiet rays require zero
screens, but captures require exactly one screen, so stopping at the newly
encountered target need not be a capture. General facing capture additionally
tests target identity. These source observations reject automatic eligibility,
not prove that every instance has a wrong distance. They concern diagnostic
rules, not full Xiangqi legality or held-out human values; none were read.

## Independent controls and construction decision

test_contact_reuse_contract.py exhausts all three-state directed quiet graphs,
all nested actual/relaxed edge relations, every common terminal set and all
starts that satisfy the contract. It compares independent BFS distances, also
covering cycles/unreachable goals. Tiny counterexamples show dropping either
inclusion or the invalid-edge-tail condition can change contact time. They
are abstract graphs, not extra chess measurements or material validation.

A possible constructor first proves the contract for an exact intrinsic mode
family, reuses its quiet graph across targets, and keeps target-specific terminal
queries. Ineligible modes retain target-specific guarded paths and honest budget
intervals. Target-conditioned graphs may share raw compiled event/cube tables
without sharing evaluated quiet edges. That latter safe caching option does not
require this theorem because each target still tests its own definite occupancy.
No full mode batch or preprocessing budget increase is authorized by this note.
