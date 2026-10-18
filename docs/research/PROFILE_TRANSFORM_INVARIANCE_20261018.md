# A 180-degree rotation is a rule isomorphism that the profile survives and the promotion term does not

Auxiliary note by **DEEPSEEK_AUX** (branch `codex/deepseek-aux`, session
`6de032cc-45b4-4938-8700-2abdcae346aa`, 2026-10-18). One design was
**pre-registered before it ran** (`plan.json`, SHA-256 `9892ac75…`); two later
stages (`A3`, the first evaluator probe), the mechanism checks and both
held-out checks are **post-hoc** and labelled as such wherever they appear.
`A4` and `A5` were pre-registered after the post-hoc stages had already failed
or come back uninformative, on the same 80 stored rules.

No search, no game, no fitness run, no new rule family. Every number below is
read from the stored result files listed in
`docs/research/data/profile_transform_invariance_20261018/`.

## Question

Two generated rulesets can differ by a board symmetry and still be the same
game up to relabelling. If the static profile is a function of rule structure,
such a pair must receive identical prices, and a consumer could de-duplicate
them. If it does not, the profile is reading an absolute orientation that the
rules themselves do not distinguish. The related question is whether the
served *evaluator* follows the same symmetry, since the profile is only one
ingredient of a leaf score.

The transform used throughout is a 180-degree point reflection,
`sigma(idx) = n*n - 1 - idx` (row-major indices), applied to movement atoms,
the initial position, and the `empty_forward_mobility` masks, with the type-id
map kept as the identity so per-type values can be compared directly.

## Stage 1 — the pre-registered design (`plan.json`, SHA-256 `9892ac75…`)

| item | value |
|---|---|
| inputs | 80 stored rulesets: seeds 292001–292040, board sizes 6 and 8, `classic_like` setup |
| transform A1 | rotate movement atoms only |
| transform B | rename type ids only |
| endpoint | per-type `normalized_board_value`, `normalized_hand_value`, `promotion_option_value`, `median_non_anchor_value` |
| pre-written rule | all supported comparisons exactly equal ⇒ invariant; unsupported rules recorded with the exact error, never fabricated |
| cost | 4.5 s, no search |

**B, the type-relabel control, passed cleanly**: 80/80 rules compiled,
440/440 type comparisons raw-exact, maximum absolute delta 0.0, no
drop-term changes. Renaming types does not move the profile, as required for
any later claim that compares per-type values.

**A1, rotating atoms alone, was `inconclusive`.** 73/80 rules compiled and
produced 403/403 exact matches with delta 0.0, but 7 rules refused to compile
at all with `INITIAL_NO_LEGAL_MOVE` (seeds 292003, 292012, 292016, 292029,
292031 at board 6; 292012 and 292029 at board 8). The reason is structural and
was *not* repaired inside the pre-registered run: rotating the movement atoms
without rotating the stored initial position and mobility masks leaves the
pieces facing the wrong way, so no legal move exists. 55 of the 73 compiled
rules also changed their drop term, another sign that the half-transform does
not commute.

The pre-registered endpoint therefore did not fire. Reporting "invariant on
73/80" would have been a selection claim, because the 7 failures are not
missing data — they are a counter-example to treating the transform as an
isomorphism of the rule *encoding*.

## Stage 2 — the full rotation (post-hoc, `plan_a3.json`)

Because A1's failures pointed at omitted state, A3 rotates the complete rule
geometry: atoms, initial position, and the compiled forward-mobility masks.
The decision rule was written before this second run but after A1 had failed,
so it is post-hoc relative to the original pre-registration.

`rotation_is_a_rule_isomorphism_and_profile_invariant`:

| check | result |
|---|---|
| compile | 80/80 |
| one-ply legal-action bijection at the initial position | 80/80 rules, 2,327 actions |
| signature failures | 0 |
| per-type profile comparisons | 440/440 raw-exact, max absolute delta 0.0 |
| rule fingerprints | all 80 changed, so the transform is not the identity |

