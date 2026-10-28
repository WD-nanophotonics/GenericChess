# One-path main check extension — 2026-10-28

Delivery update2026-10-29: reviewed sync completed throughc4d1cdca;latest USER default approval supersedes the initial local-only consent queue below. Historical closure states/caps/failures stay unchanged;delivery follows this research commit.
The default-OFF prototype changes real search coverage, but has **no playing
quality evidence**. Both frozen candidate-game designs stopped before any game:
48 initial-position slots and24 checked-history slots remain NOT_STARTED.
Do not activate, refill, retune these gates or call this a negative strength test.

## Mechanism and verified contracts

At a nonterminal positive nominal depth d, after winning-declaration handling,
a checked node with entry allowance e=1 spends delta=1. Children receive
(d+delta-1,e-delta); siblings, PVS re-searches and aspiration retries use their
proper parent/root allowance. Qsearch and actual ply/clock remain unchanged.
At d=0 this mechanism does not add a main layer. A d1 checked node can therefore
search an opponent's quiet response after the evasion, beyond baseline Q-only
coverage; it does not generally cover the evading side's next-turn defense.

TT identity retains its complete original state/history/clock/Q-policy guard and
adds policy version plus ENTRY allowance. Stored depth remains nominal. No
cross-allowance EXACT/LOWER/UPPER dominance is assumed. Cached PV validation uses
the same depth/allowance transition. Mate distance still uses actual ply.
Counters distinguish expanded extension nodes from TT-only returns; completed
iteration depth is nominal. main_search_max_ply is measured only when extension
is enabled (OFF zero is not evidence of a zero-depth search).

75 relevant controls pass: independent abstract d1/d0 trees, both warmup
allowance directions and numeric bounds, sibling/PVS/aspiration transfers,
actual six-family full-history cold/hot/TT-off/PV checks, inside-extension
cancellation rollback, real max-ply/repetition terminal priority, outer service
limits and resource-reader controls, plus40 shared search regressions. These
are semantic controls, not strength measurements. Optional fields are appended
for positional API compatibility. Final isolation edits skip extension helpers
on the disabled hot path and reject uncertified/non-Leaper public opt-in scope.
No speedup of those final edits was measured. All experiment frozen sources
predate those isolation edits and remain preserved, rather than relabeled.

## Actual finite stages

| Stage | Saved returns | Qualification | Candidate games |
|---|---:|---|---:|
| New24 initial roots, D2 |41|40 passed,1 D1 cancellation,7 NOT_RUN|48 NOT_STARTED|
|12 exposed checked histories, D1 Player|24|Legal D1 all24, only1 choice-difference family|24 NOT_STARTED|
|Six second checked histories, direct fixed Q4|12|All returned,0 capture drops|0 planned|

The first frozen gate also had zero initial action-difference families. q0040
was a legal baseline D1/first-Q0 result, cancelled at its3-second allowance,
not a complete D2 or Core-proven immediate win. Expectations/caps were not changed.
The checked-history follow-up was separately frozen using ALL first two checked
ongoing histories per family, selected before expansion or score observations.
It was an explicit development follow-up, not the first preregistration or holdout.
It too failed its three-family action-difference gate and was closed.

Core-only replay first found12 legal evasion/quiet-opponent-response witnesses
in all six exposed families. The six previously unqueried second histories then
produced12 bounded direct-Q4 traces: all six actually entered an extra quiet
main layer, three changed root actions. The real Player first completed iteration
uses ordinary Q0, explaining why that fixed-Q4 observation does not establish
first-iteration or equal-service behavior. Extra coverage/score/action changes
are not corrected WDL or a unique root-value causal explanation. Trace capture
omits complete Q-return/TT-producer dependencies and has no own loaded-binary
receipt; other stage receipts are not retroactively substituted for it.

Independent saved-return readers verify41+24 originals,79+36 literal legal PV
plies and all72 NOT_STARTED game slots, privately and from the public-format
compressed copies. A legal return is kept distinct from a passed qualification.
[Evidence manifest](data/leaper_check_extension_20261028/manifest.json).

## Decision

Keep the prototype OFF. The separate1s-vs2s default-controller experiment is
[an endpoint resource control](LEAPER_RESOURCE_RESOLUTION_20261028.md), not evidence
for this extension. Preserve these failures and coverage witnesses; revisit
only with a changed, prospectively frozen informative state-distribution premise.
No C build, solver, training, new worker, AUX or scheduler change occurred.
At original closure this report/source remainedlocal. The2026-10-29 delivery
update supersedes that temporary approval queue;no retrospective push is claimed.
