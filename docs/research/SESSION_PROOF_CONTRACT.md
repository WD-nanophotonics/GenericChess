# Optional session proof: authority and cost boundary

DEV_AUX research scripts, not production/default integration. Both iterative
AND/OR and Session PN emit SessionWinCertificate; only the separate public
GameSession replay verifier admits an executable SessionStrategyCursor.

A leaf records the exact actual SessionResult and the target must be its winner.
UNKNOWN, RESTART/no-contest, draw, depth or time cutoff cannot form a winning
leaf. An interior target node contains one legal typed choice; a defender node
contains the complete set of board actions and owned declaration IDs, including
claims assessed as LOSS. Resignation is omitted as dominated in a forced-win
query. Actual declarations end a session without mutating its Core GameState;
therefore board-only outcomes or position keys cannot replace session authority.

Root fingerprint, exact GameRecord and complete GameState are bound. Every
verification edge independently reconstructs the current record via public
GameSession.replay and submits/declares the typed choice. Target-edge legality
is established by that public execution, avoiding unrelated frontier generation;
defender set equality still requires the complete frontier. Duplicate choices,
missing defenses, mixed action/claim forms and nondecreasing or false ranks are
rejected. Rank is zero at an actual winning terminal and otherwise one plus the
maximum child rank. Finite induction therefore supplies an executable strategy
against every represented legal defense, conditional on public-rule correctness
and determinism. This is not a new proof of the entire rule executor.

PN proof/disproof numbers select work; they do not independently authorize a
win. Target aggregation is min proof / sum disproof; defender aggregation is
sum proof / min disproof. Actual terminals set exactly one of these to zero.
Depth-unknown nodes have both infinity. A partial target frontier can stop only
on a proved child; a partial defender frontier can stop only on a refuting child,
whose infinite proof number prevents a winning AND certificate. Winning defender
nodes therefore exhaust all choices. Interruption before frontier installation
or certificate completion returns UNKNOWN, not a partial all-defense witness.
No TT merges states or histories. The verifier independently replays transitions
but shares choices()/execute() with the provers; it cannot alone exclude a shared
choice-enumeration defect. Actual public two-claim outcomes and explicit expected
refusals test this boundary without duplicating an execution framework. Stored session snapshots share immutable
values; actual public submit/declare replaces the clone's tuple/state/marker.

PN counts newly inspected tree nodes; iterative search counts repeated visits.
Neither is an equal primitive-cost budget. Report actual elapsed proof and
verification time, frontier/transition counts where available, cap failures,
source revision, and exposed-case dependence. A shorter proof on these cases
is not a faster material learner or a general engine strength result.

JSON transport uses strict public GameRecord/action codecs and reconstructs the
root by actual replay. Decoding is explicitly UNVERIFIED; the independent
verifier/cursor remains required. A source-bound full-state repr SHA catches
transport/root mismatch but is not a portable identity standard. No pickle,
eval, private session state injection, or trusted winner label on import.

Named initial setups are not arbitrary GameState imports. They retain default
inventory and cannot encode fresh initial side1. The fresh-root helper validates
zero ply, exactly one genuine initial history/count entry, actual terminal and
all board/hands/aux fields before rebinding the initial provenance key under a
new explicit rules fingerprint. Existing played history is never discarded.
The old KRN study roots fail this admission; no balanced Session learning assay
is claimed on their behalf. Future integration requires an explicit supported
root/record design, separately frozen distribution and unchanged fixed opponent.
