# PVS OFF/ON pure-Leaper pilot - 2026-10-26

**NO-GO for more PVS experiments on this exposed panel at this budget.** All
24 actual Core games were draws: four repetition and twenty max-ply. PVS ON
scores12/24, with no positive movement family. No product/default/backend change,
solver, training, extra game, refill or new worker follows from this result.
It does not prove PVS generally useless or either policy minimax-optimal.

## Approved scope and what ran

The user directly approved the [published limited proposal](LEAPER_PVS_QUALITY_DECISION_20261026.md)
and cumulative320-minute ceiling before the first Player call. Prior related
200.3688811whole minutes, including its old cap overshoot, plus a conservative
21-minute design/delivery allowance remain charged. The new cost origin is
2026-10-26T13:14:08Z; the resulting whole-chain deadline is14:52:45.867134Z.
That is98.6311189remaining minutes, not a fresh320-minute allowance. Offline gaps
and administrative work are not effective research credit. Detailed session and
closing-cost evidence accompany the packet/own ledger; no clock reset erased
prior work. The old deferred16-game Native-service experiment stays deferred.

Exactly12 published full h2 histories, six movement families on5x5/6x6 boards,
were used without outcome selection. Full RuleSets, max-ply96, repetition4,
preludes, clocks and exact TT/history guards remain. They are exposed,
correlated development inputs, not12 independent family draws or a holdout.
Only PVS differs. Both arms use original AlphaBetaPlayer, DEFAULT evaluator,
disk cacheOFF, Native legality/availability/check requestsTRUE, ordering and
root tactics as current defaults, Q4/hard8, depth64/node500000 ceilings. Thus
OFF is the product's PVS setting with these identical opt-in Native services,
not a claim to benchmark every desktop default. Each seat has a separate fresh
Player/TT per game, retained across its own turns. Seat order alternates across
roots; each exact initial history gets both ON-seat assignments.

All24 cold D3 qualifications returned complete depth3 with equal paired scores
and legal chosen actions/PVs. Different search work is allowed. All12 selected
actions also happened to match. ON executed2323 null-window searches. This is
limited shallow correctness evidence, not a deep/all-rule certificate.

The subsequent24 games produced2115 original Player returns. Total2139returns
include the qualifiers. Nominal per-turn allowance is1s for both policies, with
an independent monotonic caller-deadline token created immediately before each
Player invocation. The same cooperative token implementation is used in both
arms. It can return reason cancelled at caller expiry, not necessarily internal
time_limit. No token is reused across calls, and no watchdog/thread was added.

Qualification took3.733265s of UTC stage span (3.101736s of Player outer calls),
inside the separate90s reservation. The game/recording batch took2210.782465s,
inside its2700s reservation. These reservations are additive. A five-second
in-flight dispatch reserve and720-second whole-chain delivery reserve were
frozen before execution; they reduce risk rather than prove a hard atomic bound.
All24 slots completed; no dispatch/whole-cap extension or replacement occurred.

## Outcomes and censoring

| Movement family | Actual ON points /4 games | Fixed4 budget-qualified score bounds |
|---|---:|---:|
|0|2|[0.25,0.75]|
|1|2|[0.5,0.5]|
|2|2|[0.5,0.5]|
|3|2|[0.5,0.5]|
|4|2|[0.5,0.5]|
|5|2|[0.5,0.5]|

One OFF call, g1184 in game13, took1.1198713s and exceeds the frozen1.1s
eligibility threshold. Its real draw remains in all actual results.23games and
11complete swapped-seat pairs are timing-eligible. Threshold1.1s is neither
the requested1s budget nor a guaranteed execution limit. Qualified subsets are
descriptive and do not remove timing selection bias.

For the fixed24-slot budget estimand, both games12/13 of the affected pair are
UNKNOWN, rather than dropped and renormalized. The mean ON score bounds are
[11/24,13/24]. Enumerating their nine possible W/D/L score completions permits
at most one positive family; the frozen advancement rule needs at least three.
Thus censoring cannot rescue that advancement gate under this fixed-slot bound
convention. This is score bookkeeping, not inferred minimax action values,
confidence intervals, hypothetical rerun results or population significance.
No Elo estimate or universal strength conclusion is supported.

## Mechanism and cost boundaries

| Actual game trajectories | OFF | ON |
|---|---:|---:|
|Player returns|1056|1059|
|Outer Player seconds|1044.057129|1044.928871|
|Process CPU seconds|1042.218750|1043.218750|
|Main visits|2620529|2692144|
|Q visits|2938450|2798079|
|PVS null-window searches|0|1700745|
|PVS re-searches|0|10182|
|Native legality frontier calls|2229173|2170349|

