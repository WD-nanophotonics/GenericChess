# Practical ABP search cost and exact-map optimization — 2026-10-24

PRIMARY_SANDBOX; control base `86c3fa4b1349943b1cc3752ac8922825569f7dee`.
The production change is ONE Python Core function: RuntimeCountsSnapshot.items
now applies persistent updates once and sorts once, preserving exact output.
No key/hash/history/clock component, search tree policy, Native kernel, API,
pruning, learning, UI or default option is changed. Experiments separately test
existing opt-in flags; those flags remain off by default.

## Decision and achieved result

Adopt the practical-search direction in
[Chat1792834286](https://nanomelon.slack.com/archives/C0C6L21UU20/p1792834286090719),
under the user's prior direction to use latest Chat guidance and continuing
project authorization. This replaces the automatic P0/P1/B1 geometry queue.
The remote claim that AUX is paused is not independently verified or acted on;
no AUX checkout/state/schedule was touched, requested or used as a new service.
[Claude1792838901](https://nanomelon.slack.com/archives/C0C6L21UU20/p1792838901674919)
withdraws Position-only TT advice; exact history remains mandatory.

The safe representation optimization materially reduces cost on some small
searches, but scarcely helps the larger existing legacy-compiled benchmark
positions. Eight eligible same-wall games yield **2 candidate wins,2 losses,
4 rule draws**, mirrored by seat: no demonstrated game-result gain. An independent
existing Native availability flag reduces costs on its qualified semantic inputs;
it does not accelerate the unchanged legacy API and is not activated globally.
No amateur-human strength, general Elo or universal speed result is established.

## Complete inputs, backend and accounting

The [packet](data/search_performance_20261024/README.md) retains eight complete
RuleSet/GameRecord inputs: a certified n3H6 Leaper root and its one-defense child;
a six-actor n4 rule with fresh/3ply prefixes; an existing board6 promotion/drop
fixture with fresh/6ply histories; existing DEFAULT_SUITE classic6_ply16 seed7
and classic8_ply24 seed42. All complete rules, role, clocks, repetition and hands
are preserved. Standard-suite rules are generated variants, not standard chess.
The two certified records have known WDL; other input WDL/best-action truth is
UNKNOWN. Repeated known-score checks do not create137 independent labels.

Small inputs use the established explicit semantic lowering. DEFAULT_SUITE uses
its existing public compile_ruleset route. We preserved both APIs and their
actual action/history representations: opt-in legacy-to-semantic lowering is
not a one-to-one action adapter and old history-key strings cannot be copied.
Actual Native legality calls are present on the semantic inputs and0 on these
legacy-compiled standard inputs. The latter is a routing boundary, not proof
that the installed Native kernel cannot support their rules.

Leaf evaluation is the unchanged rule-derived generic-v5 profile. All pair arms
use identical full inputs/evaluator/Q policy/TT lifecycle. Main+q visits are the
node budget; Runtime pushes, legality trials and replay work are different counts.
Cold TT is reset per decision; same-player Native action-conversion caches remain.
ABBA balances order but is not a fully cold-process experiment. Profile/setup
cost is separately retained where measured; transfer receipts include residual
setup/recording overhead without falsely labeling it search time.
Python3.12/Windows and actual Native0.5.0 binary hash are in environment.json;
this was observed after start, not a claim of frozen hardware or measured load.
Concurrent load is unmeasured. No unrelated process monitoring/quiet window.

The current public reader validates **714 retained decisions,3286 legal PV
plies,156 map/transfer pairs,32 availability pairs and all8 final records**.
Actual opt-in Native availability queries total2478812. Data-only qualification
executes no Player or frozen source text. Initial3 and later6 instrumented queries
are counted separately from ordinary timing comparisons. Pytest calls are not
added to the experimental search-call count.

## Baseline and first existing switch

Reuse existing benchmark suite, play_game/RunConfig, core_function_timings,
SearchStatistics, TimingAuditRecorder and cProfile. Baseline controls use D2/D3,
512/4096 total-node caps and0.5/2second limits on six complete inputs; standalone
same-player warm-depth2 probes are marked separately. All decisions/counters,
root values, PVs, fallbacks and stop reasons remain in the raw streams.

The initial measured ordering cost was about5% on one six-actor sample. A single
staged-picker pilot preserves all12 completed fixed-depth root scores but shows
mixed timing effects. It is not activated. Fixed depth permits equal-valued best-
move changes; neither PV equality nor random-opponent victories define strength.
The measured larger cost suggested the single exact-map change below.

## One exact-map hot-path change

The old items() recursively copied and sorted each ancestor's whole map. Exact
TT equality after matching digests can legitimately invoke it even without a
hash collision. The new method walks the parent chain, copies the root map,
applies the SAME updates oldest-first (including deletions), then uses the SAME
canonical sort. Digest hashing and exact equality/collision guards are unchanged.
No persistent cache or discarded-history projection is introduced.

Induction on the update chain gives the same map; canonical ordering remains.
Tests cover deletion/reinsertion, sibling independence, order-independent equal
maps, forced equal digests with unequal exact keys/counts, long realistic chains
and null-key frames. Existing typed auxiliary/history/clock/PV/promotion/drop
regressions remain. This is exact-map reasoning and finite engine validation,
not a claim to have tested the entire generated game domain.

Four paired timing repeats use AB,BA,BA,AB order per case/Q/control. Both arms
have same full input, cold TT and actual old/new items implementation. Node and
completed-depth calls compare score,PV,main/q counts,TT probes/hits/cutoffs,
beta cutoffs and runtime push/pop work whenever not time-truncated.
Wall-time arms compare achieved work/depth separately.

Median seconds at the65536 node cap (solved controls finish early at D64):

| input | Q | actual work | old s | new s | time reduction |
|---|---:|---:|---:|---:|---:|
|promo6_0|0|65536|10.672|9.237|13.5%|
|promo6_0|4|65536|13.529|13.519|0.1%|
|promo6_1|0|65536|12.675|8.816|30.4%|
|promo6_1|4|65536|13.810|11.182|19.0%|
|six4_0|0|65536|18.028|11.067|38.6%|
|six4_0|4|65536|14.319|11.921|16.7%|
|six4_1|0|65536|23.144|11.714|49.4%|
|six4_1|4|65536|13.465|10.929|18.8%|
|solved3_0|0|5900|1.573|1.158|26.3%|
|solved3_0|4|6065|1.609|1.186|26.3%|
|solved3_1|0|1422|0.317|0.254|20.0%|
|solved3_1|4|1451|0.325|0.255|21.5%|

D64 on the H6 solved controls is redundant iterative work, not64ply strategic
coverage. The known win is already found at completed D3. The promotion-root Q4
negative result is important:97.9% qnodes and almost no map speed gain.

## Transfer to actual standard-suite paths: negative/UNKNOWN boundaries

Legacy classic6_ply16 reaches D2 and stops with qsearch_check_hard_limit (8),
40712 visits, about20.6seconds in both versions. Requested D3 is not completed.
Legacy classic8_ply24 completes D3 with43436 visits in about47seconds. Its explicit
65536-node arm reaches the unchanged60second safety cap at about54k visits;
that planned matched-node condition remains unmet, not silently repaired by a
larger cap or different denominator. Both8second arms retain only D1. There is
no material practical speed gain here and no exact larger-root WDL claim.

## At most three observed bottlenecks

1. **Q work and uncounted trial pushes.** Default Q4 dominates the standard
   roots (about97–99% qnodes). Full classic6/8 depth probes have119467/339198
   runtime pushes for40712/43436 visits. Node counts alone understate work.
   The live runtime already classifies on demand and reuses each pushed child;
   the eager helper is a reference, not the executed path. No eager-to-lazy rewrite
   is justified by reading that unused helper.
2. **Physical legal-availability/attack checks per pushed child.** In independent
  8192-node cProfile samples, semantic promotion has1.476s in has_legal_action
   within4.295s; legacy classic8 has8.672s there within25.799s and14.161s cumulative
   legal-action iteration. Timings are nested and profiler-affected: do not add
   them as disjoint fractions or compare them to uninstrumented speed.
3. **Exact repetition-map materialization where TT matches recur.** This is the
   measured and fixed hotspot in the smaller/deeper cases; it is tiny in the
   q-heavy standard samples, so further TT simplification is not the main cure.
   Incremental runtime hashing already exists; no per-child external-SHA story
   or Position-only score reuse is inferred.

## Independent existing Native availability probe

After those measurements closed, one new bounded probe enables ONLY
use_native_semantic_availability on four existing full semantic records. Current
iterative map and all other options are identical in both arms. Native check
remains off; Core owns histories, clocks and adjudication. Actual boolean query
counts are recorded, not inferred from provider availability. Four ABBA repeats,
same65536-node /8second controls, original total deadline.

| input | Core availability s | Native availability s | reduction |
|---|---:|---:|---:|
|promo6_0|13.422|9.678|27.9%|
|promo6_1|11.085|9.464|14.6%|
|six4_1|10.851|8.409|22.5%|
|solved3_0|1.157|0.785|32.2%|

All qualified fixed-work values/PVs/work remain equal. Packing/import costs are
included in search time. This is a supported semantic-input result only; the
public legacy API is not silently lowered and the default flag remainsFalse.
The rough1.52x forecast came from an instrumented sample, not a universal bound.
Existing Native opt-in/check-handoff guards add22 passing headless checks,
including chess/shogi promotion/drop and short cutoff decline cases.

## Same-wall games and limits

The existing play_game runner uses2seconds per move, normal Q4/hard8, persistent
TT per player within a game, fresh players per game, both candidate seats. Eight
registered games use four exposed prefixes from three rule families (two prefixes
share one family). These are correlated engineering cases, not IID openings.
Four repetition draws, four checkmates, no caller truncation/fallback/timing-
invalid exclusion; all8 final records replay. Candidate2W2L4D is seat-symmetric.
This compares the map implementation change, NOT the later availability flag.
Do not multiply the two experiments' speed ratios or attribute game results to
the availability option. No trusted opponent ladder/human test was performed.

## Failure, budget and provenance record

Initial preparation incorrectly used default setup instead of the named solved
GameRecord: zero search calls, corrected to strict replay. Two compressed
conditional-expression syntax errors were caught before query execution. A real
caller error treated GameRecord.actions as ActionRecords: two valid games were
retained, then the six unstarted games continued with the correct Action tuple
under the SAME original schedule/caps. No completed episode was rerun and the
stopped-process gap is excluded from effective work. Scientific expected values
were not edited to match output.

Early baseline/candidate row started_at was emitted after choose_action and must
be read as a completion marker; wall/cpu durations and phase receipts are valid.
Original streams and source capture remain exact. Future caller metadata is
corrected before/after the query, without rerunning old measurements.

The original inclusive experiment deadline is12:41:29UTC,100minutes after plan
start, including preparation, code, recording, validation and analysis. All
scientific producers closed at12:17:43UTC; no frozen cap/refill or renamed long
history study. Recorded effective work is3819.541326seconds (63.659minutes),
14intervals. Prior/offline/failed-job gaps and later documentation/Git/Slack are
not credited. Current exact quality/source evidence is independently scoped;
no old history-line cap or completion claim is revived.

Public evidence includes exact compressed project records/source text, LF JSON
presentation and explicit sanitized copies of two profiles. Automatic review
initially refused an uninspected bulk export. Per-file decoded inspection then
identified personal path prefixes only in those profiles; publication copies
remove them while private originals remain. The53-file reviewed hash allowlist
was accepted; no enforcement bypass or public account/credential output.

## Next useful step actually begun

next-legacy-probe.json preserves both complete standard-suite inputs,0 new Core/
Player calls. Existing adapter entrypoint inventory was inspected: packing,
full legal actions and terminal helpers exist; a cheap boolean path or support
is not assumed. Read those implementations and choose ONE supported readonly
physical-predicate/attack-cost probe, or retain explicit Core decline. Predict
benefit only after total payload/import cost; stop on legal/terminal/history/
clock mismatch or inadequate cost case. Do not silently lower legacy action/
history representation, change qtree/defaults or start a broad architecture job.
B1/colorbound geometry, inverse, material TD and NNUE remain preserved reserves.
