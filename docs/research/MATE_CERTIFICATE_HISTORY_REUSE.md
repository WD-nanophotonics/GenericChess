# Revalidate a strategy under history; never reuse an unqualified label

The new source question is whether useful proof reuse requires duplicating
every entire historical search. Kishimoto and Mueller describe path-specific
entries plus simulation of a previous proof on a new path. Their proof trees
retain a winning OR continuation and all AND continuations; their correctness
argument assumes solved entries remain available. The paper explicitly leaves
replacement/garbage collection as an open issue. Thus a board hash plus a
correct solver result is not by itself a persistent replay certificate.
[Primary paper, AAAI 2004, pp644-649](https://cdn.aaai.org/AAAI/2004/AAAI04-102.pdf).

Local inference: treat a foreign strategy as an action proposal, not a terminal
value. Replaying one locally legal attacker continuation can establish a lower
bound for that attacker; every locally legal defender continuation remains
necessary. Revalidate terminal precedence, history and the decreasing remaining
horizon at each node. If a solved foreign node has no reproducible children,
keep unknown. This does not require importing the foreign solver's TT policy.

## Existing local paths inspected

`MateOnlyPublicGame.terminal` calls PublicGame's fresh terminal boundary before
projecting nonmate results to unresolved. `observe` checks unresolved BEFORE
winner and has no transposition cache; its owner-zero max/min direction is
explicit. `terminal_first_interval` also checks unresolved before winner, but
its ongoing DTM branch is a conditional arithmetic interface, not an associated
mate-source importer. Its caller must bind the full state and goal premises.
`partial_decision_loss` accepts exact owner-zero intervals and reorients them
for the root owner. It does not authenticate their provenance or goal: never
mix mate-only, horizon-WDL and full-WDL intervals merely because all have the
same numeric shape. No observed current mate-source consumer bypass was found.

SavedContactProofGraph's graph is indexed by complete action prefixes, decodes
full recorded GameState, checks fresh terminal results, and marks missing
states/expansions unresolved. This avoids board-only transposition merging. Its
cached action lists rely on the previously qualified producer; the constructor
alone does not independently re-enumerate or authenticate all saved edges.
It is an exposed Chess evidence adapter, not a foreign Shogi proof verifier.

## Limits of local identity

Position/repetition identity excludes history. SearchStateIdentity adds ply,
repetition counts and an adjudication summary; its documentation explicitly
does not make path-dependent Standard Shogi TT-compatible. The current-position
check summary need not determine future repetition adjudication for every
other reachable position. Do not promote this summary to a complete proof-cache
identity without a separate sufficiency argument. Use the original full history
for local replay now. No source execution, imported labels, new game tree or
old failed-window deepening was performed in this source/consumer audit.

The production runtime uses a stronger boundary than SearchStateIdentity's
public summary: RuntimeHistoryContext retains a persistent chain of exact
position identities plus actor/check evidence, and compares that chain after
a digest match. RuntimeSearchKey includes this context when tt_eligible;
continuous-check search refuses TT use without the eligible runtime. Full
history and absence of opaque imported keys/witness misses are required.
This supports the current runtime guard; it does not authorize a foreign
board-hash cache or promote the public summary to the runtime's exact chain.

Next useful application: bounded local strategy replay under the full public
defender generator, with an explicit attacker and literal goal contract. A
missing strategy/export remains a soft blocker; numeric search integration
and independently declared material-prior questions can proceed separately.
