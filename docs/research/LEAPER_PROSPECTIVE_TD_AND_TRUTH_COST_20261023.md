# Prospective batch-TD play, tie refinement and truth costs

On 32 frozen new prefixes, the Unit-initialized batch-TD endpoint improves
signed utility by4/64 over Unit and1/64 over both free priors. The latter is
one role1 LOSS-to-DRAW conversion. B2C1 matches its final WDL on every frame.
Mobility-initialized TD changes seven paths but no final outcome. These are
finite exposed-rule results, not an independent-rule learning success or a
reason to expand training.

## Inputs and executed policy

The rules are the eight older ABC worlds from sandbox
`55abf3de22f20ac03eb07b5260284466173a3264`. Their ordinary A/B/C movement
sets are pairwise distinct in every world; the newer `(9,9,8)` alias example
is a different cohort. Existing fit/validation results remain CLOSED.

The32 prospective prefixes were frozen before this segment: four per world,
seed830431, uniform legal prefixes of at most eight plies, with no outcome,
response or oracle filter. Their initial full-history overlap with the64 fit
prefixes is zero. One already-terminal prefix remains, contributing12 views.
Rules and earlier model-selection results are exposed; new prefixes do not
make independent held-out rules. The62 distinct final records are descriptive,
not62 independent samples. Both roles share the same prefix draw.

All six models and the execution order were fixed before play. Each actor uses
D4/q0,8192 nodes,2 seconds, a fresh Player/TT per query and equal capture
ordering. The opponent is the same fixed mobility D4 policy. Actual repeat4
and rule max_ply128 remain authoritative; no caller truncation becomes a draw.
Static here means the normalized pure material leaf, not PRIMARY's full
Static-dynamics/order adapter. Their performance numbers must not be added.

The384-slot run finishes in1569.399 seconds under its original2400-second
cooperative cap:25,926 completed queries,5,274,368 nodes,0 UNKNOWN. No missing
slot is filled, model selected or old experiment rerun. A separate synthetic
pre-query interruption check preserves384 missing slots with zero Player calls;
it is lifecycle validation, not scientific play.

## Actual paired results

Each row contains64 role frames. Utility is W minus L divided by64.

| Policy | W/D/L | Utility | Difference from Unit | Difference from mobility |
|---|---:|---:|---:|---:|
| Unit |8/45/11|−3/64|0|−3/64|
| mobility |10/44/10|0|3/64|0|
| Static material |10/44/10|0|3/64|0|
| B2C1 |10/45/9|1/64|4/64|1/64|
| Unit-TD |10/45/9|1/64|4/64|1/64|
| mobility-TD |10/44/10|0|3/64|0|

Unit-TD improves over Unit by2/32 in each role. Its entire extra contrast over
the free priors is role1,1/32; role0 contributes zero. Unit-TD/B2C1 have64/64
equal outcomes and48/64 equal complete records. Mobility-TD/mobility have64/64
equal outcomes and57/64 equal records. The finite arithmetic is not a
population significance test. No minimum detectable effect or inferential
power gate was preregistered, and none is retroactively asserted. The later
13:18 Chat advice arrived after this already-frozen run had closed.

## What was learned, and what changed

The endpoints reuse256 complete frozen-policy episodes from Unit/mobility;
they are not online TD trajectories. For each world/initialization, average
the16 episode updates, using the maintained TDLeafEpisode with eta0.05,
lambda0.95, scale10 and A fixed at1. Actual player0 terminal rewards supply
the endpoint targets; no oracle label selects a training start.

All9803 own-actor targets and16 endpoints are reconstructed. There are7119
nonzero B/C gradient observations and178 nonzero episode deltas. An independent
reverse-error sum agrees within2e−14. The final reward update itself is zero
in every episode. Interior transitions include133 nonzero terms targeting a
terminal search prediction and135 targeting an ordinary search prediction.
Thus zero *additional final-reward* credit does not mean payoff information
was absent. These categories are arithmetic contributions, not new ablations.

The two TD/own-initial contrasts contain25 first divergences at18 distinct
full histories. Literal shared-Core D4 trees complete for all18:47,347 visits.
Twenty-two initial served actions are excluded by the TD critic's optimal set;
every TD served action remains co-optimal under its initial critic. Three
pairs retain both served actions under both critics. Full-set changes and
both-served co-optimality are overlapping properties.

There is also a useful general bound for these particular Unit endpoints.
Every material leaf has A/B/C features in`{-1,0,1}`, hands zero. Enumerating
the27 possible feature vectors per world bounds the actual floating leaf
change by at most epsilon=0.019571245749042676. Terminal-distance scores do not
change. Negation and max are nonexpansive, so every literal root-action value
changes by at most epsilon at any common finite depth. Unit action values are
integers: a formerly strict gap is at least1. Since2epsilon<1, a Unit-TD
optimal action must have been Unit-co-optimal. All18 observed Unit divergences
also satisfy the stronger full-set inclusion check.

