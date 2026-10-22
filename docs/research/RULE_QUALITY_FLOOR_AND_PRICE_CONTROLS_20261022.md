# Rule quality, terminal competence and complete price controls — 2026-10-22

## Decision

Keep rule-derived and Unit prices as candidates. Do not activate a generator
filter, evaluator, ordering policy or learner from this exposed cohort. A cheap
terminal-recognition policy is a useful competence control: low random-play
resolution alone does not establish an unlearnable game. The new finite
Unit-leaf edge warrants a fresh, predeclared comparison at common ordering;
12 full new inputs are prepared, with zero fitness queries.

[Technical summary and replay instructions](data/rule_quality_prefix_and_floor_20261022/README.md)
contain the complete selected inputs, actual returns, failures and qualification.
The preceding [rule-quality report](RULE_QUALITY_CAPTURE_AND_COMPETENCE_20261022.md)
remains evidence; none of its frozen UNKNOWN outcomes was replaced.

## Inputs and actual work

Reuse the original 24 generator slots: 22 accepted slots represent 13 distinct
complete rules; two generation refusals remain. Each capture variant has 176
recorded uniform-policy views, comprising 104 actual games and 72 exact reuses.
The variants differ only in capture disposition. All promotion, drops, future
types, auxiliary fields and complete relevant history remain in the inputs.
The rule clock is 512 plies; the experiment caller stops at 96.

Fixed prefixes 0/4/16/64 give 1,408 accepted-view slots, plus 128 unavailable
intended slots from generation failures. There are 1,314 available prefix
records, including three actual terminal states, and 570 distinct full inputs.
A metadata-only 24-input preflight preceded the whole pass. An independent
reader checked all 570 roots and 13,376 literal complete child states.

A two-turn terminal scan checks 501,312 replies on those distinct inputs. The
subsequent dense pass covers all 16,398 actual turn roots and 208 final states
of the old 208 games. It performs 15,847 new scans and reuses 759 exact prefix
returns. Its 1,430.2-second cost was below the frozen 2,400-second cap. All
positive WIN/LOSS witnesses, actual selected-action classifications and full
parent histories were separately qualified with shared Core. This is not an
independent rules engine or a complete WDL census.

No new random games, training or AUX work ran. There are 176 genuinely new
match games across the price factorial, with 2,064 Player returns and 2,008
FLOOR turns. Two earlier crossed cold prototype returns are separate. Every
new match history and all 2,064 literal Player PV edges pass Core qualification;
a legal PV does not independently prove its returned search value.

## Sparse experience is not explained by one closed subclass

The checked two-king/empty-hand/no-creation subclass is a sufficient no-mate
argument under its stated draw/clock conditions, not an all-domain detector.
Only the remove-from-game variant enters it: nine actual games / 18 views,
first entering at plies 50–90. It occupies 227/8,519 actual turns (2.665%);
the equal-game mean occupation is 2.274%. Thus this known subclass does not
explain most unresolved experience. Other unproved draw classes remain possible.

The pocket traces include 2,013 actual drop actions and 6,485 promoted-piece
turns; remove traces include 6,497 promoted-piece turns. These semantics were
exercised, not merely retained as unused schema fields.

A fixed 8×8 opening has 28 actions: two are immediate wins and 17 concede an
immediate winning reply. This proves some local choices differ, but it does not
prove that learned prices are needed to distinguish them. At a certified WIN1
root, if W/L/D/U count immediate-win, reply-loss, immediate-draw and unknown
children, uniform first-action regret against adversarial continuation is bounded
by `[(2L+D)/N, (2L+D+2U)/N]`. The example gives `[17/14, 13/7]` on utility
−1/0/+1. This is neither random-self-play payoff nor a trained-policy gain.

## A terminal-recognition control isolates one cheap mechanism

FLOOR takes the first Core-legal immediate rule-winning action if one exists;
otherwise it follows the original uniform RNG stream. Until its first activation,
its history is exactly the original history, and the new action ends the game.
The 96-ply caller limit is unchanged: a diagnostic win at the final censored
state is not executed as a 97th move.