These are different visited trajectories and call counts, not matched-position
speedups. All2115 game results retain source main_iteration.2075 returns report
caller-deadline cancellation with that deadline observed; none is misclassified
as user stop.40 reach depth64 early, all with only1-3remaining clock plies and
score0. Different binding limits must not be recast as equal actual wall work.
No Native legality fallback/operational failure or availability decline occurred.

The twelve first-decision OFF/ON comparisons share the exact full starting
histories.11choices match; n6-f1-h2 changes action (OFF D6 versus ON D5). Another
root reaches a deeper ON iteration without changing action. These are mechanism
observations, not WDL labels or evidence that a changed choice is better/worse.

D3 sum outer cost is1.552349s OFF versus1.549387s ON (ratio0.998092); median
paired ratio1.005506, with6/12faster ON roots. Main+Q visits9206 versus9388.
One small timed pair per root does not establish a repeatable net cost gain.
More scout activity or depth cannot substitute for a decision-quality endpoint.

Outer call timing ends after the actual return, including PlayerDecision
construction. The Player's own elapsed field ends earlier. Compile/replay,
constructors, raw recording, ledger and PV validation are separately charged
inside total cost. Game-batch minus summed outer calls is121.796464s, an outer
remainder rather than a measured removable component. Setup0.863365s includes
the0.140994s constructor subset; do not add those overlapping categories. Native
internal exclusive wall and peak total RSS remain UNKNOWN; no profiler was added.

## Validation and the next concrete consumer

An independent saved-data consumer replays2115 full-history game decisions and
10738 supplied PV plies against Core, binds every original return, checks roots,
legal full semantic actions, actual terminals and seat perspectives.26empty PVs
remain explicit and legal under the default TT contract; no unseen TT producer
chain is invented. Public compressed bytes/input/source hashes are separately
checked.2115 selected transitions also check exact two-cell board footprint,
unchanged hands/aux, side switch and rule identity. These validations do not
independently reproduce search or establish all-defense WDL certificates.

The next useful source-only step was begun, without new Player/solver/game/build:
current Semantic selected pushes still use Python _transition, then exact
identity/history/snapshot/clock/terminal work. Reverse attack sources, Native
membership tables, another Native backend's two-square undo, and the existing
plain-Leaper two-cell hash certificate already exist; none is claimed as new.
Compiled legacy lowering retains dormant DROP patterns, but all allowed masks
are false in these12 complete rules; the existing certificate already handles
that distinction. IR syntax alone must not misclassify these as mixed games.

Actual saved availability queries all reuse the input packed by readonly check:
10448711OFF and9762446ON, with zero availability imports. Replacing only the
check predicate can move this shared packing to availability rather than save
it. Geometry/attack-count algebra alone cannot authorize terminal/history skips;
attack overlap needs OR/multiplicity, not XOR or duplicate-pattern double-check
counts. Pseudo-attacks also differ from fully legal move masks.

One specific UNIMPLEMENTED candidate remains worth a finite design assessment:
certified immutable two-square child construction at this Semantic selected-step
seam, avoiding generic WorkingPosition hand-dicts/events/effect dispatch. The
existing HASH footprint certificate is not alone a transition-equivalence proof:
child hand/aux/shape normalization, unexpected input fallback, cancellation,
rollback, full identities/history/TT and Core terminal precedence must still be
preserved. Net whole-call benefit is UNKNOWN. No cache/kernel, renewed H6S3,
profiling, old16 games or follow-on experiment was selected or authorized here.

## Review and delivery provenance

New autonomous Patrol8edbf21d was fully preserved/read during same-round resume.
Its5f134bbd preapproval snapshot said approval was pending; the later direct user
approval preceded execution and takes precedence. Its endpoint, opportunity-cost
and cap cautions are retained; it did not independently run this pilot.
Dot's source-only boundary advice was read/adopted without making it a budget
or work gate. The single delayed reply check executed13:40:09Z instead of its
13:21:09Z due time; that lateness is a workflow deviation, not a five-minute reply
expiry. No duplicate request, empty polling or AUX assignment occurred.

One archive-reader test initially failed before its body because pytest selected
a protected system Temp directory. Only that failed item was rerun in a fresh
own ignored basetemp and passed; no expected value or scientific record changed.
The relevant publication test suite and matching quality/session receipts are
recorded with delivery. No product source/default/UI, public repository visibility,
other checkout or existing schedule was changed.

Scientific session d368da11-f6b1-4a86-90d4-3da519cb6efd ended safely at
2026-10-26T14:32:07Z with3636.680397recorded effective seconds(60.611minutes),
2146intervals and matching quality review; finish/final-checkPASS. Conservative
whole cost at that checkpoint299.356839/320minutes; delivery remains charged
through actual closure rather than added to research. The later small source
normalization check illustrates a candidate boundary, not a new game/search or
a current bug. Product source and defaults remain unchanged.
