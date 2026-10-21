# Search allocation and any-win qualification — 2026-10-21

PRIMARY retained the current evaluator, search defaults and independent AUX lane.
The new result is a scoped cost benefit from the existing default-off any-win
option, alongside negative evidence against selecting q depth from deeper
scores or restored actions. The maintained cost probe now exposes the existing
`--capture-only-qsearch` option; it does not introduce a new engine policy.

[Technical evidence index](data/search_allocation_20261021/summary.json) links the
complete fixed PUBLIC packet at3ddbf998, whose contents include48
complete generated rules,592 new capped game histories,202 finite roots and202
actual finite continuations, literal proof observations, all missing/failed slots,
paired costs and exact private-original hashes. It references the preceding
four-world packet at base revision6ea35571272708f7e220fa3868f2ca1a4d0cf7ca.
A separate reader replayed all592 histories/16996actions and all finite records
through Core, matching complete records and terminal results. This establishes
saved-record correctness, not an independently replicated timing experiment.

## Controlled scope

New generated rules use16 fixed seeds2026102501–2026102516 at each of5/6/8
squares, three existing setup presets, hybrid leap/ray movement and the existing
optional no-opening-win1 preference. All48 generated successfully. These are
movement-generator rules lowered to semantic execution; they do not sample the
whole explicit DSL/compound/auxiliary domain. Full rules, promotion, drops,
relevant history and actual rule clocks remain intact. The earlier560-game
subcohort includes4256drops and790promotions. There is no all-domain claim.

Each5/6/8 comparison uses a fixed D2q0 opponent, default static profile/dynamics,
TT/main ordering/root scan, actual Native legality/availability/check services,
3000 paid nodes and0.1seconds per query, hard check-q depth8, and64 additional
observation plies. Actual rule caps are unchanged. Query times above0.105seconds
and operational fallbacks make a game unqualified for paired utility; retain its
raw result but assign[-1,1] in the analysis. UNKNOWN is never a draw or success.
Different trajectories have different query counts, so total game cost is not a
same-position speed ratio. Historical and new arms run sequentially.

The6/8 study reuses seed IDs but rotates the preset across the combined world
list. Linked IDs are family identifiers, not a board-size-only intervention.
The later mixed-board check-only/any-win prototypes also inherited a misleading
`board_size:5` header. Their frozen slots and complete rules correctly identify
32games per board. The packet retains and explicitly diagnoses this metadata
error instead of silently correcting original records. Future work must replace
all dependent template scope fields before launch.

## Actual utility and the missing factorial cells

The new16-game D3q0 arm on the earlier four rules ends5W/6L/5UNKNOWN. Relative to
sealed q1, its mean identification interval is[-0.625,1]; no robust gain.
Eight bounded independent Core child observations remain[-1,1].

The following are raw32-slot counts per arm. Intervals additionally censor all
unqualified slots. They are finite-cohort identification bounds, not confidence
intervals, Elo or population estimates.

| Board | D2q1 full W/L/U | D2q1 capture W/L/U | D3q0 W/L/U | D3q0 minus full q1 |
|---|---|---|---|---|
|5|8/22/2|10/21/1|17/13/2|[0.4375,0.6875]|
|6|4/24/4|6/24/2|17/12/3|[0.5625,1.125]|
|8|8/14/10|9/13/10|9/7/16|[-0.75,1.0625]|

All96 first5-board slots qualify. The192 larger-board slots include12 timing-only
and3 fallback-only failures, disjoint and all retained. The result supports a
local allocation difference on5/6boards; it does not establish dominance or an
8-board improvement. All22 first action divergences in the initial5-board
three-arm comparison originate with the candidate;10 paired histories match.

Separately add64 post-seal games to fill A=D2q0 and D=D3q1, retaining B=D3q0 and
C=D2q1 full from the original96. This is an exposed mechanism diagnostic, not a
new contemporaneously randomized full factorial. All32 contexts per cell qualify.

| Contrast | Mean bound |
|---|---|
|B−A|[0,0.25]|
|D−C|[0.1875,0.5]|
|C−A|[-0.5625,-0.3125]|
|D−B|[-0.375,-0.0625]|
|(D−C)−(B−A)|[-0.0625,0.5]|

Family-paired intervals are included. For example C−A is strictly negative in6
families and includes zero in10; the interaction has2positive,1negative and13
zero-containing family intervals. Do not treat both owners as independent games
or infer a universal main-depth/q interaction.

## Mechanism and negative alternatives

Seven qualified contexts change from an A win to a C loss. Five original C
queries already completed D2: horizon changes cannot all be explained by a lost
main iteration. Two original C queries retain D1; separate larger-time cold
D2 queries change their actions. All28 cold four-cell queries preserve parents.
Six relevant child WDL observations remain UNKNOWN; the seventh is an explicit
win under a larger diagnostic allowance. These are not seven proved bad actions.

Fourteen further q2/q4 queries complete D2 in7/7 versus2/7 cases and restore the
old q0 action in4/7 each. That stability did not predict utility: a separately
frozen32-game q2 arm finishes7W/24L/1UNKNOWN, all qualified and Core-replayed.
Its contrast with q0 is[-0.625,-0.4375], and with q1[-0.1875,0]. Thus q2 is not
selected. Twenty-five first divergences from q0 originate with the candidate;
14 retain D1 and11 D2. Seven histories match. A saved common parent at seed2513,
ply6 distinguishes an original100ms D1 loss trajectory from a separate308ms cold
D2 checking-drop win proved by Core. The persistent/cold TT difference is also
explicit; never replace the original loss with this diagnostic win.

A q4 mate5 claim at seed2501 remains independently unproved: the fixed2second
Core observation visits3943 transitions and returns[-1,1]. This is neither a
proved contradiction nor permission to expand its cap. It is retained separately
from the successfully certified any-win cohort below.