This is a statement about the admitted complete finite-depth material critic,
not an all-state public-search correctness certificate or an actual-WDL ceiling.
Refining an old critic tie can change later visits and improve played outcomes.
It does not identify unique intrinsic prices, justify arbitrary larger steps,
or imply that other initializations and rules have the same integer-gap bound.

## The sole improvement beyond free priors

World16/prefix0/role1 first diverges at ply9 with six actors, full-history ID
`9a23405c7e45519b8107d31a74d3db8ca2b7283e0bc7caa1bd282541346a1f6d`.
Unit-TD and B2C1 select the same A move; mobility selects a King move.
A separate NEW literal D4 probe pays2215 visits. Both served moves are
co-optimal under Unit-TD and mobility. Unit-TD removes another action from the
larger optimal set; it does not strictly prefer its served move over mobility's.

Two NEW full-history continuations,125 D4 queries/28,454 nodes/9.770 seconds,
isolate the first action from the later learner policy. Original outcomes are
reused rather than replayed as new fitness.

| Forced first action | Later learner policy | Role1 actual outcome |
|---|---|---|
| Unit-TD | Unit-TD, OLD | DRAW |
| mobility | Unit-TD, NEW | LOSS |
| Unit-TD | mobility, NEW | DRAW |
| mobility | mobility, OLD | LOSS |

The TD first action is sufficient under the fixed mobility continuation and
opponent, and changing only the tail does not rescue mobility's first action.
This is a conditional policy intervention. The six-actor actions' minimax WDL
remains UNKNOWN; it is not proof of a unique strategically best action or a
general tie-policy repair. B2C1 already obtains the same finite benefit.

## Cached history truth and verification

Eight already-COMPLETE4×4 graphs are reused without new closure work. Among
4126 distinct prospective query histories,1037 have point bounds for all
actions,581 retain one-sided bounds and2508 are uncovered. No certified inferior
served action is found in the covered visits. Policies visit different states,
so these counts are not paired error rates. The key larger-material gain
histories remain outside a complete exact action-WDL comparison.

The private reader checks all384 outcomes and25,926 queries/101,415 PV edges.
The public compact reader checks all outcomes/records and3482 queries/13,623
PV edges from48 metadata-selected full games. The mechanism reader recomputes
19 literal trees/49,562 visits,26 controls and216 integer-gap leaf bounds,
and checks all125 intervention queries/488 PV edges. The target reader checks
all9803 published target arithmetic rows and256 actual terminal outcomes.
Cached old graph annotations are reused, not independently rebuilt by these
fast public readers. Full omitted old target PVs stay in hashed private ledgers.

An initial mechanism-reader attempt passed its tree/PV portions, then supplied
a GameSession where state_sha requires GameState. Only that reader call was
corrected; no game, query, model or cap was changed. The first regression test
invocation also encountered an unwritable system temporary directory; using an
own-checkout basetemp repaired the environment. The93 relevant compatibility
tests pass. No shared Core/Session/search change or learner speedup is claimed.

## Larger-board truth: caps and a cheaper fallback

PRIMARY's committed5×5/6×6 trajectories supply4549 four-actor references and
2436 distinct histories. Before labels, metadata hashes select two5×5 roots
in distinct fingerprint/roster groups and one6×6 root. This is post-hoc truth
and cost diagnosis, not a new rule screen, training-start selection or causal
board-size comparison. Each closure has a600-second enumeration guard and
500,000-position ceiling; the batch retains its1800-second whole cap.

| Board/world | Positions admitted / expanded | Result | Measured seconds |
|---|---:|---|---:|
|5×5/26|427799 /417282|TIME_CAP_UNKNOWN|617.260|
|5×5/1|373072 /373072|COMPLETE|601.312|
|6×6/53|500000 /298045|POSITION_CAP_UNKNOWN|530.456|

The whole loop takes1750.112 seconds. Per-component times include preserving
the graph/partial snapshot after the cooperative enumeration guard; they are
not assertions of total runtime at most600 seconds. Partial graphs retain no
WDL labels and are never resumed or treated as closed. Summed admitted entries
and expanded entries have different meanings, and are not independent samples.

World1's selected root has only three rule plies left. Its11 actions are all
DRAW, despite a prehistory count3. A direct actual-history tree verifies this
with1220 visits in1.083 seconds:1089 MAX_PLY and10 repetition terminal leaves.
Building the global component was unnecessary for that single-root answer.
This was a cost-selection mistake: check remaining rule clock before global
closure. The paid component is retained and reused over all384 same-fingerprint
natural references:96 distinct histories,12 fully point-labelled and84 bounded,
with no certified inferior served action. No further precision job is justified
merely to turn these bounded counts into a larger exact count.