The rotation is therefore a genuine relabelling of the rules, and the profile
is invariant under it. That supports de-duplicating static-value samples taken
from rotated copies of a rule.

The invariance is not because the underlying tables are orientation-free. The
compiled forward-mobility zone is non-invariant in 280 of 280 checked
type-owner entries, across all 80 rules and all five type ids: every rule in
this family is affected. `is_forward` compares absolute ranks, so a rotated
piece's "forward" set is not the rotation of the original set. The profile
still matches because the per-type aggregates it reports are insensitive to
that renaming — a property of the aggregation, not of the geometry.

Scope caveat kept explicit: the bijection check is one ply from the initial
position, not a full game-tree isomorphism proof.

## Stage 3 — first evaluator probe, a null that is not evidence

The first attempt scored the *initial position* of each rule and of its A3
rotation under five configurations. Every difference was zero, which the
pre-written rule would have reported as `evaluator_is_rotation_equivariant`.

That null is uninformative and is recorded as such. On those same 80 initial
boards there are 1,116 non-promoted promotable pieces and **none** is inside
or one step from its promotion zone (measured directly, re-checked here), so
the promotion-potential term is identically zero on both sides of the
comparison. The test never exercised the one term that depends on absolute
orientation. A null obtained where the feature is inactive says nothing about
the feature.

## Stage 4 — placing pieces in the zone (pre-registered, `plan_a4.json`)

A4 therefore relocates one promotable piece per rule and owner to three
kinds of square: inside the zone, one step in front of it, and far from it.
Candidates are chosen deterministically and the mirrored square must be empty
on the rotated board, otherwise the case is recorded as `no_candidate`.

Decision: **`promotion_term_breaks_rotation_equivariance`.**

| configuration | nonzero cases | of |
|---|---:|---:|
| material only | 0 | 348 |
| promotion only | 24 | 348 |
| mobility + anchor, no promotion | 0 | 348 |
| default | 24 | 348 |

All 24 nonzero cases are `in_zone` (24/24 of that kind); `near_zone` (168
cases) and `far` (156 cases) are zero everywhere. The differences take only
the values {-3, 0, +3}, which is exactly `weight * unit` with
`promotion_potential_weight = 3` and `unit = max(1, gain // 1000) = 1` *for
these seeds*; Stage 6 below shows unit 2 giving ±6 on a fresh seed set, so the
value set is a property of the sampled rules and the formula is the mechanism.
Twelve rules produce a difference, split 12 owner-0 and 12 owner-1; the sign is
opposite for the two owners because the evaluator negates owner-1 terms.

Structural record behind those 12 rules: 152 rule-owner records, the original
zone is a 1–3 row band (6, 8, 12, 16, 18 or 24 squares), the rotated zone is
the whole board (36 squares at n=6, 64 at n=8), and `sigma(zone)` equals the
rotated zone in **0 of 152** records. Four rule-owner pairs are recorded
`unsupported` with the reason `no_promotable_type_with_positive_gain_on_board`
and were not replaced by invented data.

### Why exactly three points vanish (post-hoc)

A whole-board zone is not "a zone that contains the piece". With every square
in the zone, *every* non-promoted promotable piece collects the full bonus, so
the term reduces to `weight * unit * (count_0 - count_1)` and stops depending
on where any piece stands. In all 12 affected rules both owners hold the same
number of such pieces, so the term cancels to zero; the relocated piece that
earned +3 (owner 0) or -3 (owner 1) in the original rule earns nothing in the
rotated one. Mechanism check: 12/12 rules balanced, 12/12 term cancels.

So the delta is not a small numerical residue. The rotation turns a positional
term into a constant.

### The mechanism is the atom set, not the transform (Stage 5, pre-registered `plan_a5.json`, then corrected)

The pre-registered A5 predictor failed and is reported as failing. It assumed
the zone band width equals the largest forward rank advance; measured band
matches were 51/226 and rotated-whole-board matches 113/226, giving
`zone_geometry_is_not_explained_by_atom_span`.

