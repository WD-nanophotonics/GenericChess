# Existing Native services under pure-Leaper DEFAULT/PVS — 2026-10-25

Existing opt-in readonly availability and child-check services reduced this
registered matched-work query cost by **38.16%**, without changing the chosen
actions or reported scores. They did **not** repair the two known errors at a
real 1.5-second budget. This is useful scoped cost evidence, not a strength or
all-rule success claim. Product defaults, UI and AUX implementation are unchanged.

## What actually ran

The caller constructs `AlphaBetaPlayer` with no evaluator override, disk cache
OFF, `SearchTuning(use_pvs=True)`, ordinary Q4/hard8 and default root tactics.
The control uses the existing default Native legality only. The candidate adds
existing `use_native_semantic_availability=True` and
`use_native_semantic_check=True`. No DRAW cutoff, LMR or rule-clock cap is combined.
Core still owns complete rules, full GameRecord history, clocks, adjudication
and TT guards. No new backend or solver was built.

Eight complete histories (six known game rules plus p49/p53) first received
cold D3 qualification in three configurations: control, availability only,
availability plus check. All completed with identical action, score, legal PV,
main/q work and actual TT/PVS counters. Three deterministic cooperative-cancel
calls preserved the root and balanced runtime. Qualification took 27 returns.
Availability-only cost 0.742s, both 0.734s, control 1.100s across eight D3 calls;
this tiny diagnostic is not evidence of a reliable incremental check advantage.
The later candidate was fixed as both, not selected by a threshold sweep.

The main plan then froze 64 paired 1.5-second queries and 64 paired 50k-event
queries (30-second safety guard), followed by 24 two-second actual games on
six known rules, two complete starting histories each, colors exchanged. Arms
alternate within quality pairs; quality Players have separate cold TT, game
Players retain their own TT across moves. All 1,234 main returns were saved.
The 4,200-second batch closed at 3,536.438s; no slot/cap/tolerance was refilled.

## Quality and actual cost

| Endpoint | Control | Native availability + check |
|---|---:|---:|
| 1.5s source-WDL-correct choices | 62/64 | 62/64 |
| 1.5s query outer seconds | 93.631 | 93.217 |
| 1.5s main + q events | 388,089 | 671,193 |
| 50k source-WDL-correct choices | 64/64 | 64/64 |
| 50k query outer seconds | 839.615 | 519.211 |
| 50k main + q events | 3,021,084 | 3,021,084 |
| 50k time censors / fallback | 0 / 0 | 0 / 0 |

Both endpoints have zero WDL repairs and zero regressions. At 1.5s two choices
and 24 scores changed without changing attributed WDL. At 50k no actions or
scores changed. Four near-clock calls completed D64 before exhausting 50k;
p60 uses 12,186 events per arm, p62 uses 1,157. Events are budget visits, not
distinct states. At 1.5s each arm has 61 deadline-censored calls and no fallback.

p49 and p53 remain wrong DRAW choices at 1.5s: control D4, candidate D5. At
50k both reach D6 and select the source-proved WIN. Query costs are respectively
13.382→7.881s and 12.205→6.937s. More depth/work is not credited as a repair.
The 64 histories are exposed, correlated TRAIN data from one RuleSet; labels
are source attribution with current-Core action/full-history binding, not new
independent solving or an unknown-rule holdout.

All 64 matched-work quality roots belong to the `other_root` inventory stratum,
not two-anchor roots. Thus this cost result is not the root-only DRAW effect
from the previous experiment. That does not establish uniform cross-rule gain.

All 24 actual games end in Core rule DRAW. **17 games** are timing-eligible and
only **6/12 color pairs** have both games eligible. Eight over-tolerance calls
in seven games remain in the data. There are no game fallbacks. All candidate
queries: 490 / 979.484s / 5,868,333 events; control: 488 / 974.412s / 4,789,266.
Eligible subset: candidate 321 / 641.007s / 3,879,625 events, control
319 / 636.192s / 3,161,919. Trajectories and query counts differ; these aggregates
are not causal per-position speedups or independent Elo observations.

Actual other-root game queries cost 857.466s/429 candidate versus 854.355s/428
control; two-unpromoted-anchor roots 122.017s/61 versus 120.058s/60. Under fixed
wall budgets both mainly spend their allowance. Full-record strata and all
query/phase/service totals are in the assessment; none are inferred from names.

## Timing and provider boundaries

Quality row time includes fresh Player construction and choose_action, but not
module imports, Core record replay, final row serialization or PV validation.
Fresh construction is separately measured (50k total 0.193/0.186s). Game Players
are constructed before the game-loop timer; their initialization remains inside
the whole-batch receipt, not a fabricated per-game setup measurement. Game
service time additionally includes evidence append, work-ledger save and PV
replay. Search-reported time is a third clock.

For example a candidate service call takes 2.119896s while its row/search clocks
are 2.000101/2.000066s; another takes 2.300965s with row/search
2.262146/2.262106s. Recorder overhead explains some difference, not every
overshoot. Exact OS/kernel/GC shares are UNKNOWN. Existing fixed tolerance
remains; no invalid game is silently restored to eligibility.