For both players using FLOOR, complete derived records and a fresh RNG/Core
policy reader agree on all 208 actual source games:

| Variant | Original checkmate / draw / UNKNOWN views | FLOOR checkmate / draw / UNKNOWN |
|---|---:|---:|
| Pocket | 48 / 12 / 116 | 130 / 12 / 34 |
| Remove | 14 / 22 / 140 | 80 / 16 / 80 |

Six of the 18 original closed-class views avoid entering that class; 12 do not.
Original outcomes remain untouched. These are exact finite counterfactuals on
exposed streams, not new independent samples or an automatic experience filter.

The four policy cells are A=RNG/RNG, B=FLOOR/RNG, C=RNG/FLOOR, D=FLOOR/FLOOR.
The additional 416 one-sided policy cells pass fresh RNG/Core execution. Ignoring
computation cost, immediate-win substitution weakly dominates the original
policy against a fixed opponent: its first deviation is already a win.

A correction matters: equal censored prefixes under different continuing
policies do **not** imply equal unknown eventual outcomes. The earlier shared-tail
calculation is retained only as a conditional common-continuation result. For
unbounded continuing policies, distinct unknown cells and the dominance
constraints `C≤A≤B`, `C≤D≤B` give the following conservative sensitivities:

| Variant | B−A | D−C | Interaction D−C−B+A | Role-balanced gain |
|---|---|---|---|---|
| Pocket | [13/88,129/88] | [7/11,103/88] | [−15/22,45/44] | [73/176,145/176] |
| Remove | [9/88,149/88] | [13/44,16/11] | [−101/88,119/88] | [17/88,19/22] |

A separate analytical-closed-draw layer tightens some remove bounds without
relabeling raw UNKNOWN. An independent halfspace-vertex solver verifies 1,664
objective extrema across 416 source/layer cases. These are finite completion
bounds, not population confidence intervals. Physical deadlines can defeat the
free-computation dominance argument; no runtime/default claim follows.

## Capture resources and promotion change early defense

All 13 matched opening-rule pairs were checked. Six two-turn branches in the
8×8 free-random family 20 have identical physical boards, side, promotion flags
and auxiliary state but different hands/fingerprints. Remove ends in mate;
pocket has exactly one legal drop, verified to escape check.

One concrete sequence uses generated types, not orthodox piece meanings:
`X f2×c8; X b8×e2=B`. Pocket legitimately holds B and can play `B@f2`;
remove has no such defense. A full 16-cell promotion/capture control shows
that choosing B for the first mover's promotion supplies an alternate board
move `B c8–f2`, so remove also survives this particular attack. The unpromoted
opponent-X move is a negative control. The original six branches include a
second, distinct opponent-C action from h8; these actions are not interchangeable.
This is a rule/resource counterfactual, not a same-RuleSet board-value
impossibility or a proof of eventual pocket wins.

## Competence beyond FLOOR and the price factorial

The 24-state matched cost preflight has a maximum FLOOR choice cost of 10.2 ms
on this execution. Then D1 uses the maintained Player, fresh player per game,
TT within game, no disk profile cache, 8,192 nodes / one second per decision,
requested q4 / check-hard8 and a 96-ply caller. The fixed FLOOR opponent uses
the same owner-local RNG streams in both candidate roles. Missing generation
slots are preserved, and no frozen cap is extended.

All cells have 44 completed, eligible games and four unavailable role slots:

| Cell | Leaf / ordering | Wins / losses / UNKNOWN | Candidate nodes | Paid candidate seconds |
|---|---|---:|---:|---:|
| A | Static / Static | 33 / 11 / 0 | 49,968 | 8.000 |
| B | Static / Unit | 33 / 11 / 0 | 49,968 | 8.124 |
| C | Unit / Static | 36 / 4 / 4 | 70,710 | 11.957 |
| D | Unit / Unit | 34 / 4 / 6 | 72,631 | 12.446 |