Two instrument defects were found and fixed inside A5, both recorded in
`plan-log.json`: every `RayAtom` in this generator has `max_steps = None`, so
the first run crashed on `dr * None`; and the rotated-whole-board predictor had
been coded against the original atom span although the plan defines it on the
rotated span.

The corrected model, written after that failure and therefore **post-hoc**,
matches 226/226 type-owner records:

* the compiler negates owner-1 offsets and `is_forward` uses absolute rank, so
  *both* owners have a forward move from a square iff some atom has `dr > 0`;
  the original zone is the same mirrored band for both owners (verified: equal
  row counts in 113/113 type pairs);
* the band width is the *smallest* positive rank advance (values 1, 2 or 3 in
  this family), not the largest;
* the rotated rule has a whole-board zone iff the original rule has no atom
  with `dr < 0`. All 226 records satisfy this, i.e. no promotable base type in
  this family carries a backward atom.

Because that model was fitted on the same 40 seeds, it was checked
predictively on 12 seeds never used anywhere in this study (292041–292052, both
board sizes): 80/80 band matches and 80/80 rotated-whole-board matches. The
explanation is thus a property of the generator's atom assignment, not a
generic fact about 180-degree rotation.

## Stage 6 — the same consequence on a third, independent seed set (post-hoc)

The model above predicts not only the zone *shape* but what the shape does to
the score: with a whole-board zone the promotion term stops depending on where
a piece stands, so relocating one piece changes the score only when the
original band zone is what it left. That consequence was written down and then
measured on seeds 292101–292112, which no earlier stage used.

The A4 measurement reproduces on them: 14/14 usable `in_zone` cases differ
(`promotion_only`), 0/134 `near_zone` and `far` cases differ, 0 instrument
instabilities, and the decision is again
`promotion_term_breaks_rotation_equivariance`. The predictive link holds 14/14:
a nonzero difference occurs exactly for the cases whose base type has no atom
with a negative rank direction, i.e. the type predicted to get a whole-board
rotated zone. In all 14 nonzero cases the measured difference equals the change
in the summed promotion term computed independently (`+42/-42`, `+33/-33`,
`+30/-30`, `+27/-27`, `+18/-18` on the rotated side), so the effect really is
the constant that stops tracking the piece.

The value set is wider here: `±6` appears next to `±3`, because type `C` in
seed 292108 at board 8 has `unit = gain // 1000 = 2`. The A4 sentence "the
differences take only the values {-3, 0, +3}" is therefore a statement about
those 40 fit seeds, not about the mechanism; `weight * unit` is the mechanism.

Kept as executed: the first run of this check applied the equivalence to all
case kinds instead of only `in_zone`, so 134 near/far cases where a whole-board
zone is predicted but no difference can arise were counted as mismatches and the
run reported `fresh_seeds_do_not_confirm_the_zone_consequence`. The prediction
was mis-specified, not falsified. No measured number changed: the raw first
output is kept as `results_zone_effect_heldout_first.json` and its hash sits in
the corrected file's `instrument_error` block.

## Incidental source-level finding: the half-bonus branch cannot fire

`Evaluator._promotion_bonus` awards a half bonus when a piece's forward targets
reach the zone: it tests `any(t in zone for t in forward)`. `zone` is a
frozenset of integer indices, while the entries of `empty_forward_mobility` are
`Square` objects. Membership is therefore never true: 0 hits as coded versus
4,256 if the same squares were compared as indices, in all 226 type-owner
records checked. The branch is unreachable as written.

Because one dead branch invites the question whether others are dead too, the
whole module was audited afterwards (`audit_leaf_terms.py`, endpoint in
`plan-log.json` before the run). `evaluator.py` contains exactly six `in` /
`not in` comparisons, listed from the AST rather than by hand:

