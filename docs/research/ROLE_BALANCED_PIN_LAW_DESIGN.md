# Role-balanced sparse law: declared design and cost decision

2026-10-05. Source-only design; no game observations, new goal labels or
admitted vector. A concrete alternative to choosing a favorable template
separately for each queried mode:

- Standard Shogi, own King a1 and enemy King i6 OR i7, equally weighted.
  Enemy native Pawns e6/f7 in both frames. Designated target chosen uniformly
  from these two physical Pawns; both targets remain in the actual board.
- Other own ordinary base u uniformly in P,L,N,S,G,B,R. Queried mode m is
  either native/promoted board base/current or held base, n=1, origins explicit.
- With probability1/2, queried token is source, placed e5 if board or held;
  other token u is native board support at a6 OR a7 matching enemy King rank.
  With probability1/2, queried token is supporter at that square if board or
  held; other token u is native board source e5. Source role stays fixed for
  the target event, even when a coalition omits that source.
- Rank reflection/owner swap has weight1/2. Fresh history/ply0. Sparse missing
  stock is explicit; no standard-game reachability/conservation claim.

The primitive product has2*2*7*2*2=112 equal-mass frames per queried mode.
Do not drop a frame whose legal roots/task/identity mapping are unsupported,
reweight by successes, select a different target for a type, or reset an actual
successor history. Unsupported frames retain task intervals. Native dead-rank,
nifu, safety and Session checks still require full authoritative qualification.
Origins with base B/R plus same-base supporter use at most the standard two
physical tokens; n=2 held extension is NOT silently allowed for those pairs.

For each frame and S subset{source,supporter}, use the same designated physical
target/custody event, controlled over two own actions plus two enemy replies.
Allocate the task using RESOURCE_MARGINAL_CONSTRUCTION_HYPOTHESIS.md and record
the query's source/support role before averaging. This law does not demand
positive coefficients or borrow material labels; it exposes role effects.

## Decision before any batch

112 frames/mode across13 board and7 held modes require2240 context frames and
8960 coalition task cells, before any game branching. Source-absent cells are
analytically0, but even the remaining4480 cells are not licensed as cheap by
the128-transition/5000-enumeration cap. A small independent bounded pilot may
qualify one changed mechanism or partial intervals, NOT exact full estimates.
It may not reset the global budget per mode or turn unvisited cells into0.

The law's two rows/targets remove the earlier single-front-target exclusion of
native Knight by construction, but this is a SUPPORT expectation to qualify,
not a observed positive mean. Its role averaging still treats one Pawn target
unit as task demand, carries finite-window saturation and hypothetical missing
inventory, and could yield signed/zero mode allocations. Even a complete pass
would leave static leaf transfer and independent Shogi goals unproven.

Do not execute an enormous table or a coefficient batch now. The useful next
falsifier is one predeclared new matched role/target comparison under ONE shared
small cap, or analytical bounds that genuinely reduce unknown coalition mass.
This is a concrete finite approximation law, not a unique rule-selected law or
a mandate to solve WDL first. Candidate-independent use remains locked until
the actual candidate vector/interval selector is frozen and mode-complete.