Metrics are deltas on the actual execution thread and same provider. In the
50k candidate, availability performs 6,154,269 queries, all reusing the preceding
check input; check performs 6,154,269 imports/queries. Reuse does not eliminate
check's own import. At 1.5s availability calls/queries differ by 19 and in games
by 110 because entry polls can abort before a query. This is not an automatic
bug. Check only serves child gave_check; not every in_check becomes Native.
Counters include permitted root scans and TT-PV validation, not just expansion.
All actual admitted calls have zero availability declines. Missing exported
PlayerDecision fields were never interpreted as zero service use.

## Additional boundary checks and remaining-cost diagnosis

After the timing producer closed, 24 preregistered calls checked three actual
full-history near-clock roots (H64/96/128), independent same-player cold/warm
sequences and p49/p53 D4 cold/warm, plus cancellation followed by normal reuse.
All matched requested-depth actions/values/PV/work/TT behavior; roots and runtime
balance remain intact. They do not prove every history case. Existing product
tests separately cover required errors, post-query cancellation and one-use
handoff consumption. The boundary caller's stop-file polling was corrected to
250ms before its first call; no executed source or expected value was rewritten.

A separately frozen two-call diagnostic uses the first metadata-selected 6x6
p5 history at D5, both services enabled. Unprofiled/profiled calls preserve action,
score, PV, main/q and TT behavior. Cost 2.138→5.638s demonstrates substantial
observer perturbation; profile timings are not unbiased production fractions.
It records 28,184 runtime pushes, 8,472 q calls (6,606 recursive), and 20,694
noisy_child classifications, all from runtime qsearch. Therefore at least
14,088 classifications do not recurse; this is a count lower bound, not a
proportional cost or safe-skip certificate. Inclusive push cost 3.141s and q cost
4.710s overlap within a 5.171s profiled self-time total and must not be summed.

Source review **rejects the duplicate-push premise**: qsearch already keeps one
pushed child around classification and recursive search. noisy_child explicitly
includes every terminal child before quiet/check filtering. A noncapturing,
nonchecking move may still reach clock/repetition/stalemate; dropping such
children from parent-board geometry would change policy. No such screen was
implemented. Ordering/evaluation counters (6.259/23.383s against 519.022s search
at 50k) also do not justify adding another cache without a changed premise.

Next question: can a conservative pure-Leaper search-layer classification avoid
some complete pushes while preserving terminal inclusion? First measure tiny
per-site actual quiet/terminal/check/material outcomes and costs with full
behavior/work parity, then decide whether a sound prototype is worthwhile.
No AUX runtime edits, new backend, old trace refill, price/depth threshold fit
or mixed-rule expansion follows from this diagnostic.

## Cost, provenance and collaboration

The original Native logical-chain forecast was 100min; a retained amendment
adds a conservative 10min allowance for the previous source survey whose exact
isolated active cost is UNKNOWN. It was not zeroed by a new session. A later
checkpoint includes the remaining bounded diagnostics/review and remains below
120min; no Dot budget approval or session reset was used. The earlier closed
DRAW experiment is a different mechanism and retains its historical ledger.

Fresh start request GC-SLACK-20261025-181049-62d7ba8e was delivered against full
verified 2bbb5e303c89419455db890e7367951df20d4a2b. Solicited Dot reply
1792919653.784419 is source review, not independent execution. Adopted actual
provider deltas, warm/history/cancel boundaries and cost accounting. Dot correctly
noted existing runtime-handoff tests: this experiment is new DEFAULT/PVS/Q4
qualification, not the first runtime proof. Latest autonomous Chat root
1792912079.322259 was complete and unchanged at opening. One premature read
was preserved and explicitly NOT accepted as the delayed check; the actual
+5min check at 09:17:24UTC retained the new reply. Five minutes is not expiry.

The data-only reader replayed all 1,234 returns, 256 quality rows, complete game
prefixes/finals, 7,404 legal PV steps, WDL perspective, provider deltas and timing
eligibility. Lossless archives preserve source/input/plan/return bytes and hashes.
Source capsules were copied after closure, hash-matched against preregistered
main sources/receipts, and are DATA ONLY, not an independent original capture.
Private raw Slack/account wrappers and pstats paths are excluded from publication.

[Lossless evidence manifest](data/leaper_native_default_20261025/manifest.json).

Operational close: 40 targeted Native/handoff/terminal/Qsearch controls passed.
The scientific packet was published and full remote SHA independently verified
as 9fcbe14da416ba0411291ef2dfa75e9c8f9ea428 before the final Dot follow-up.
Session bbee209c-39ba-44c3-a6bf-e958b53565eb ended safe_checkpoint at
2026-10-25T10:30:59.301018+00:00 with 3773.622921999994 recorded effective
seconds (62.894min), 1287 ledger intervals, matching substantive quality JSON,
and accepted finish plus final-check. Wall81.559min was not substituted for
work. Five sub-resolution query intervals remain uncredited rather than using
perf_counter to invent UTC endpoints. The research objective remains open;
this is a completed bounded study and next executable question, not class success.