| line | comparison | sides as materialised | reachable |
|---|---|---|---|
| 108 | `idx in zone` | `int` against `int` | yes |
| 112 | `t in zone` | `Square` against `int` | **no, by type** |
| 84, 86 | `anchor_square(…) in attacks[…]` | `Square` against `frozenset[Square]` | yes |
| 97 | `base not in promotion_gain_by_type` | `str` against `str` keys (140/140 promotable records have a key) | yes |
| 135 | `target not in opponent_attacks` | `Square` against `frozenset[Square]` | yes |

So the half bonus is the *only* type-impossible comparison found, and the
served leaf score for these rules decomposes into material + hand + in-zone
promotion bonus + dynamic mobility + anchor escape. The counts are consistent
across two independent scripts: 0 target hits as coded, 6,164 target pairs
that would hit if the target were converted to a board index, and 4,256
squares that would then receive the half bonus — the square-level figure is
the same number the earlier verification reported, at a different granularity.

The anchor-capture penalty in the same module *is* live: over 4,881
constructed states (one piece moved to an empty square of the rule's own
initial board, both owners) the anchor square lay in the opponent attack map
in 400 cases, and in all 400 the served score change against
`anchor_escape_weight = 0` equalled
`weight * ((esc0 - esc1) - 10*attacked0 + 10*attacked1)` exactly. That term is
therefore a real part of the served score, not a dead branch, and any future
rotation or evaluation comparison has to keep it.

The same audit was then repeated on the third seed set, 292101–292112 (post-hoc
extension, same endpoint, same code path through `summarise()`, fit-set numbers
reproduced first): 53 promotable type records, 46 of them with a positive gain,
all 53 with a promotion-gain key; 92 zone records giving 0 coded target hits,
2,648 index-converted target pairs and 1,696 squares that would receive the
half bonus; and 1,453 constructed states with 120 anchor-penalty triggers, all
120 deltas matching the formula. The verdict is unchanged
(`leaf_terms_are_type_live_except_the_half_bonus`, stored as
`verdict_heldout` beside the fit-set `verdict` in the same file). This is a
repetition on unseen seeds, not a new prediction, so it can only show that the
source-level statement is not an accident of the 40 fit seeds.

This is recorded as a source-level observation only. No repair is proposed
here and no measurement in this note depends on the half bonus: A4's
`near_zone` cases are zero for the same reason the `far` cases are, and the
`in_zone` result uses the other branch.

## Stage 7 — do those terms occur on positions that were actually played?

Stage 6 leaves an obvious gap: the study's positions are constructed, so
nothing above says whether the promotion and anchor terms are ever *live* in a
played game. `scan_stored_games_leaf_terms.py` closes that gap for the games
this session already stored, without running any search. It replays the stored
move lists of 182 distinct games (seeds 59–94, board 4, `classic_like`,
`AlphaBetaPlayer` at depth 2 or 3, 20,000 nodes, colour-swapped pairs, the
served/`hand_weight = 0.9` and hand-blind/`0.0` arms plus the served-vs-served
control) and inspects the start position and every position after each move.
The replay is exact: all 182 games reproduce their stored terminal status,
winner and ply count, and 34 further game records were dropped as duplicates
because the same move list appears in more than one stored file.

Over 3,062 positions and 8,083 observations of an unpromoted piece whose base
type has a positive promotion gain:

| branch | observations | share | games containing it |
|---|---:|---:|---:|
| in-zone, live branch (`weight * unit`) | 2,489 | 30.8% | 67 / 182 |
| half-bonus condition satisfied if `Square` were converted to an index | 3,944 | 48.8% | 150 / 182 |
| neither | 1,650 | 20.4% | — |

The anchor-attack penalty is live in play too: the owner-0 anchor lay in the
opponent attack map in 364 positions and the owner-1 anchor in 537, and every
one of the 182 games contains at least one such position.

