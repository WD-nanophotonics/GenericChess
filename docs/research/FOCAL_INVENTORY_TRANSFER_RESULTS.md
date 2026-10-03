# Focal replacement is a prototype background, not unchanged inventory

The prehashed FOCAL_INVENTORY_TRANSFER_PROTOCOL.md checks twelve symbolic
owner/base-type count vectors from compiled initial Chess/Shogi rules, with the
frozen sampler source hash. It does not enumerate more transitions or states.
Input rule/code base is c5e10c6a122361071e2d1face4ab835d93d06c01; the program
and vectors are in data/focal_inventory_transfer_20261004.json.

The sampler's physical placeholder occupies one initial own Pawn slot. Querying
type t gives I_query(t)=I_initial-e_(own,P)+e_(own,t). Every non-Pawn query
therefore has one fewer Pawn and one more queried token than actual initial
inventory. Four Chess and six Shogi non-Pawn base types have count L1 distance2.
Both Pawn queries preserve the count vector. Tests reconstruct each substitution
on the already frozen physical boards and confirm the symbolic vectors.

If compared with ANY defined nonempty distribution retaining actual initial
inventory and an existing focal token of type t, the non-Pawn laws have disjoint
supports in full Position space: the inventory-count event has probability1
under the query law and0 under the actual-inventory law. Under convention
TV(mu,nu)=sup_A|mu(A)-nu(A)|, TV=1. Conditioning on safety or Pawn structure,
changing weights or restricting to reachable states cannot erase the count
invariant as long as neither population is empty. For binary task X, the bound
|E_mu X-E_nu X|<=TV therefore only says <=1, offering no useful guarantee.

This does NOT prove the expectations actually differ; a constant task can have
the same mean on disjoint supports. It does not certify reference nonemptiness.
Equal counts for Pawn also do not imply equal laws, TV0 or successful transfer.
The twelve count comparisons take roughly a tenth of a second; they are exact
support bookkeeping, not strategic population or piece-value observations.

This comparison keeps all initial tokens on board with empty hands, as in the
current proposal law. Held/captured-token populations need their own count and
transfer contract; the certificate is not silently extended to them.

## Decision

Keep the replacement law as an explicit conditional prototype if its intended
approximation remains justified. Stop describing it as the unchanged actual
initial inventory for every queried type, or invoking 'common background' alone
as a small-distribution-shift certificate. The reference-background construction
is legitimate but a transfer approximation, not a consequence of linearity.

A smaller task-sufficient projection or a validated transfer experiment might
support useful type-local coefficients despite the coarse TV bound. It must
justify retained information; the earlier background-coupling and stalemate
controls show that arbitrary omission of remote tokens or terminal effects is
unsafe. Do not repair the sampler, launch score batches, fit values or change
context weights merely to make the inventory supports match. The next scientific
choice remains the intended static target, reference population and predictive
loss. Xiangqi material evidence remains sealed and engine evaluation unchanged.
