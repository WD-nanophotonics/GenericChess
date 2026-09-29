# The initial state alone cannot support a type-wide action prior

**Unknown.** Can the RuleSet's declared initial position supply a canonical,
game-independent context for deriving each ordinary piece's static value
from its immediately executable actions, avoiding an arbitrary context
distribution?

**Smallest falsifier.** In Western Chess, enumerate legal actions only at the
compiled RuleSet initial position and group them by the moving piece's
current type. The observation is bounded to one position and one movegen
call; it does not score a formula or inspect material references.

| Type | Legal initial actions for side to move |
| --- | ---: |
| Pawn `P` | 16 |
| Knight `N` | 4 |
| Bishop `B` | 0 |
| Rook `R` | 0 |
| Queen `Q` | 0 |

The 20-action total is a direct result of `initial_state`, `legal_actions`,
`action_source_square`, and the compiled Western Chess RuleSet. It is also
forced by the familiar initial blocking geometry, but the executable count
checks the exact local semantics. The initial position is rule-declared and
requires no frequency model. It does **not** expose immediate actions for
three of five ordinary types, so an initial-state-only option valuation would
assign them zero or leave them unidentified. Neither is a defensible
context-independent material prior merely by calling the context canonical.

Expanding to later reachable positions would expose their actions, but it
again requires a horizon and a way to compare or weight different histories.
This is a failure of this specific context-selection principle, not a
claim that initial positions are useless for validation or that every
rule-derived approximation is impossible. Do not turn the 20 moves into a
new entropy/feature-count formula; those older routes already failed their
declared tests.

**Next lead.** A context ensemble needs an independently justified support
and weighting that both represent dormant types and respect rule-preserving
renaming. Before running a broad enumeration, seek a tiny representation
invariance falsifier for one proposed weighting. The default of uniform
legal histories is not yet justified as strategic visitation or material
utility. Keep Xiangqi material values sealed.
