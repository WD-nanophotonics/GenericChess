# Relative history in pure Leapers — prospective protocol 2026-10-27

Status: FROZEN before empirical dispatch. One new mechanism; the closed geometric
coverage assessment is not repeated, retimed or extended. Default OFF.

Question: does normalizing main-search cutoff history by actual action visits
improve equal-whole-service-time actual Core game outcomes against the same
current AB search? Current baseline records raw cutoff counts only.

Motivation: [Winands et al., The Relative History Heuristic](https://erikvanderwerf.tengen.nl/pubdown/relhis.pdf)
combines successful history with exploration frequency. Its measurements concern
LOA/Go tree efficiency, mainly at deeper searches, not Leaper strength. Our
query-local, main-only, smoothed version is an adaptation rather than a replication;
no published percentage is borrowed as an expected improvement.

## One variable and exact observations

Maintain independent unclipped S and A keyed by parent side and full semantic
action identity. A increments once after a main action successfully enters its
child context; scout and subsequent wide PVS search for the same parent-action
edge share that increment. S increments only on the existing final main beta
cutoff. Count ALL such main actions, including captures; only eligible quiet
actions consume these paired records. Different semantic target-empty/capture
patterns remain different keys. Current-node TT-only returns, generated-unvisited
moves, Q and root tactical probes add no synthetic credit. A real parent edge
whose child returns from TT still counts. Entered then aborted is exposure A,
not a confirmed negative observation; S is never fabricated. This ratio is a
ranking heuristic, not calibrated success probability or a credible interval.

Rank eligible quiet slots by (S+1)/(A+2), descending, stably preserving baseline
ties and all protected TT/capture/promotion/killer/counter indices. Legacy
history/killer updates remain identical; their clipped history is NOT used as
our numerator. Tables start fresh each query; no cross-query persistence,
depth weighting or parameter search. No Q use/pruning/eval/TT guard changes.
Only structural plain-Leaper IR admission, existing disabled-drop handling and
normal Core legality; fallback unsupported rules to baseline. OFF/Q do not
allocate or update the new sample tables. Geometry flag, staged picker,
countermove and other experimental switches OFF in both arms. PVS ON in both
is the explicit experimental reference; product default PVS remains unchanged.

Source inspection discovered runtime.state is a mutable view: save parent side
BEFORE push. Behavioral tests instrument real main recursion and prove that
multiple scout/wide child entries produce one parent-action opportunity; cutoff
keys have prior opportunities. Other controls cover low-frequency normalization,
semantic identities/duplicates, protected slots, Q/default/unsupported and reset.
The source-only v1 40game/20rule proposal was revised to24games BEFORE any empirical
dispatch following Dot's cost advice; the exact old private plan is retained.

## Inputs, endpoints and fixed caps

Six old4x4/H128/repeat4 rules: preserve negative controls worlds5/8 plus4chosen
from the other8 by seed202610271151. Six new canonical D4orbit-mask pairs sampled
without outcome selection from1..31, excluding the original ten pairs, with the
same frozen seed. New rules have unplayed outcomes but geometry metadata may
have been exposed; do not call this a fully blind independent-rule holdout.
Interleave old/new roots, then two colors per root, alternating color order.
All complete RuleSets/GameRecords/fingerprints frozen before queries; no H96
substitution or selective-prefix/eligibility refill. Natural Core adjudication
and complete history remain authoritative.

First24paired D2/2s/500k/Q4hard8 semantic qualifiers (one ON/OFF per12roots),
fresh Player/TT per call, all requested Native legality/availability/check ON,
disk OFF. Require completed depth, equal paired values, legal action/PV, unchanged
query state, balanced runtime and no provider failures/fallback. Any failed slot
halts dispatch; missing planned slots remain explicit. This is not a cost gate:
CPU zeros retain UNKNOWN, not approval failure or a reason to rerun old calls.

Only then24near-baseline games, same controls and one ON/OFF color pair per root.
Per actor fresh Player per game, TT retained within actor only. One-second service
clock begins before full-record packing/first Player construction, feeds remaining
time plus original cancellation deadline, ends after decision packing. Separate
compile/replay/persistence/PV validation and total costs. Requested D64/500k total
main+Q nodes/Q4hard8; no rule-clock cap, early-win option or relaxed2nd second.
Cooperative overshoot>10percent is a failure, not exactly-one-second billing.
No random opponent: the comparator is the same current AB without normalization.

Freeze actual loaded Native module file hash BEFORE any queries and verify each
new Player's backend against it. Save executed Python source, binary/CPU/timing,
full game traces and original returns before checks. Process RSS/peak are totals,
not attributable per-arm allocations; table-entry counts are distinct from bytes.
Persist failed calls/ONGOING/NOT_STARTED/NOT_RUN, never relabel them draws.

A65minute game batch includes setup/call/record overhead and2s in-flight reserve;
24*128*1s=51.2min nominal service ceiling leaves overhead reserve, not a promise
of completion. Whole independent run105min forecast,110min cap from
02:47:33.917952UTC,15min reserved for analysis/delivery. Includes preparation,
implementation/tests, qualifiers, games and delivery; no historical-task sum.
Single-run <120min standing grant applies, no new approval queue. Stop on scoped
stop, contract failure, batch or whole reserve; no seed/prefix/cap refill.

Report all24fixed slots, old/new strata and per-rule color pairs, actual Core
W/D/L, final-record terminal reason, work/depth/Q/TT, actual reordering and costs.
For missing outcomes give best/worst completion bounds on the fixed denominator.
A continuation signal needs all12prospective games qualified/terminal, net wins
positive across that stratum,>=3prospective rules positive and<=1negative. This
operational small-panel screen is not statistical significance or class-wide/Elo
proof. All draws/no exposure/no signal ends this candidate without adding slots.
Even a pass only motivates separately chosen future work, not default activation.

## Communication and roles

Latest remote e0c4ec99 review tree and covered Slack autonomous/own threads unchanged.
New opening AGENT_REQUEST12c8aaed/root1793069332.300999 sent02:48:52.300999UTC
from published/fullSHA checkpoint. First complete readback occurred after+5min
(~02:54UTC), also the single delayed reply check, not an instant read substituted
for it. Dot1793069550 source-only advice read/adopted: unclipped counters, parent
edge/TT/abort semantics and pre-execution24slot revision. No repeated poll.
No source treats Dot as user budget authority. No AUX task/state/checkout,
worker/fee/schedule or mixed-rule/default extension.

## Pre-dispatch autonomous review received during publication

Publisher found new sandbox a6823de1/Patrol2026-10-27_115659_JST_e0c4ec9.md;
exact16028bytes privately saved/read before empirical dispatch. Its inspected
snapshot predates this relative-history protocol. Adopt: close old geometric
CPU repair, actual quality/near-strength opponents,>=3new rule classes, explicit
complete histories and actual terminal/missing outcomes;no fused-Native rewrite
or LMR/source-label patch without a concrete causal premise. This protocol has
6prospective unplayed outcome rules, fixed current AB opponent and24color games.
Current resolution still UNKNOWN, not asserted prequalified;all-draw/no signal
will be retained. A source filter cannot guarantee future decisive quality;the
small exploratory trial answers that uncertainty rather than preselecting wins.
The review's own lack of an execution grant is not a new user-approval gate:
latest USER permits independent single-run<120min work, and this full run remains
105forecast/110cap. No historical minutes or reviewer suggestion creates extra
permission. Its recommended Native-cost alternative is deferred this round to
avoid two mechanisms. Review-reported external AUXpause is not direct local
USER authority;no AUX/state/schedule action is taken.