A smaller fallback was frozen before any new child labels: one metadata-hash
legal capturing child per original parent where available, used only after a
parent attempt closes UNKNOWN. World1 reuses its complete graph; world26 has
no such child. The sole NEW6×6 child of world53 completes in105.347 seconds:
65,760 positions/500,048 edges, under its180-second/120,000-position limits.
This is a new three-actor problem, not a refill of the failed four-actor cap.

Its actual history has only A plus two Kings, max prior count1 and105 plies
remaining. The exact action bounds are`[-1,-1], [0,0], [-1,-1]`; root WDL is
DRAW. It is outside the structural draw-only closure, which contains2208
entries: minimax DRAW and a closed deadzone are different here. The capturing
action therefore raises the original four-actor parent's lower bound to0;
the parent remains`[0,1]`, since its other actions are UNKNOWN. This child is
legally reachable from the natural parent but appears in zero original played
query records; do not describe it as natural decision exposure.

Four NEW Unit queries at D1/D2/D4/D6 all complete and select the DRAW action,
paying437 nodes in0.997 seconds. A literal D4 tree pays827 visits and gives
`[-1,0,-1]`. B/C and hand features are identically zero throughout this
capture-removal component, so all A1 pure-material endpoints have the same
evaluator there. This is a useful WDL fork already handled by counting, with
no free B/C price contrast to learn. It does not validate larger-board training.

## New committed structural rules: actual useful-decision exposure

Recovery also consumes sandbox `7c0d3e55d6424945ab166b06351e16823cda9b70`.
Its shared Core/rules/Session/search and public helper files match the imported
`efac7908` baseline; the new commit supplies additional research inputs. No
uncommitted PRIMARY work, generator task or production default is adopted.

The complete committed price packet contributes 960 OLD games and 21,306 OLD
query references. A new Core replay finds 3,322 references to four-actor states
with two distinct ordinary types: 1,852 distinct full histories across 39 full
rule fingerprints. Neither 39 fingerprints nor repeated policy records are
independent movement-rule samples. The census is for post-hoc truth feasibility,
not another forward screen or oracle selection of experiential starts.

For each fingerprint, choose its shortest remaining-clock history, breaking
ties by SHA256 of fingerprint and history ID. The first component is selected
by that same hash among the 20 candidates with at least16 plies remaining and
maximum prior repetition count at most2. Under a fixed180-second/120,000-position
cap it closes33,584 positions/149,000 edges in51.430 seconds. Root WIN/DRAW
actions differ, but its two saved Unit/Static calls both complete at depth0 by
choosing an immediate win. A raw action-WDL fork therefore overstates this
root's unresolved learning opportunity.

One separately frozen additional attempt changes that premise: require a saved
positive-depth search return before choosing the first hash among10 eligible
candidates. This is an adaptive, explicitly post-hoc diagnostic, not a fresh
unbiased test or training-start procedure. The first result and its cost remain.
No third component is launched. The second root, world23, has118 plies left and
maximum prior count1; its component closes49,928 positions/261,744 edges in
71.303 seconds under the same separately declared cap. Its seven action values
are `[-1,-1,-1,-1,0,0,0]`. Both saved search policies choose a DRAW action.

Intersecting the two paid components with all40 same-fingerprint saved games
gives360 covered query references at169 distinct histories;303 other references
remain uncovered. All360 covered histories have exact action bounds under their
actual clocks/prehistory. Twenty-one distinct histories have nonconstant action
WDL, contributing54 repeated references. None of240 covered search references
is certified inferior. Of120 FLOOR references, two are inferior, but both refer
to the SAME actual history and same chosen action in two policy runs: WIN is
available, while FLOOR selects DRAW. This is one witnessed mistake, not two
independent errors. Different policy visitation counts are not paired error rates.

Two local pure-material diagnostics examine the second frozen root and the sole
FLOOR-error history. At D1/D2/D4, Unit, B-half, B-double and A-normalized Static
all have the same singleton optimal support, and that action has optimal actual
WDL. These six literal trees cost3,082 visits/2.580 seconds; they are not new
played games or PRIMARY's dynamic/ordering policy. Even D1 resolves both tested
witnesses. This finite parameter check neither proves an all-price law nor
rules out useful learning on the uncovered histories.

A new exhaustive check over all20 already-covered forks in the second
component examines D1 and D2 with the same four material vectors:40 additional
literal trees/769 visits/0.787 seconds. All four vectors keep identical supports
in every case. At D1,12 of20 supports include a DRAW action where WIN is
available; at D2, every supported action at all20 roots has optimal exact WDL.
This identifies a finite horizon/tie mechanism that two singleton witnesses
would miss. It is still exposed post-hoc analysis, not an independent test,
actual policy rollout, all-positive-price theorem or evidence to train more TD.

