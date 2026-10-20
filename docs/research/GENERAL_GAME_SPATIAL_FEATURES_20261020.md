# Spatial state-action features as a bounded generic-search candidate — 2026-10-20

## Question

Does spatial state-action feature research justify replacing the current generic
search/evaluation interface, or does it identify a narrower future candidate?

## Primary-source result

Soemers et al. formalize local binary features around a state-action pair and
introduce SPatterNet to evaluate active features efficiently. Their performance
comparison covers 33 Ludii games and shows more efficient feature matching than
the naive and prefix-tree approaches. The paper distinguishes this engineering
result from policy utility: it cites earlier work for learned policies and
strength improvements, while inter-game transfer of those policies remains
future work.

The representation deliberately has limits relevant to our target. Its spatial
features inspect only the primary board, not hands or other containers, and the
formalization focuses on orthogonal graph relations. The authors identify
additional representation work for under-supported game categories. It is
therefore not a drop-in evaluation over GenericChess's complete rule domain,
which retains promotion, drops, auxiliary state and relevant history.

Primary source: Soemers et al., “Spatial State-Action Features for General
Games,” Artificial Intelligence 321 (2023), 103937, especially §§4–6 and §7:
https://ludii.games/publications/ARXIV2022-1.pdf; bibliographic record:
https://doi.org/10.1016/j.artint.2023.103937.

## Mainline consequence

Treat efficient local feature matching as a possible implementation technique,
not as evidence for static price transfer, full-domain coverage or playing
strength. Keep the exact structured action/state transition interface. Revisit
such a feature candidate only if a concrete question specifies how it retains
hands, auxiliary state and history and an affordable matched comparison can
change the model choice. No feature code, training run, API/default change or
current route reopening follows from this source review.