On the exact3x3 finite game/two equivalent encodings, check-only D2q0 still makes4
selected-action errors in202 queries. Capture-only D2q1 makes zero and its202
actual continuation policies match exact values, costing3712nodes. Four Core
witnesses show why: it retains quiet terminal children even without captures,
promotions or inventory changes. It omits ordinary quiet checking continuations;
an existing forced-check regression demonstrates a missed win. Consequently it
is not a generic substitute for full q search. These are dependent exposed
conditional histories, not202 independent games or training labels.

On64 identical earlier hybrid inputs,128 interleaved full/capture q1 queries retain
all6 known certified flags. Capture/full paid-node ratio is0.8121 and time ratio
0.9470, narrowly passing the declared5% time screen. There are two changed actions
and two extra D2 completions, without a strength claim. A real seed2512/prefix5
checking drop has an independent all-defense Core mate3 certificate; separate
cold full-q1/capture-q1/D3q0 costs are595/401/1068nodes. The maintained CLI with
capture-only reproduces its action/score in401nodes, with matching input/source
hashes. This does not refill the original D3 game loss.

Eleven earlier hard roots give one extra D2 completion with existing ordered q
in22 calls. Concurrent normal project load limits timing interpretation. No
utility benefit is established. Inventory profiling also fails its proposed
5% hotspot threshold: combined self time1.96%, combined cumulative envelope5.62%.
Combining scans cannot erase all their work; no optimization was implemented.

## Any-win goal: literal proof and paired cost

Run96 new D3q0+any-win games on the same48 exposed rules and fixed D2q0 foe.
Core replays2953 actual actions. All78 positive candidate claims are independently
proved:43 immediate wins and35 mate3 claims, with no missing proof. For these35,
source is `completed_root_win` and completed depth2, not completed D3.

| Board | Raw W/L/U | Qualified | Difference from sealed D3q0 |
|---|---|---|---|
|5|17/14/1|31|[-0.1875,0.0625]|
|6|17/12/3|31|[-0.3125,0.25]|
|8|9/5/18|24|[-1.0625,1.3125]|

Whole-game utility remains unidentified. On all35 non-immediate proved parents,
70 separate cold, interleaved off/on calls retain exactly the same action and
independent Core win. Node ratio is0.1864 and time ratio0.1773. Of the off calls,
30 finish D3; their separate ratios are0.1974/0.1830. Five hit the node cap while
retaining a completed winning child; their ratios are reported separately. All
on calls stop with `root_win_found` at truthful completed depth2. These selected
positive-root savings justify retaining the option, not enabling it by default,
claiming shortest mate, or extrapolating an average speedup to arbitrary roots.
Search clamps static values below the terminal band; an oversized heuristic
alone cannot activate the option, as the existing regression also verifies.

## Theory use and remaining uncertainty

Hay et al.'s [Selecting Computations](https://arxiv.org/pdf/1207.5879) frames search
as computation cost versus eventual decision utility. Its sampling assumptions
and unknown result distributions do not license treating our static score gaps
as calibrated win probabilities or applying independent-sample bounds to warm-TT
node counts. Our inference is narrower: an independently proved win attains the
any-win goal, so further search can be avoided without fitting a new controller.
No MCTS, metacontroller or learner was added.

Nau et al.'s [When is it better not to look ahead?](https://www.cs.umd.edu/~nau/papers/nau2010when.pdf)
studies branching, evaluation granularity and nearby-state value similarity.
Its decision-error definition needs true optimal moves. Our fixed-foe losses and
score oscillations do not establish that metric; exact finite controls and
larger-game trajectories must remain separate. Neither more score precision nor
a gate fitted to these exposed results follows from the paper.

The worst recorded168.7ms query does not recur in three cold diagnostics, each
about100.1ms. The largest instrumented budget-check gap is1.68ms; CPU-clock
increments are actually15.625ms in the diagnostic. No scheduler/OS cause is
confirmed, no timing tolerance is relaxed, and original failures remain excluded.

## Reproduction, verification and next selection

Use the actual `worlds`, study protocols and strict canonical records in the
packet with existing `GameSession.replay`, `deserialize_game_record`, Core
terminal evaluation, public `AlphaBetaPlayer` and benchmark `play_game` APIs.
The `analyses.generated-drop-probe-input` object can be saved with the existing
research-record writer and passed to:

```powershell
.venv\Scripts\python.exe scripts/semantic_probe_cost.py --input artifacts/generated-drop-probe-input.json --seed-count 1 --prefixes 5 --variants all --depth 2 --qdepth 1 --nodes 3000 --seconds 2 --total-seconds 10 --capture-only-qsearch --output artifacts/generated-drop-reproduction.json
```

A fresh run is a new measurement, not a replacement of any sealed output. Full
original per-query instrumentation stays private; the public copy retains complete
inputs/histories, costs, failures and terminal claims without adding tracked
one-off producers.83 affected qsearch/semantic-effects/completed-win/strict-record
regressions pass. No static expected value was changed.

Keep defaults and AUX ownership. Next examine an explicit non-actor/auxiliary
effect case using an existing semantic fixture and maintained caller: do the
actual child classification, mandatory controls and bounded choice preserve full
state/history under selective q? Begin with a small paired Core/service
feasibility; no solver replacement, new learner, frozen panel refill or generic
claim from one fixture. Broader distributional utility follows only a concrete
new mechanism and declared exposure. Science OPEN.

The user's two existing schedules were changed and verified ACTIVE at90minutes;
no new task/worker was created. Timing administration and delivery are excluded
from research time. Project Chat was read once with no new messages, privately
preserved before assessment. No outbound message or AUX checkout/state write.