The public structural reader rebuilds both components through Core and checks
every supplied natural-history action bound and served-action regret. Entries
summed across components are paid work, not independent states or samples.
It does not load or trust the private pickle caches. An interrupted reader
provides no verification success. Exact graph and oracle labels remain outside
experiential training and training-start selection.

## Higher-material actual-Session proof preflight

A separate preparation finds49 saved same-history positive-depth Unit/Static
action disagreements across34 full fingerprints with more than four actors.
Before new proof labels, hash order selects one per fingerprint and the first
four roots: actor counts8/6/8/8. Full Position-graph closure is not launched.
Four actual-Session proof-number preflights instead receive4096 visited nodes,
five seconds and depth8 each. This reuses the maintained AUX opt-in
`generic_session_win_proof_batch_pn` and public Session certificate verifier,
including complete defender choices and actual terminal authority.

The first three calls retain UNKNOWN after5 seconds each, visiting
1278/1234/1475 nodes. Peak explored depth is not completed minimax depth.
The fourth call returned a certificate but its wrapper incorrectly accessed
the verifier dictionary as `v.valid`. That original attempt failed before its
certificate/verification receipt was durably saved. Its exact fourth-call cost
is unavailable; the original call limits and failure remain. It is not silently
counted as a verified result or replaced by a successful first attempt.

One NEW, separately recorded technical recovery corrects the dictionary
contract and repeats only the failed fourth root. It proves WIN in547 visited
nodes/2.087 seconds. Public Session replay verifies its rank5 certificate with
eight nodes/seven transitions and two actual checkmate leaves. The first three
UNKNOWNs are not rerun. This repair adds cost and does not refill old fitness
or graph caps. The wrapper now preserves its unverified export before replay.

Four separately frozen child calls then test the two saved S4/U4 actions for
both root players, with the same4096/five-second/depth8 limits. Together they
take6.348 seconds. The U4 action retains an actual rank4 WIN certificate,
independently replayed at seven nodes/six transitions. S4 remains[-1,1]: neither
a failed forced-win call nor `no_forced_win_in_exhausted_tree` supplies a draw
or loss label. The root is[1,1],U4 is[1,1],S4 remainsUNKNOWN. A certificate for
one action does not prove the other action is inferior.

Both OLD full games containing these price choices end with physical player0
winning: the S4-at-root record has29 queries and the U4-at-root record has5.
Their reported utilities use the named controller's physical role, so the
opposite signs in those source rows are not opposite physical winners. These
records are reused, not new fitness. The proof does not establish a new played
strength contrast, price law or learner benefit. No prepared600-second expansion
is launched after these preflights.

The certificate reader decodes only public GameRecords, then independently
checks both complete-defense trees against actual Session replay. Decode alone
is not verification. Full source hashes, first failure, new recovery, all UNKNOWN
receipts and both certificates are retained in the structural packet.

## Direction and communication

The evidence supports keeping this finite positive comparison while declining
to expand TD on these exposed eight worlds. Ask Chat/Claude whether the next
decision-changing step is a small label-blind tie control or more history truth
on newly committed PRIMARY rules. The first new-rule consumption is now done;
the next preference is one cheap neutral tie control, reusing an existing
intervention outcome if its action matches. Do not expand proof merely to
resolve S4's remaining UNKNOWN where both saved physical games already win.
A zero or
small finite contrast does not establish a universal absence of learning space.

PRIMARY still owns rule/layout generation, forward screens and depth campaigns.
DEV_AUX owns these frozen-policy learning mechanisms and history-truth costs.
The shared public helpers/tests are reused from sandbox
`efac79080ba6eb2b8219e325e9779dcb1a47abbb`, checked unchanged at
`7c0d3e55d6424945ab166b06351e16823cda9b70`; the research learner/receipt adapter
remain AUX-specific. No other-role files, product defaults or worker are changed.

The user's later two-way communication instruction is in both existing patrol
prompts. The latest direct cadence correction changes both to ACTIVE at60
minutes, with unchanged chat targets, superseding the earlier120-minute receipt.
The own mailbox entry previously resumed one SEND_UNCERTAIN forever. It now
preserves that old dispatch after a completed unsuccessful reconciliation read,
permits a new distinct report, rejects resending the identical old body and can
reconcile the old dispatch later. A no-reply tool footer no longer masquerades
as an edited comment. Eighteen focused mailbox regressions pass. Administrative
prompt/transport work is excluded from effective research time.

Curated data and portable readers: [evidence directory](data/leaper_prospective_td_20261023/README.md).
