# First-action target access: a topology and event-identity check

## Unknown and smallest observation

Can the ADR-130 source-local product `b(s) |Reach(s)|/A` stand for the
expected number of *first actions* from `s` that can eventually access a
uniformly selected target? Test two four-vertex directed graphs before
computing another game value. This is a model-definition check, not a
material formula or an outcome claim.

Let the vertices be `s,u,v,x`. Both graphs have first edges `s→u` and
`s→v`. Graph G1 also has `u→x` and `v→x`; graph G2 has `u→x` only. Count
the starting vertex in each directed reachability set, as ADR-130 does.

| Quantity at `s` | G1 | G2 |
| --- | ---: | ---: |
| First-action count `b(s)` | 2 | 2 |
| `Reach(s)` | `{s,u,v,x}` | `{s,u,v,x}` |
| ADR-130 source product `b(s)|Reach(s)|/4` | 2 | 2 |
| `Reach(u)` / `Reach(v)` | `{u,x}` / `{v,x}` | `{u,x}` / `{v}` |
| `(|Reach(u)|+|Reach(v)|)/4` | 1 | 3/4 |
| First actions with a continuation to target `x` | 2 | 1 |

The source product is a well-defined expectation of *source capability
retained when the target is source-reachable*. It cannot be reinterpreted
as the expected count of target-serving first actions. The two objectives
make different predictions even without occupancy, captures, promotion,
or strategic responses. Counting each first action separately is an
explicit option-capacity objective; it does not estimate the probability
of visiting the target, the payoff of doing so, or the value of a piece.

## Executable RuleSet gate

For a possible first-action objective, each counted event needs an owner,
source type and square, action destination and resulting type, event
probability under a declared context measure, and a rule for collapsing
equivalent semantic descriptions. Directed reachability after that
event must be computed from the resulting `(type, square)`, with type
changes and held mode handled explicitly. The formula and event identity
must be fixed before Chess/Shogi comparison and Xiangqi holdout.

The existing V2A/V2C successor grouping has a destination and final type
in its internal key `(owner, source, target, target_state, effect_key,
final_type)`. The V2D capture grouping instead uses `(owner, source,
removed_square)` and its public ledger lacks the destination. In a
generic RuleSet, removal can be at a square other than the destination;
`resolve_removed_square` supports target, path step, fixed and offset
references. The existing aggregate capture probability therefore cannot
always be assigned a unique postaction reachability factor. Current
Western Chess history-conditioned en-passant is already excluded from
the stationary V2C/V2D board model; that exclusion does not justify
silently identifying removal square with destination in generic rules.

The exact synthetic check in
`test_shared_off_target_removal_group_loses_distinct_action_destinations`
uses two nonhistory leap captures from the same 8x8-board source. They
land respectively one square right and one square up, require the
landing square empty, and both remove an opponent at the one shared
diagonal square. The compiled RuleSet has two distinct actions, while
the V2D public capture ledger has one physical-removal row with both
pattern names and no destination. Some boundary sources make this
offset invalid and the full synthetic audit therefore reports incomplete
coverage; the interior witness is locally valid. This confirms that
removal identity is insufficient for postaction reach weighting in the
supported interior event model.

Next gate: decide whether capture is a separate service channel or only
a consequence of the successor action, then define a destination-aware
event identity and test its representation invariance. If no invariant
event definition and independent comparison objective survives, reject
this candidate route rather than tuning against human values.
