# Cancellation, transport cost and existing q4 scheduling

Science remains OPEN. This segment answers the previous memo's concrete
cancellation question, then compares existing algorithms under the changed
low-cost q caller. No product/default/UI/private-iterator API changes occur.
Source/result bindings and failures are in data/cancel_q_scheduling_20261012.json.
The base is5783a3d659e66a34f20031952172ca087d6c1fb7. Prior cost/cap records remain
immutable; these exposed roots do not become new holdouts.

## Full logical collection cancellation

The existing research BatchLegal collection keeps every S0-S2 candidate,
validates current-position S3/S4 in bounded Native chunks, and binds accepted
actions with Core. It holds no cached child or history. On EP, temporary
auxiliary creation/expiry and nested pawn-drop legality, six direct cells
cancel after one completed chunk, retry full enumeration, compare exact eager
membership/bindings and every full Core child, then cancel a push and retry.
Full position/ply/terminal/identity/hash/counts/history/aliases restore.
Two chunk8 cells have fewer than eight candidates and cannot reach a second
chunk; they are explicit exclusions. The original assertion assuming they could
is preserved with its source/failure, not renamed an engine defect.

Actual AlphaBetaPlayer/CancellationToken tests contain45 TT0 and45 TT-on rows:
each has25 actual cancelled returns, two unreached S4 target8 cases, nine
completed baselines and nine same-player retries. Cancellation is injected after
Native chunk completion at predeclared1/2/8 calls, with chunks1/8/32. The return
matches the last successful root negamax result from that SAME call, or the
existing legal root-scan fallback when no iteration completed. All root caches,
bindings and full Core state restore; no partial new iteration is advertised.
Original cross-call warm-TT/depth oracle assertion is retained; it does not
establish corruption of cancellation state. TT0 retries match the cold complete
D2 action/score/PV. TT-on retries retain action/value, but two S4 retries after
UNREACHED cancellation already completed D2 and later return an empty warm PV.
The existing default require_full_pv=False exact-TT return deliberately omits
the line. Six unmodified S4 cold/warm calls clarify that contract: False gives
PV lengths2/0/0; True gives2/2/2, allD2/value0/legal same action. This is not
cancellation corruption or a reason to add another guard. Do not claim identical
cold/warm PV without the existing explicit flag.

The research cache representation is still a prototype: ordinary Core
legal_actions advertises a tuple, whereas this injected q collection is a
logical iterable. Actual q consumers can use it, but product adoption would
require an explicit consumer/contract, including public tuple materialization
and root fallback checkpoint behavior. These finite tests alone do not justify
that interface work. No partial-prefix list is substituted for logical legality.

## Optional q0 root extension

Twenty completed existing Native q0 cells cover nested S4 atD1-3 and standard
Shogi drops atD1-2, TT0/1, full versus corrected optional root windows. Complete
canonical action/PV/value and independently searched selected-child value agree;
full Native snapshots restore. S4 values are all0 and refinements0: this tests
nested legality and current mode compatibility, not an actual S4 tie-refinement
trigger. The Shogi-drop fullD3 call fails the original complete-depth assertion
under max1Mnodes/30s. Its return metrics were not saved before the assertion,
so the exact stop reason is unknown. Preserve the20 saved rows and original
failed source/log; do not extend the cap or claim24 completed rows. C remainsq0.

## Measured remaining caller costs

One cProfile run of active1091 completesD2/q4, main247/q25265, score-2416,
in21.116s. Inclusive costs overlap: Core push5.098s, quiet exclusion4.999s,
logical collection construction3.832s, evaluation3.283s.9265 collections produce
1043409 raw candidates; Native subset totals0.572s. Formatting/hashing are
visible, but profiling overhead and nested costs prevent additive savings or
pure compiled-language attribution.

A motivated four-call lexical-text reuse check preserves the full D2 decision,
main/q counts and root. Text reuse costs8.338/8.311s versus8.568/8.582s,
ratios0.973/0.968. The extra2048-entry per-provider research text dictionary
caches immutable syntax only, never legality/child/history/current bindings.
Defer product caching: about3% on one exposed root does not change the next
choice enough to warrant another integration.

