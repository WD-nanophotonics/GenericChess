# Pure-Leaper quality decision: PVS OFF versus ON - 2026-10-26

Decision: **NO-GO for further profiling, default activation or a strength claim.**
A bounded exploratory equal-time PVS ablation is technically specifiable, but
its decision-quality resolution is UNKNOWN. Execution is **NOT_STARTED** and
requires a new cumulative necessity assessment. This is a proposal, not a grant
or an instruction to repeat the deferred 16-game Native-service experiment.

## What changed the decision

The closed [cost diagnostic](LEAPER_COST_ATTRIBUTION_20261026.md) localized an
inclusive push consumer: observed 56.06% of wall in ten qualified D8 trios,
with median observer/control ratio 1.00936. It did not identify a removable
56.06% share or a useful optimized implementation. More profiling cannot repair
the missing quality comparison. The nominal batch overrun and final conservative
whole-chain upper 200.369 minutes versus the granted 200 remain failures of the
cost boundary; a new session does not erase them.

The autonomous Patrol review at sandbox 68f83ff02067b7d557b12eb1438e066504bfa192
recommended this GO/NO-GO decision before further work. Its review snapshot
predated the completed diagnostic and did not contain the user's later direct
approval. We adopt its next-step priority without retroactively calling the
completed approved diagnostic execution of that review. Fresh opening fetch
resolved sandbox f1e6ca1576af1801883d48a686d2b51a100bc7e5; Patrol blobs are unchanged.
The two known autonomous Slack threads are unchanged. The new AUX source-bound
milestone was read as its own report; PRIMARY neither reran nor reassigned that
work. The new-round Dot request and single delayed check are privately retained;
no reply had arrived at that check. A reply is not an execution gate.

## New source and saved-data examination

Product SearchTuning.use_pvs defaults FALSE. Both sides of the prior 24-game
2-second/0.5-second resource curve explicitly used TRUE, as did the earlier
fixed-depth root-order trials. Therefore none isolates the OFF/ON causal effect.
That curve is evidence about two resource policies with PVS already enabled,
not the product baseline versus PVS. The optional Native availability/check
services used there also differ from the desktop baseline; keep them identical
in any new ablation and name the baseline accurately.

In current search.py, after the first ordered main child, PVS searches a null
window and re-searches a child only when alpha < null_score < beta. Q search
has no equivalent PVS switch. Exact TT/history/clock guards and all Q action
classification remain. Scout/re-search work can help or hurt cost; its counters
cannot establish quality. TT/PV returns and the retained complete iteration or
completed-root-win/fallback must retain their actual provenance. Equal-depth
scores can be qualified; equal-time depth and action changes are not WDL truth.

A fresh, zero-Player one-step Core examination of ALL twelve existing h2 roots
finds 118 legal actions in total, all leading to nonterminal children, with no
immediate root win. Per-root legal counts are 13,5,8,5,17,10,12,5,2,10,16,15 in
the original metadata order. This provides at least two live alternatives in
each of six movement families across two board sizes. It establishes an
opportunity for the algorithm to operate, **not** distinct minimax action values
or an unsaturated quality endpoint. No solver, new game or Player ran here.

The old actual outcomes still have decisive results in only family4; five
families are draw-only under that particular resource contrast. This neither
proves those games intrinsically drawn nor predicts OFF/ON outcomes. Selecting
family4 alone would condition on old results. We therefore cannot presently
certify a quality-discriminating set of three families. We also cannot infer
that a prospective trial must be useless merely because this different old
contrast drew. Both uncertainties enter the necessity decision.

SearchLimits.deterministic is documented as unused compatibility metadata.
There is no consumed search RNG seed to freeze in this controller. A protocol
must state this rather than inventing a seed guarantee. Existing roots and their
two-ply preludes are deterministic, fully serialized, already exposed development
inputs. Six families are clusters; board variants and swapped-seat games are
correlated, not 24 independent rule samples or a heldout population.

## One concrete optional pilot, not yet executable

Question: at the SAME nominal whole-call time, does existing PVS ON produce an
observable relative-play signal against OFF on the full unselected development
population, or is this endpoint too draw-dominated to justify further expense?
The primary goal would be endpoint/algorithm discrimination, not deployment.

Inputs: exactly the twelve prefix_length=2 roots of the published prepared-v2
packet, all six families and both board sizes, full RuleSet fingerprint and
complete GameRecord, max-ply 96 and repetition 4 unchanged. Freeze input bytes,
all source hashes and the literal full records before dispatch. No old H6/H64
labels, p49/p53 selection, family filtering, new geometry census or AUX solver.
The source manifest and this examination table bind the candidate inputs.

Arms: original AlphaBetaPlayer with DEFAULT evaluator/disk cache OFF and identical
Native legality/availability/check requests TRUE; ONLY use_pvs differs. All
other tuning defaults, Q4/hard8, max depth64, max nodes500000, no rule-clock cap,
no stop-after-root-win. A new Player/TT per seat per game; retain that policy's
TT across its own moves. No cross-arm TT sharing or midgame tuning changes.
Check actual Native acceptance/fallback counters, not just requested flags.

