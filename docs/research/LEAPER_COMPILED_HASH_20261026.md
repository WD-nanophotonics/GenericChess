# Pure-Leaper compiled hashing — 2026-10-26

A strictly admitted two-cell hash update reduced complete search-call wall cost
by **5.32%** in the frozen fixed-work study. It retained the observed actions,
scores, PVs, work, TT results and Native service counts. The equal-time check
changed none of 19 choices and repaired neither named error. This is a scoped
runtime improvement; the pure-Leaper decision-quality objective remains open.
Both new tuning switches default to **False**. No UI, evaluator, search-order,
rule clock, live history, terminal priority or TT guard was changed.

## What actually changed

`use_plain_leaper_local_hash` certifies executable IR before using the existing
component tokens on source, destination and side. Its square-board admission
requires plain leap patterns with exact move/remove effects, no promotions,
triggers, auxiliary slots, declarations, pass, progress or extra adjudications.
Unrecognized schemas and unsupported rules retain full semantic diff hashing.
Compiler-retained drop patterns are excluded only when all referenced drop masks
are disabled. Core legality, transition, check, repetition and terminal work still
run. The initial hypothesis that those drop geometries were unreferenced was
wrong; the preserved source diagnosis explicitly supersedes it.

`use_cached_position_identity_hash` is a separate, experimental lazy memo of the
same immutable Position Python hash. Equality remains exact, including typed aux
values. It uses the same rule admission, is independently switchable, and retains
all components of RuntimeSearchKey. Its whole-call cost evidence is incomplete.

The result adds optional local/full-diff operation counts and an actual-admission
cache flag. Hash-operation counts can include a push that later fails; completed
push/pop counts retain their existing meaning. Terminal results without runtime
observations continue to report None. Python changes require no Native rebuild.

## Registered measurements and results

The 12 generated cost controls use 4×4, 6×6, 8×8 and 10×10 boards, three fixed
orbit-mask pairs, complete six-ply histories or natural earlier termination,
max_ply 128 and repetition limit 4. They are exposed template families, not a
strength holdout. Fresh players start with cold TT; entries can be hit during
iterative deepening. Callers explicitly enable DEFAULT dynamic evaluation,
PVS, Native legality/availability/check, main ordering and Q4/hard8. Ordinary-Q
sorting stays off. Calls include compilation, replay, Player setup and search;
recording and verification overhead is separately present in batch receipts.
Pair order is counterbalanced; process caches and concurrent load remain limits.

| Study | Status | Result |
| --- | --- | --- |
| Actual-path observer | 10/10 returns | Five completed-D4 pairs preserve action/score/PV/work. Perturbed timer shares: semantic diff hash 9.4–11.0%, evaluation 3.8–5.3%, Native packing 2.1–2.5%; these are not unbiased production fractions. |
| Local hash, 50k nodes / 30s | 72/72 returns | 33 nonterminal pairs all reach node limit and preserve action/score/PV/work/TT/Native counts. Wall 270.023→255.653s, CPU 269.453→255.266s. Three natural-terminal pairs remain setup controls. |
| Four-arm factorial | **59/96 returns; 37 NOT_RUN** | 13 complete nonterminal groups: wall baseline 102.022s, local 96.763s, identity memo 101.097s, both 95.558s. Large-board second repetitions are missing. This is conditional prefix evidence, not the planned replication. |
| Equal 1.5s search budget | 38/38 returns | All 19 choices agree; both match 17 attributed optimal labels, with zero repairs/regressions. p49 and p53 still select labelled DRAW instead of available WIN. |
| Full-history contracts | 248/248 histories | 76,440 sampled branches and 13,947 actual walk plies agree on full hash, exact TT key, occurrence, terminal and undo. Four board sizes, all 31 radius-two orbit masks and symmetric/forward-only variants; at most six sampled branches per state. No complete-domain proof or solver census. |
| Final regression gate | 125 passed | 31 targeted tests plus 94 runtime/aux/rollback/Native tests, including warm/cross-flag TT, cancellation and simultaneous Python/component collisions. |