The24-call predeclared active1091 chunk1/8/32 curve uses1/16/64/256s,
maxD12/1Mnodes/q4/hard8/PVS, reversed arm orders, the same lexical q order,
Core authority, Native evaluator/legality/availability and quiet guards.
All24 rows finish normally at the stated time limit. Each chunk size returns
D1/ordinaryq0 at1s, D2/q4 at16s andD3/q4 at64/256s, with the same retained
per-budget value in both orders. No additional completed support results.
Six completeD2 controls preserve exact action/PV/value/main247/q25265.
Chunk1 checks192134 candidates, chunk8 checks226983, chunk32 checks392028;
accepted bindings are71233/76980/92621. Costs are8.935/8.985,8.587/8.632
and8.962/8.995s respectively. Fewer checks at1 do not compensate for more
Native calls; extra prefill at32 costs more. Keep8 for this research caller.
Maximum sampled Native times are0.000381/0.000680/0.001688s for1/8/32.
Observed maximum Native-call times are sample maxima, not domain-wide latency
bounds. A Native chunk has no Python checkpoint inside it; caller budget checks
remain cooperative. Timed wrappers add common call overhead. Ordinary concurrent
load is reported without claiming exclusivity or noise-free speedups.

## Existing PVS versus ordinary alpha-beta

Dot's new request reply selects existing Core q4 algorithm controls before a
formal private iterable interface. Adopt one substantive objection: these
algorithm arms SHOULD have different work counts. Compare complete values and
legal selections, then report null windows/re-search, candidates, leaf cost and
actual budget completion. Equal main/q counts are not a validity requirement.
All claims about this segment are based on our evidence supplied in the message;
Dot did not independently execute or inspect the new unpublished results.

The actual switch is existing SearchTuning(use_pvs=False/True). Both arms keep
same leaf/rules/q inclusion/hard8/lexical q/default main ordering, fixedchunk8,
quiet guards and a fresh default TT per call. No algorithm is manufactured for
the control. Existing PVS results on older cohorts remain historical evidence;
this changed active/default auxiliary caller has no equivalent frozen control.

Eight completeD2 controls preserve value, canonical action and PV. On1091
PVS has247main/25265q versus AB164main/45485q;229null windows and5
re-searches, costs8.58/8.57 versus15.06/15.14s, ratios0.570/0.566.
On1090 PVS has1727main/33120q versus AB1349main/100486q;1541null
windows and11re-searches, costs16.47/16.59 versus50.96/51.63s, ratios
0.323/0.321. Fewer expensive q nodes compensate for additional main work.
These full values are-2416 and-3641 respectively, not stronger-play evidence.
The16-call1091 delivery curve confirms an actual completed-support difference:
at64s PVS completesD3/q4/value-230 while AB retainsD2/q4/value-2416, in both
arm orders. At1s both retainD1/q0/value9, at16s bothD2/q4/-2416, and at256s
bothD3/q4/-230. All stop at the declared time limit; no cap was enlarged.
This is a finite algorithm/caller delivery result, not stronger-play evidence.
Hard-q/budget stops describe retained completed iterations; unfinished scores
cannot become a shared reference. Different same-value ties/PV are explained
under current selection rules, never renamed stronger moves. No games/Elo,
human-price fitting, cap extension, new C q4 kernel or product policy change.

## Choice and reproducibility limits

Finish the declared controls, then choose one mainline question based on actual
work and useful delivery. Retain the Native primitive and finite research q
consumer. Do not continue microscopic comparisons merely to chase small gains;
a formal interface needs an actual product consumer. Profile results are costs
of this caller, not an exhaustive proof that all generated rules are covered.

All producers, declarations, complete/partial JSON, failed versions and source
hashes are archived. Python stdout host paths remain private; structured
Agent-only failure summaries are published. Raw Slack/account/user/private
inputs, binaries and profiler binary records are excluded. Tests/publication
are recorded after completed evidence review, with exact remote SHA verification.
