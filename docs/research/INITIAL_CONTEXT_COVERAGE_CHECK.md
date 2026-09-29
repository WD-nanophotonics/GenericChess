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

**Bounded Shogi coverage cost check (2026-09-29).** To test whether the
smallest reachable-history horizon covering all ordinary types might be
cheap, breadth-first enumerate *histories* from the Standard Shogi initial
state through depth 2, using `legal_actions` and `apply_action`. The resource
limit was 1,200 generated histories and 15 seconds; the abort criterion was
either limit before finishing a depth. All 900 depth-2 histories completed
within the limits. Group legal board actions at each frontier by the actor's
current type and inspect whether either hand has a token:

| History depth | Histories | Board actor types seen | States with hand tokens |
| ---: | ---: | --- | ---: |
| 0 | 1 | G, K, L, P, R, S | 0 |
| 1 | 30 | G, K, L, P, R, S | 0 |
| 2 | 900 | B, G, K, L, N, P, R, S | 0 |

Here `K` is the anchor; the six promoted ordinary types have no action in
this bounded frontier, nor does any hand mode occur. Thus an exhaustive
history ensemble with full board/hand type coverage needs depth greater than
2; the tested 900-history frontier is still incomplete. Histories are not
claimed to be distinct full semantic states or a visitation distribution.
This check does not prove that no symbolic or sampled later-context scheme
could be cheap. It does show that "expand until every type appears" is not a
cost-free rule-derived substitute for an independently justified context
measure, especially in a capture-to-hand game. No Shogi material reference
or Xiangqi value was used.

**Next lead.** A context ensemble needs an independently justified support
and weighting that both represent dormant types and respect rule-preserving
renaming. Before running a broader enumeration, seek a tiny representation
invariance falsifier for one proposed weighting. The default of uniform
legal histories is not yet justified as strategic visitation or material
utility. Keep Xiangqi material values sealed.