Unit covers every declared/current/future nonanchor with board1000/hand900,
keeps anchors and supplied Static hand zeros at zero, and gives promotion
price gain zero. Dynamic weights remain 2/5/3. Thus the leaf control includes
material and price-derived promotion effects; it is not a single coefficient
or a learned evaluator. Ordering uses its stated table separately.

The same exact FLOOR-self game is reused as two opposite role frames, whose
utilities sum to zero even if unresolved. This legitimate role identity does
not couple different candidate policies' UNKNOWN tails. Static D1 therefore
has finite role-balanced utility 1/2 against FLOOR; it exhibits competence
beyond that terminal floor, without identifying its cause as rule prices.

Against that fixed opponent, accepted-cohort effects are:

- Complete Unit D−A: `[1/22,7/22]`.
- Leaf at Static ordering C−A: `[3/22,7/22]`.
- Leaf at Unit ordering D−B: `[1/22,7/22]`.
- Ordering at Static leaf B−A: `0`.
- Ordering at Unit leaf D−C and the interaction: `[−3/11,2/11]`.

Equal weighting of the 13 distinct full rules keeps the two leaf bounds positive,
`[2/13,4/13]` and `[1/13,4/13]`. This is a descriptive reweighting, not more
independent evidence. Negative/uncertain families remain, and hypothetical
planned-generation completion bounds cross zero. Unit also pays more turns and
nodes. Keep this scoped positive result alongside older negative/different
opponent envelopes; it selects no universal winner or production default.

## A failed simplification was diagnosed, not patched into success

Actual D1 reserves ordinary q depth zero in its first iteration but still uses
forced check evasions through hard depth eight. A naive complete-one-ply-value
assertion failed and its original reader/results are retained. On the first
failure, a naive value5648 checking move permits three legal quiet evasions with
literal values2724/2724/2712; the actual selected score5593 is not contradicted.

Among 34 first trajectory divergences, 15 satisfy the no-checked-child plain-leaf
contract and have independently checked disjoint Static/Unit argmax supports.
The other 19 are explicitly **not** full-value-qualified by that simplification.
Their complete histories/PVs remain physically qualified. No production code,
old test expectation, frozen return or rule meaning was changed to fit a result.

A preflight output-directory error before the first save, a reader syntax typo
and shell quoting errors were also retained privately. They caused no new
fitness refill; the scientific contract failure above is preserved publicly.

## Cost, advice and next decision

One new Claude root and its complete thread were privately saved before
assessment. Its request to stop the old fallback expansion agrees with the
already published mainline; the cited old sandbox revision did not include the
preceding rule-quality delivery. AUX roster/training suggestions remain AUX's
work. No outgoing message or real-time consultation occurred.

Dense all-reply instrumentation costs far more than the cheap competence controls;
do not make it a gate for every new game or learner. Use existing exact terminal
semantics and bounded witnesses only when the answer changes a concrete choice.

Primary-source checks reinforce the scope limits:
[Browne–Maire 2010](https://rafal.io/static/papers/evolutionary_game_design_ludi.pdf)
targets human-interest quality, not a universal learning gate.
[Clune 2007](https://cdn.aaai.org/AAAI/2007/AAAI07-180.pdf) combines goal/payoff,
control and termination; stability alone is not the full method.
[Stephenson et al. 2021](https://ludii.games/publications/COG2021-1.pdf) studies
rule-description prediction of heuristic performance, a useful future candidate,
but not fixed piece-price calibration or grouped-family transfer evidence.
No published human/game labels were fitted.

The next protocol freezes 12 fresh seeds over 4/6/8 boards, classic/free setups
and bilateral/none symmetry before generation. All 12 generated successfully.
It compares the two leaf candidates at common Static ordering against FLOOR,
48 intended games, the same full semantics, 96-ply caller and a shared900-second
batch cap. Its existing opening preference is ON only in this experiment;
production defaults are unchanged. Inputs are complete; fitness queries are zero.
Science remains OPEN.