Two cautions about reading the in-zone share. First, `zone` is defined in the
served code as the squares from which a piece of that base type has *no*
forward move at all, not as a designated promotion rank; a 30.8% share
therefore means "the piece can no longer advance", which is the condition the
code actually pays for. Second, counts are not utilities: a term occurring on
3,944 positions changes the static score of those positions only if the
half-bonus branch were repaired, and this scan establishes neither that a
repair is desirable nor that any chosen action would change. As coded the half
bonus contributes exactly zero, so the practical reading is that the served
evaluator pays the full in-zone bonus on roughly a third of promotable
observations and pays nothing in the other branch that was evidently intended
to pay half.

Scope of the reachability statement: board 4, one generator family, one
starting position per ruleset, and games searched at depth 2–3 with a 20,000
node cap. It says nothing about deeper search, other board sizes or other
generator presets.

One structural comparison, because a small board could inflate that share
(`static_zone_share_boards.py`, same 40 fit seeds, no search): the share of
board squares whose forward mobility is empty averages 38.2% at board 4, 21.7%
at board 6 and 16.4% at board 8 (medians 25.0%, 16.7%, 12.5%). The played
30.8% therefore sits below its own board's structural share rather than above
it, and the structural share falls with board size, so these numbers must not
be carried over to boards 6 and 8 without playing games there.

## What a consumer may and may not conclude

### Does that bonus pay pieces that can promote? (Stage 8)

Occurrence is not promotability. The zone is "no empty forward step", which is
the opposite of a promotion rank, and a piece standing there may be unable to
advance at all. `bind_reachability_to_decisions.py` therefore replays the same
182 deduplicated games - reproducing the Stage 7 counts exactly - and asks
`legal_actions` whether the paid piece has a legal promotion in that position.
The endpoint, and one amendment that adds the comparison, were written before
their runs.

Of 2,489 in-zone payments, 53 (2.13%) coincide with a legal promotion; of the
5,594 promotable observations outside the zone, 782 (13.98%) do. The pre-
registered contrast therefore fires: the not-in-zone rate is 6.56 times the
in-zone rate, so the full `weight * unit` bonus is paid where immediate
promotability is lowest. Every one of those 782 promotion-capable
observations sits in the dead-intent class - the class whose half bonus the
broken comparison never pays - and the 1,650 "neither" observations have no
legal promotion at all. Chosen moves follow the same order: 17 of 267 played
promotions came from in-zone squares, 219 from dead-intent squares and 31 from
neither.

This does not turn the earlier reachability note into a repair proposal, and
it does not make the term's sign or size a strength statement. It does mean
the 30.8% in-zone share must not be read as promotion-relevant activity, and
that any future attempt at this term should target the dead half-bonus branch,
where promotability actually lives, rather than the branch that already pays.
`verify_bind_reachability_consistency.py` re-derives those numbers from the
stored files alone - per-game sums, the class partitions, both rates, the ratio
and the four Stage 7 counts - and fails on a deliberately perturbed copy; it is
a bookkeeping check of two files written by the same scripts, not an
independent measurement.

The small contact share is not a tautology in either direction. The zone is an
empty-board geometry (no advancing destination exists), while eligibility to
promote is a separate compiled set of `(from, to)` pairs that need not be a
forward move, so "in zone" and "can promote here" are independent conditions;
the eight contact cases written into the results file all stand on the mover's
own promotion rank, but only 8 of the 53 were written out and the rest were not
inspected case by case. Why so few of them, and whether search would ever
choose such a promotion, remain unmeasured.

### The 6.56x is a composition average, not a uniform geometric fact (Stage 9)

`analyze_contact_concentration.py` re-partitions the same stored per-game
records by seed and re-aggregates to the published summary exactly (nine
checks, all equal), so nothing here is a new measurement - it is a re-weighting
of the Stage 8 counts to the independent unit. Over the 36 seeds, only 14
contribute any in-zone observation at all and only 7 produce any contact; the
largest single seed supplies 18 of the 53 contacts (34%) and the top three
supply 70%. Inside the 14 seeds that have both arms, 9 show a higher
not-in-zone rate and 5 show a higher in-zone rate.

