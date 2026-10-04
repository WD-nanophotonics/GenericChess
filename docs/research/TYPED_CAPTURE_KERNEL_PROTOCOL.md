# Sparse typed capture-incidence diagnostic, before observations

2026-10-04. New changed premise: type-dependent active placement supports;
COUPLED_CAPTURE_CONSTRUCTION.md explains why independent victim types collapse.
This licenses incidence information only, not coefficients or game outcomes.

Compile current Western Chess and Standard Shogi. Types are the sorted ordinary
current types present in the actual initial board; exclude anchors. Do not use
game/piece names to select support or arithmetic. Retain intrinsic event audit
coverage/exclusions. Unsupported intrinsic semantics abort; do not give zero.

On each owner/source, evaluate each event cube on an otherwise empty board,
with own actor at source and, for capture events, one enemy at the sole resolved
removed square. Multiple-removal events are outside this diagnostic and abort.
Union compatible event descriptions. Source is active if at least one empty-
target quiet event or single-victim capture event is possible in this scope.
Capture identity is source/victim-square existence, not destination/promotion
branch count. Off-target removal may qualify if its other constraints hold.

For each actor/victim type pair i,j and owner o, use actor support S_i,o and
opponent victim support S_j,1-o. Uniformly distribute over distinct ordered
square pairs in their Cartesian product; reject an empty support/pair population.
K_ij is the owner-averaged exact fraction of such pairs with a capture incidence.
Compute a second matrix with every type supported on all squares. No blockers,
other actors, anchors, own-anchor safety, history, hand drops, custody payoff,
promotion premium or terminal utility is modeled. Capture-to-hand counts only
the board removal existence. Type-independent cubes remain type-independent;
only the declared placement law supplies victim-type information.

Report Fraction-valued matrices, support sizes, pair/capture counts per owner,
exact rational rank, identical-column groups and first lexicographic nonzero
2x2 minor. The all-square matrix must have identical columns and rank at most1.
Any violation rejects the implementation. Active rank>1 is INFORMATION_PRESENT,
rank<=1 is NO_NEW_COUPLING; neither is material validation. Do not change law,
threshold, support or type family after seeing results. No eigenvectors, fitted
weights, conventional material bands or holdout files are read or produced.

One process, at most100,000 compiled candidates per type (existing intrinsic
cap), 10 seconds total diagnostic including compilation, no state transitions.
Budget failure is incomplete, never a larger-budget retry. Focused tests may
exercise semantic controls independently, not repeat a failed numerical batch.
Freeze protocol hash into the runner before the first real-game observation;
output pins program, event composer, source-rule files and protocol hashes.