The factorial stopped because a terminal call took 8.54ms by perf_counter but
its UTC start and end were identical. The work ledger correctly rejected the
zero interval. That return is retained without effective-time credit; the 37
remaining slots were not replaced. Future callers skip unverifiable zero spans.
The raw CLOSED contract receipt retains its last slot in a misnamed
`unfinished_slot` field; 248 case rows and the receipt counts establish completion.

A separate two-call cProfile diagnostic hit both 30s caps because its own
unthrottled stop token repeatedly read files. It is invalid for identifying
search hotspots. Both returns, normalized statistics and the executed caller are
retained; its active defective script is retired. No replacement profile ran.
An analysis division by zero from a zero-resolution terminal CPU measurement was
also preserved; that CPU ratio is UNKNOWN, with raw observations unchanged.

## Interpretation and next action

The identity memo costs 8 bytes for its extra slot and 36 bytes for the example
cached int: +44 shallow bytes per cached identity. Actual live count and peak RSS
are UNKNOWN. Its isolated repeated hashing is about ten times faster while
unused construction and first-use hashing are slower. The factorial prefix
shows only about 0.91% whole-call gain for that memo alone. It is not a default
recommendation. The local hash has stronger repeated whole-call evidence.

The equal-time panel consists of 17 previously exposed source roots from nine
rules plus two known **5×5** controls. Earlier references to these two controls
as 6×6 were incorrect and are corrected in the old report. Their WDL labels are
attributed existing evidence, not newly solved proofs. Seventeen cases are
already at the observed ceiling; this panel cannot establish class-wide strength.
Native dynamic_features counts legal-action features, whereas the current Python
leaf uses pseudo-attack unions and escape terms; it cannot be substituted as an
equivalent evaluator merely because an API already exists.

A new structural witness uses two real king-only histories AB and BA, each with
eight plies, current occurrence three, identical position/counts/clock and public
Core search identity. Their conservative Runtime keys differ. Three one-ply
successors agree. This neither proves all futures equivalent nor authorizes a
history quotient; **every existing guard remains intact**. The safer next
feasibility question is memoizing the hash of the entire immutable search key.
An isolated 14-key wrapper probe preserves raw-key dictionary interoperability
and distinct history keys, but does not measure construction, actual search
frequency, memory or whole-call benefit. No production whole-key cache exists.

Continue pure-Leaper compilation/search work, review the next bounded hypothesis
with Dot and latest autonomous GitHub/Slack reviews, and forecast the cumulative
cost before more execution. Mixed/legacy optimization, NNUE expansion and the
old anchor/quiet/trace experiments remain deferred. Neither a new session nor a
new specification resets related experiment cost or missing frozen slots.

## Evidence and cost boundary

[Manifest](data/leaper_compiled_hash_20261026/manifest.json) binds lossless gzip
inputs/returns, failed and negative results, source blobs and plans. The source
ZIP contains text data only; never import or execute archived sources. Exact
private originals precede publication copies; personal path prefixes are excluded
from the latter. Factorial and quality pin Native binary SHA
`a2e1b0bae4e1e1910334572f862f347298da9d82546d18ec7563372016010208` (0.5.0).
The first fixed-work run did not pin its binary before entry; paired calls share
one loaded process and matching actual service counts. The first identity micro
pins its prototype/input, not the entire underlying Core module.

There are 181 study Player returns including invalid/partial studies; test
fixture searches are separate. At the scientific checkpoint the preserved
session contains 3716.610039 effective seconds in 446 intervals, of which
71.173026 seconds preceded this kernel work. No offline, waiting, transport or
report-writing time was credited. Scientific wall cost from the actual kernel
audit start is 74.877 minutes; full logical forecast is 100 minutes including
publication/communication. Delivery cost is recorded separately, without new
experiments. At the observed mean saving of about 0.435s/call, each additional
hour of engineering needs roughly 8,300 similar calls to amortize by time alone.

Publication intake: autonomous review `0aa20c8fd75a98416d29270aa090d26346ebda75`
was privately preserved and read in full before synchronization. It audits
45adda source only; its lack-of-new-results observation predates this study.
Its strict admission/whole-query/quality gates are adopted. It neither validates
these new measurements nor opens closed budgets or AUX work. Attack-union OR
cannot be undone by XOR; this prototype changes component hashing only.