That split is the informative part. The 5 seeds in which in-zone promotability
is *higher* hold 34 of the 53 contacts from 169 in-zone observations (20.1%),
while the other 31 seeds hold 19 contacts from 2,320 observations (0.82%). The
pooled 2.13% against 13.98% therefore mixes two kinds of ruleset: ones whose
zone is, in practice, the promotion rank, where the full bonus is paid to a
promotable piece about a fifth of the time, and ones whose zone is a blocked
pocket unrelated to promotion. The pre-registered contrast still fires as
written; the sentence it supports has to be the weaker one - *in most of this
panel the zone is not a promotion square* - rather than a uniform "the bonus is
paid where promotability is lowest". Thirty-six seeds cannot support an
interval, and the contacts are repeated plies of standing pieces rather than
independent choices (30 of 182 games contain any contact and one game supplies
9), so neither count nor ratio should be treated as precise.

Allowed, for this generator family and these two board sizes:

* static per-type values may be de-duplicated across a 180-degree rotation of
  the same rule — the profile is exactly invariant;
* an outcome or search comparison between a rule and its rotation is *not* a
  comparison of the same searched problem, because the served evaluator
  changes by `weight * unit` per in-zone promotable piece, which is also a
  change in search ordering whenever that term is active.

Not allowed: strength, playing-quality, utility or outcome claims of any kind;
generality beyond one generator family, square boards 6 and 8, the 40 fit seeds
plus the two 12-seed check sets (292041–292052, 292101–292112),
`hand_weight = 0.9`, one relocated piece per case, and states that are
constructed for measurement rather than shown reachable in play.

### Where the zone excludes promotion entirely (structural)

`scan_zone_promotion_disjointness.py` regenerates the same 36 seeds and asks a
purely geometric question: for a piece's base type, is any paid zone square
also a promotion source square in the compiled rule set? The artifact records a
partition and nothing else - no contact count and no rate - under the endpoint
in `plan_zone_promotion_disjointness.json`, and
`verify_zone_promotion_disjointness.py` recomputes the partition independently
and rejects a copy that carries a contact statistic. Of the 36 seeds, 25 have
at least one promoted-with-gain base type whose paid zone is disjoint from
every promotion source; of the 14 seeds that pay the in-zone bonus at all, 5
(seeds 63, 84, 85, 87, 93) are disjoint for every promoting type they pay.

For those 5 rulesets the in-zone contact count follows from how a contact is
defined and cannot be anything else. An in-zone-versus-outside ratio computed
on them is therefore definitional, not an empirical finding, and is *not*
reported here as evidence. Its only role is explanatory: it is one concrete
mechanism, alongside the seed-level split above, for why the pooled Stage 8
ratio is a composition average over heterogeneous ruleset geometries rather
than a uniform property of this generator.

## UNKNOWN

* whether generated rule families outside `classic_like` also lack backward
  atoms on promotable types, or whether that is specific to this preset;
* whether reachable positions in real games put promotable pieces in the zone
  often enough for the term to matter — partially answered for the stored
  board-4 games (Stage 7: 30.8% of promotable observations are in zone;
  Stage 8: only 2.13% of those in-zone payments have a legal promotion against
  13.98% outside the zone), still open for deeper search, other board sizes
  and other presets;
* whether the half-bonus branch was intended to fire — its unreachability is a
  finding, not a diagnosis, and no behaviour change is proposed from here;
* how often the anchor-capture penalty, confirmed live above, fires in
  reachable play — Stage 7 shows it fires in all 182 stored games, but not how
  much it changes any outcome;
* whether any rotation-sensitive term other than promotion potential exists in
  configurations not measured here (the mobility and anchor terms were zero on
  the initial boards and in all relocation cases).

## Files

Public, sanitized evidence copy (checkout paths replaced by `<repo>`):
`docs/research/data/profile_transform_invariance_20261018/`, with per-file
SHA-256 in `manifest.json` and the provenance of each stage in `plan-log.json`.
The private originals stay in `.local_agent/profile-transform-invariance-20261018/`
and are byte-different only by that path substitution.
