# ADR-114: F44 structural capability feature diagnosis

- Status: Diagnosis-only F44 boundary
- Baseline: `7166a743911926156de75825cd02c7c622aaa172`
- H44A protocol: `tests/fixtures/f44_structural_capability_manifest.json`
- Audit implementation: `scripts/audit_f44_structural_capability.py`
- Production change: none; no evaluator feature was integrated

## Decision

F44 selects `MULTIPLE_STRUCTURAL_INFORMATION_GAPS`; the next boundary is
`F45_STRUCTURAL_FEATURE_DISCRIMINATION`. Endpoint/control semantics,
conditional capability reserve, and density-profile shape each establish
independent discarded information. Channel diversity is relevant and varies
strongly across pieces, but its matched synthetic witness did not collide in
the current four-component representation, so it is not independently
selected at this boundary.

The audit uses the accepted F41 ordinary candidate population and the same
RuleSet compiler/analyzer. It does not change endpoint algebra, density
points/weights, production evaluation, or F43 transforms.

## Independent witnesses

S44-A has a matched collision: `quiet_only` and
`quiet_plus_capture_same_targets` have identical current mobility, coverage,
reachability, and path-efficiency values, while their endpoint signal differs
(the latter has nonzero dual-use overlap). This proves an executable
quiet/control distinction is collapsed by the current scalar representation.
For real Western pieces, Pawn has quiet mass `0.875`, attack mass `1.53125`,
zero overlap, union `2.40625`, and latent attack gap `1.35707`; ordinary
N/B/R/Q share quiet and attack geometry, while Pawn separates forward quiet and
diagonal capture geometry. The current endpoint factors remain empty-only
`1-density/2`, enemy-only `density/2`, and empty+enemy `1-density/2` with quiet
precedence.

S44-B proves a separate discarded reserve: current capability excludes
conditional patterns, yet a synthetic ordinary base and the same base with a
guarded identical capability collide in all four current components. Western
Pawn has 3 ordinary and 3 conditional patterns, conditional path-clear-only
reserve `2.1106`, and reserve/ordinary-mass ratio `2.4121`; the conditional
geometry is retained as an upper envelope, never as permanently legal mass.
Standard Shogi has zero conditional capability patterns in the audited
ordinary population, providing a negative control for this reserve.

S44-D proves that the current mobility term consumes a full density curve but
retains only its weighted scalar average. The audit records retention at all
five frozen density points, weighted retention, maximum drop, curvature, and
fragility ordering. Western weighted retention / maximum drop is P
`1.085/0.000`, N `0.886/0.250`, B `0.694/0.593`, R `0.637/0.678`, Q
`0.659/0.645`. Standard Shogi shows the same structural distinction: P
`0.886/0.250`, L `0.614/0.708`, N `0.886/0.250`, S `0.886/0.250`, G
`0.886/0.250`, B `0.672/0.625`, R `0.614/0.708`, with promoted values retained
in the machine-readable ledger.

S44-C is measured without selection. Western effective channel count /
concentration / largest share is P `1.532/0.705/0.810`, N
`5.250/0.224/0.224`, B `2.687/0.440/0.525`, R `3.160/0.329/0.383`, Q
`5.799/0.187/0.230`. Standard Shogi similarly ranges from concentrated Pawn
and Lance channels to more diverse promoted and multi-direction populations.
The channel control is canonicalized by geometry signatures and is invariant
to generated IDs/order in its extraction, but the one-vs-two-channel control
also changed the current four-component representation, so it does not meet
the frozen independence predicate A.

## Cross-rule structural table

| Ruleset/type | Endpoint overlap | Conditional reserve ratio | Effective channels | Weighted density retention | Max drop |
|---|---:|---:|---:|---:|---:|
| Western P | 0.000 | 2.412 | 1.532 | 1.085 | 0.000 |
| Western N | 1.000 | 0.000 | 5.250 | 0.886 | 0.250 |
| Western B | 1.000 | 0.000 | 2.687 | 0.694 | 0.593 |
| Western R | 1.000 | 0.000 | 3.160 | 0.637 | 0.678 |
| Western Q | 1.000 | 0.000 | 5.799 | 0.659 | 0.645 |
| Shogi P | 1.000 | 0.000 | 1.000 | 0.886 | 0.250 |
| Shogi L | 1.000 | 0.000 | 1.000 | 0.614 | 0.708 |
| Shogi N | 1.000 | 0.000 | 1.778 | 0.886 | 0.250 |
| Shogi S | 1.000 | 0.000 | 4.049 | 0.886 | 0.250 |
| Shogi G | 1.000 | 0.000 | 5.136 | 0.886 | 0.250 |
| Shogi B | 1.000 | 0.000 | 2.764 | 0.672 | 0.625 |
| Shogi R | 1.000 | 0.000 | 3.210 | 0.614 | 0.708 |
| Shogi promoted | retained in ledger | 0.000 | 5.136..5.221 | 0.659..0.886 | 0.250..0.633 |

## F43 residual explanation

F43's per-geometry log substantially repaired Western R/Q because those pieces
carry high long-ray/channel mass; Knight remained comparatively high because
its many short independent channels are not compressed in the same way.
Source-level and hierarchical saturation then overcompressed R/Q. F44 shows
that these cases differ in endpoint/control separation, channel structure,
conditional reserve, and blocker fragility; another global concavity curve is
not justified. The next stage must discriminate structural features rather
than invent another scalar transform.

## Corrective R1 closure

The first F44 submission was not accepted because the selector counted raw
`independence.pass` flags, derived invalid classification names by string
replacement, and hardcoded the density witness. It also used a guarded
conditional control with a different geometry from its ordinary base.

R1 preserves H44A and closes those defects. The guarded control now uses the
same leap geometry and endpoint relation as the ordinary base; only the state
guard differs. The audit derives the ordinary-component collision, conditional
pattern-count difference, nonzero reserve, and guarded-pattern exclusion.
The density controls now use a leap to displacement two and a ray with
`min_steps=max_steps=2`, giving equal empty-board mass `0.75` but distinct
curves and maximum drops `0.250` versus `0.625`. The density B predicate also
records the full five-point curve, its consumer path
`expected_mobility -> density_weighted_mobility -> component_values.mobility`,
and that curve shape is not retained as a current component.

The selector now consumes explicit per-family predicates:
`independent_information`, `independence_basis`, `synthetic_witness_pass`,
`real_ruleset_relevance`, `f43_residual_relevance`,
`cross_rule_consistent`, and `materially_supported`. It uses H44A's exact
classification mapping and has reachability tests for endpoint-only,
conditional-only, channel-only, density-only, multiple, insufficient, and
cross-rule-conflict paths. Corrected evidence materially supports S44-A,
S44-B, and S44-D; S44-C remains unselected because its matched collision is
false. Therefore the mechanically recomputed classification remains
`MULTIPLE_STRUCTURAL_INFORMATION_GAPS` with boundary
`F45_STRUCTURAL_FEATURE_DISCRIMINATION`.

## Scope and boundary

The complete machine-readable ledgers are under `.generic_chess_flow`:
`f44_endpoint_control.json`, `f44_conditional_reserve.json`,
`f44_channel_diversity.json`, `f44_density_profile.json`,
`f44_synthetic_controls.json`, and `f44_selection.json`. Focused tests cover
H44A integrity, the F42/F43 baseline, endpoint collisions, conditional reserve
separation, canonical channel/density extraction, cross-rule coverage, and
the single mapping-selected classification. F44 does not execute F45 and does
not promote master.
