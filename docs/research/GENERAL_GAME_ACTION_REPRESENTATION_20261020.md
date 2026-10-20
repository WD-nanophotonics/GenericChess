# Generic search action identity from general-game systems — 2026-10-20

## Question

Does general-game search/training literature imply that the current generic
search interface should flatten its legal actions into a fixed policy-output
space?

## Primary-source finding

Soemers et al. describe a Ludii–Polygames bridge that automatically maps
game states and moves for many rule descriptions. The paper explicitly notes a
limitation of its fixed tensor action representation: distinct legal moves can
map to the same output logit. In Polygames, the search tree still represents
those moves as distinct branches and may back up different values, although
the neural policy prior cannot distinguish them. The authors also report a
large performance failure on Lasca, a stacking game, and leave the right
representation/model treatment open. Their experiments use 20-hour runs with
eight GPUs per game, so those strength results do not transfer to our small,
resource-bounded decision tests.

Primary source: Soemers et al., “Deep Learning for General Game Playing with
Ludii and Polygames” (2021), especially the action-aliasing discussion and
multi-game results, https://arxiv.org/abs/2101.09562 and
https://arxiv.org/pdf/2101.09562.

## Check against this repository and consequence

GenericChess currently keeps legal `Action` objects as tree-edge identity;
`action_to_dict` assigns distinct tags and fields to board moves, drops,
semantic board moves, semantic drops and pass. The prior `PassAction` recording
repair preserves that identity inside research `PlayerDecision` records. The
source and existing tests therefore already enforce the relevant boundary for
the current engine.

Keep exact legal actions and their state transitions as the authoritative search
interface. A future learned prior may use an approximate feature/logit mapping,
but any aliasing must be explicit and must not merge legal tree edges or lose
the selected action when applying/recording it. This literature adds a concrete
future integration criterion; it does not justify a new policy head, API,
training run, backend change or current product edit.
