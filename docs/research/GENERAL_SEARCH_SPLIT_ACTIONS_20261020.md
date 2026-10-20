# Split actions as a conditional search-interface option — 2026-10-20

## Decision question

Does generic-game search literature justify replacing GenericChess's atomic
typed `Action` edges with partial-move states to lower branching?

## Primary-source finding

Kowalski et al., “Split Moves for Monte-Carlo Tree Search” (AAAI 2022),
studies automatically derived semisplit variants in the Regular Boardgames
formalism. Splitting a move into simpler choices can help, including in
single-action games, but a partial choice need not extend to any legal move.
The authors model intermediate/dead states explicitly; prechecking whether a
prefix can complete may cost as much as generating every legal move. Their
strength evidence is for MCTS/RBG games and does not establish a benefit for our
AlphaBeta engine or full generated-rule domain.

Primary source: https://arxiv.org/abs/2112.07761, §§1–3, 5–6.

## Repository boundary and decision

Core already streams complete legacy and semantic legal `Action` objects.
Semantic execution obtains full legal action/binding pairs, including guards,
postconditions and auxiliary-state effects. AlphaBeta's `SearchRuntime` then
caches the complete legal-action tuple for membership and transitions; search
accounts the complete generation request. Turning a prefix into a search state
would add partial-turn control, dead-end semantics, history/TT identity,
cancellation and depth/qsearch questions, while risking visibility of
incomplete promotion/drop/auxiliary transitions.

The recent measured cost campaign instead identified repeated checked-submit
validation as the online bottleneck and reduced it without changing action or
rule semantics. A preregistered screen then measured legal generation on one
saved deterministic root for each of eight candidate96 rules, with a 4096-node,
depth-4, qdepth-0 cap and the default AlphaBeta route. It started no games,
training or outcome comparison and completed in 1.93 seconds total. Per-root
generation fractions of decision wall time were 0.0%, 25.9%, 6.2%, 4.4%,
19.2%, 17.5%, 17.7% and 12.4%. The mean was 12.9%, median 14.9%; one of eight
roots exceeded 20%, while three were below 10%. These heterogeneous eight roots
do not show a repeated material generation bottleneck across rules. They are a
screen, not a population estimate, and the one elevated root does not by itself
justify adding partial-turn state. Keep atomic actions and existing
complete-generator path; make no API, default, implementation or training
change. Reconsider only with a new measured workload that repeatedly shows
generation dominates end-to-end cost.

Reconsider only if a new measured workload shows complete action materialization
dominates total cost and a bounded prefix/cursor prototype can produce only
complete legal `Action` values, preserve the full transition/history contract,
and reduce end-to-end paid cost under a fixed budget. Any future trial must
count dead prefixes and generator work and compare unchanged rule outcomes; do
not claim transfer from MCTS results alone.