Schedule: twelve full roots in frozen metadata order; two games per root with
ON assigned once to each seat, reversing which seat-assignment runs first on
alternating roots. Both sides get nominal 1.0 seconds per turn, not 2s versus
0.5s. The opponent is explicitly the OFF version of the same engine; it is not
an independent opponent population. No consumed random seed; no stochastic
replicates are implied. Preserve all planned 24 slots even if stopped.

Before any games, qualify both arms at a predeclared shallow complete depth on
all twelve roots, with fresh TT, unchanged root, legal action/PV and finite
scores. Preserve equal-depth score mismatches and stop for diagnosis; do not
patch an expectation to current output. Do not demand equal nodes or identical
tie action/PV across algorithms. A timed-out qualifier is incomplete, not parity.
The proposed qualification is24calls (12roots x2arms), depth3,50k nodes and3s/call,90s batch including in-flight reserve; these limits must be frozen with the admitted driver before dispatch.

Whole-call timing: the product creates its internal deadline inside root search,
so a max_time_seconds argument alone is not a strict outer service deadline.
Use the same caller deadline token beginning immediately before choose_action
in BOTH arms, with internal 1s limit and actual outer wall/CPU recorded. The
cooperative fallback/atomic operation may still overrun. Keep actual reason,
call wall and complete-iteration source; no wrapping an abort as an exact value.
Construction/replay/validation/recording are separately measured and charged to
total cost, never hidden in a speed percentage. No per-arm profiler/observer.

Predeclare timing qualification outer wall <=1.1s. Report all actual outcomes and
complete timing-qualified seat pairs separately; preserve raw failures, partial
games and overdue calls. A qualifying subset is descriptive, not an unbiased
repair for censoring. A stricter exact-time equality claim would be unsupported.
No missing/unfinished game becomes a draw, resignation or loss. A Core terminal
gives literal W/D/L; external stop does not. All complete legal actions and PVs
are saved and replayed without new search before interpretation.

Endpoint: ON score per swapped-seat rule pair and per family, separately for
all actual terminals and fully timing-qualified pairs. Give fixed-denominator
bounds [0,1] for missing game scores rather than dropping them. Also show
terminal reasons, fallbacks, query counts, actual Native use and whole service
cost. Do not use depth/score/PV or AUX partial labels as policy strength.

Decision after the one frozen pilot: a directional signal would need positive
pair score above half in at least three different families, with no suppressed
negative family or missing-slot ambiguity; even then it only justifies assessing
a NEW prospective independent confirmation. It is not significance, Elo,
class-wide improvement or default acceptance. Draw-only, one-family-only,
unstable/censored or negative results mean NO-GO for further PVS work on this
panel at this budget, without seed/time/threshold sweeps or refilling slots.
No automatic follow-on experiment is part of this proposal.

Resource bound to freeze before dispatch: at most24 games,94 turns/game and
2256 actual game calls, plus a separately bounded shallow qualification. At1s
this is37.6 minutes of nominal game search at most; 10% timing tolerance is not
a guaranteed process limit. A 45-minute compute/recording reservation includes
in-flight reserve. Do not start a new call when that reserve cannot fit before
the dispatch deadline. Stop flags/cancel remain live; retain partial output on
any recorder/semantic failure. Cooperative overruns are recorded, never renamed
strict-cap compliance. A watchdog/extra worker or product patch is not authorized.

## Opportunity cost and decision required

The already closed related chain is conservatively200.369whole minutes, not a
fresh zero. Source/design work in this round, including intake and delivery, is
additional cost. Conservative extension forecast is90-110whole minutes for
this design, qualification engineering, <=45-minute game reservation, analysis,
validation and publication; cumulative forecast approximately290-310minutes.
Proposed cumulative ceiling320minutes includes a reserve, not permission to
spend it. Actual preparation and elapsed delivery must be reconciled before any
dispatch; if the forecast no longer fits, do not start. Token cost UNKNOWN.
No increment is credited as effective research unless actually recorded.

This exceeds the >=120-minute user necessity threshold. The earlier approval
was for the bounded COST diagnostic, not this algorithm/game pilot. The old
16-game Native-service request remains CLOSED/DEFERRED. The present choice is
whether the different exploratory PVS question is worth its cost despite weak
expected outcome resolution; no execution grant is presumed.

Alternatives considered: more profiling has no new concrete removable consumer
and is NO-GO; lexical-Q key reuse could preserve ordering only with complete
semantic action identity, unchanged stable string ties and bounded ownership,
but no whole-query benefit or quality consequence is established. Replacing
lexical keys with numeric coordinates could change traversal and is rejected.
A new cache implementation would be another unmeasured experiment, not a free
way around the cumulative necessity assessment. Existing static evidence stays
available, no generic proof infrastructure or AUX task is added.

A user deferral closes this proposal without repeated approval requests. A user
grant would permit only the stated exploratory design, not a claim of success,
new samples, extra runtime, product activation or mixed-rule expansion.
