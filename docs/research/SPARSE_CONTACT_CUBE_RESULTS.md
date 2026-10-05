# Shared sparse-occupancy semantics beyond clear paths

The new primitive passes its declared movement-only controls: Cannon screens,
two-event corner preparation, Horse legs, Elephant eyes/river, Advisor palace
and Soldier river-dependent lateral moves. All12 controls agree with full
semantic root membership for both owners (24 states). One actual Cannon quiet/
capture route retains its original source and own screen, with explicit virtual
turn reset. No public GameState or independent goal query was run.

All six ordinary diagnostic profiles share23 canonical geometries/2791 cached
candidates instead of8642 repeated pattern candidates.36 board patterns,
188 explicit semantic membership entries (including apply's second checks),
2 virtual physical events,0.110sec. It does NOT compute a Xiangqi mode-price
population. No human value, historical deployment label or holdout was read.
Five behavioral tests pass: exhaustive one-blocker cube projection, frozen
owner controls, selected Shogi P/N/S promotion/vacating comparisons, whole
Western Pawn auxiliary-pattern rejection and all frozen input hashes.

## Why the occupancy algebra matters

A path-clear event excludes every blocker square on its ray. A one-screen
capture instead REQUIRES the blocker to lie on that ray. Eye/leg predicates
exclude one distinct square; zone predicates can make the event identically
empty even on otherwise geometrically reachable squares. These are exact
different bitsets, not coefficients multiplied by a guessed success factor.
Alternative compiled physical descriptions union masks, never add overlapping
events. First/second masks are disjoint; a quiet prefix preserves original
enemy/background squares and vacates the original source before the capture.

Existing intrinsic event-cube functions are reused as pure semantic primitives;
their historical material/population calculators are NOT invoked. This avoids
another independently maintained copy of eye/leg/zone/promotion semantics.
The new shared cache changes construction cost, not the old frozen producers.

## Complete-constructor boundary

The accepted grammar is restricted to compiled single-source movement and
target removal with ordinary occupancy/source/zone guards and simple promotion.
Any unsupported pattern in the supplied profile closure invalidates the whole
profile table; there is no filtered-mode, zero-weight or midpoint fallback.
Western P is correctly rejected because its full grammar includes double-step
auxiliary mutation and en-passant/off-target removal. Earlier Chess contact
Pawn bounds explicitly omit such shortcuts; their narrower virtual task remains
valid, but cannot become a complete generic semantic constructor by renaming.

Promotion origin is retained. Both diagnostic owners are checked through actual
compiled reflection, but arbitrary multi-type/legacy-atom binding compositions
and full historical Xiangqi legality are not admitted by these selected builder
controls. Global resource conservation, dynamic royal safety, drop/mate/history
and active enemy survival remain separate gaps. No new generic scalar prior
or Xiangqi validation admission follows from these semantic controls.

Next put the already complete Shogi20-mode BOARD/HAND approximation into a
strict declared leaf-use interface, or qualify Western auxiliary-state reduction
before claiming full generic construction. Independent usefulness remains OPEN.
