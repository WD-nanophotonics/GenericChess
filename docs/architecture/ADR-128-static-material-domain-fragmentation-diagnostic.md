# ADR-128: Static same-type movement-domain fragmentation diagnostic

- Status: pre-registered zero-game topology diagnostic; no material formula change
- Material comparison baseline: frozen V2D `B0=U+C`
- Scope: Western Chess and Standard Shogi

## Causal diagnostic and minimum observation

The unknown is whether invariant same-type movement-domain fragmentation is a general rule property aligned with V2D's remaining positive Chess residual, especially its largest no-transition residual. The minimum observation is the per-owner directed graph of executable same-type intrinsic movement under the frozen V2C finite-population event measure, its weak components, and the parameter-free domain statistics below. No games, search, Heavy, Xiangqi, learning, density change, transport term, transition premium, or material formula modification is authorized.

## Graph and semantic boundary

For a current type `t`, every board square is a node. Add directed edge `s→u` for a compiled, type-preserving intrinsic movement outcome with nonzero exact event probability. Include quiet and capture movement, path/screen occupancy, source restrictions, direction and restricted regions. Union equivalent semantic descriptions for each owner/source/target before testing whether probability is nonzero. Construct owner 0 and owner 1 graphs separately; never combine their edges before component analysis.

Convert each owner's directed graph to its underlying undirected graph. This tests invariant spatial domains, not one-way tempo or transport efficiency. Include all board squares, including isolated nodes, in components. Type-changing outcomes do not create source-type edges; ledger their promotion/type-transition edges separately. If promotion is optional and an unchanged-type outcome is legally available, that unchanged branch may create a same-type edge. A forced type change creates no same-type edge. Drops/re-entry, history/auxiliary-state-only actions, and dynamic positional legality are separately ledgered and excluded. Unsupported semantic coverage fails closed.

For component sizes `s_i` over area `A`, report per owner:

`D = sum_i (s_i/A)^2`, `F = 1-D`, `largest_component_fraction=max(s_i)/A`.

`D` is the probability two independent uniformly selected squares lie in the same invariant domain. Average owner-specific D/F/component summaries only after computing each side's graph independently under the frozen owner symmetry rule. No human, transport, named-piece or game-specific feature enters graph construction.

## Frozen development diagnostics

Before loading V2D validation residuals, freeze this ADR, implementation, focused tests, exact per-owner directed edge sets/hashes, component memberships/sizes, D/F, and excluded transition/drop/history/dynamic ledgers. The raw feature candidate imports neither V2D residuals nor V2E values.

After freeze, compare only to existing V2D development residuals. Within the rules-derived no-outgoing-type-transition subset of ordinary Chess reference types, preregister three descriptive conditions: (1) the largest positive scaled V2D residual has `F>0`; (2) its F strictly exceeds the median F of the other no-transition reference types; (3) at least one in-band or underpredicted no-transition type has lower F. Report Pearson and Spearman for that subset when it has at least three types, without a sign gate. These are development-set observations, not statistical significance or permission to modify scores.

Report the same topology statistics and outgoing transition presence for every ordinary and promoted Shogi board type; do not create a Shogi material gate. Classification is `STATIC_MATERIAL_DOMAIN_FRAGMENTATION_HYPOTHESIS_SUPPORTED`, `...NOT_SUPPORTED`, or `...INCONCLUSIVE`. Even a supported result authorizes only a next Chat hypothesis, not automatic combination with material values.
