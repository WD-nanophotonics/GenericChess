# Unfamiliar-rule search: first interface/cost observations

2026-10-08. Primary search work measures efficiency, stability and rule support,
not Elo, learned prices or an increasingly strong Chess player. The first
declared tier3 set uses existing generator seeds7/21, board4/6, bilateral_random,
hybrid movement, existing promotion/drop derivation and playability filters.
These four initial positions do not cover the user's tier1/tier2 mechanics.

```powershell
.venv/Scripts/python.exe -m scripts.unfamiliar_search --output .local_agent/new-search.json --depth 3 --shared-profile
```

Output must be new; immutable earlier evidence is not overwritten. Same roots,
fixed generic-v1 evaluator/profile, depth/budget, q0, root tactical scan off,
fresh TT per repeat. Plain Python legality/noTT/noordering compares with the
existing public TT/ordering bundle, two repeats. All selected moves/PVs replay
through Core. Exhaustive minimax has its separate4096-evaluation/5sec fuse;
an aborted reference is unknown, not a candidate pass or speed comparator.
Generic-v1 includes existing heuristic terms and is not the contact formula.

| Root | Depth3 plain nodes | TT/ordering nodes | Plain search seconds, first | Bundle seconds, first |
|---|---:|---:|---:|---:|
|4x4 seed7|65|92|0.0118|0.0175|
|4x4 seed21|231|227|0.0460|0.0485|
|6x6 seed7|1270|544|0.5105|0.2784|
|6x6 seed21|2018|822|0.6545|0.2918|

All16depth2 calls are complete/repeat-stable/legal and equal reference scores.
All16depth3 calls also complete/repeat-stable/legal.4x4 references agree;
6x6 references stop at the declared fuse. Repetition/history beyond initial
roots, harder tactics and broad generated distributions remain untested.
Small controls can visit more nodes with ordering/TT. No universal speedup.

Profile construction initially costs about0.009/0.009/0.083/0.044seconds by
root; an uncached player repeats that work. Existing shared memory profile cache
reduces measured player setup to tens of microseconds. No production cache
change. High-resolution external search timing is now recorded, since Windows
decision.elapsed_seconds sometimes rounds tiny calls to zero. Original outputs
and source versions remain separate, rather than silently correcting old costs.

## Semantic/native route: actual support, not an assumed universal adapter

The generator returns legacy CompiledRuleSet. NativeSemanticLegalityProvider
requires CompiledSemanticRuleset, so the requested native legality flag falls
back here. Native extension is installed; this is a compilation/interface scope.
Direct semantic compilation rejects empty DSL actions (NO_SEMANTIC_ACTIONS).
A directly passed semantic IR also lacks the piece_types attribute required
by the AlphaBetaPlayer profile builder. Failures and exact source are retained;
no production compatibility shim or broad fallback framework was added.

A separate diagnostic adds an equivalent quiet anchor-leap replacement to
activate the existing semantic compiler. Complete depth2 successor positions
and terminal outcomes match the original generated rules:48root/676second
children, zero differences ignoring only compilation fingerprints. This is
local parity, not arbitrary-history equivalence or a newly invented mechanic.

Existing native fixed-depth semantic search then agrees with the existing
independent Python packed-action alpha-beta oracle on score/best/PV, four roots,
two calls each. Both use the same ordinal type-index+1 leaf values for an
interface test; those are not a useful price candidate. No TT or model training.
Native/Python first-call seconds:0.0013/0.0166,0.0033/0.0639,0.0666/4.6972,
0.0305/1.7156. Native compile and root packing are separate in the raw record.
Different representations/runtime/visited nodes contribute; this is not a pure
language comparison or evidence that every custom rule is supported efficiently.

The first full-dictionary parity assertion found47vs52 nodes but identical
mate score, best move and PV. Retain that interrupted record: node-count equality
is not semantic parity. The completed diagnostic compares decision fields and
reports both counts; no score or success rule was changed to favor a move.
The semantic fixed-depth API works on these inputs; public generated-player
and semantic-player integration is still not unified. Next: one concrete
recombined mechanic and persistent root/history reuse via existing supported
semantic search, with declared leaf, budgets and separate startup/steady costs.

Exact declarations, all successes/failures and source recovery are indexed in
data/direction_reset_20261008.json and the matching archive. No learning/NNUE,
new worker, default search/evaluator change or amateur-strength claim.

## Subsequent single-root persistence control

One separately declared6x6 seed7 root, existing SemanticSearchEngine,1MiB TT,
depth3/4096nodes/5sec/q0, same ordinal leaf. A child is selected as the
lexicographically first Core legal action before searches, retaining its actual
one-ply history. Cold/warm initial roots and reused/fresh child roots all complete
at depth3 with score8; all PVs are Core-legal. Node counts1949/936/2001/2149,
TT hits110/242/156/115; observed seconds0.0591/0.0340/0.0612/0.0622.
This shows useful supported persistence on one unfamiliar-rule witness, not
universal history/adjudication coverage or statistically established speed gain.
It narrows the next task to one actual recombined mechanic, rather than building
a new engine or assuming persistence must be implemented from scratch.

## Recombined-mechanic control

Two fixed5x5 roots with the same inventory exercise an owner-relative blocked
leaper, capture-to-base-hand and explicit downgrade to a weaker step. Closing
the leg yields0custom actions; opening it yields1, with captured base J in hand
and the actor retaining base J/current W. Both depth2 native calls per root
match independent Python score/best/PV and every native PV is guarded-legal.
Scores are -1/7; no strength or price-quality inference follows. Three initial
producer construction errors (missing guard fields, missing promotion sets,
wrong promotion-set shape) remain separate incomplete records and source versions.
This is a small tier2 interface witness, not all mechanics or history coverage.
