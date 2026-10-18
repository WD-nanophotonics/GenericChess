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

### Why an in-zone promotable piece has no legal promotion (Stage 11, replay only)

`scan_zone_promotion_source_classification.py` replays the same six stored game
files as Stage 8: 182 games, 34 duplicate move lists dropped, 3,062 positions,
and every replay reproduces its stored terminal status, winner and ply count. It
adds no games, no search and no evaluator change. The partition and the decision
rule were written in `plan_zone_promotion_source_classification.json` before the
run, with one amendment that is also timestamped before the run and derived from
`movegen.py` rather than from a result.

The observations are identical to Stage 8: 2,489 in-zone paid observations and
53 contacts. Of the 2,436 non-contacts, 1,281 are observations of a piece that is
not to move. `legal_actions` only ever contains moves of the side to move
(`generic_chess/core/movegen.py`), so an idle piece cannot be a contact by turn
order; those cases are named `would_promote_but_not_to_move` and are kept out of
the decision rule as descriptive only.

On the 1,155 non-contact observations of pieces that are to move, the
pre-written rule fires `missing_contact_is_mostly_zone_geometry`:

* 969 (83.9 %) — the paid square is not a promotion source for that base type at
  all in `compiled.promotion_allowed`, so the compiled rules never allow a
  promotion from there;
* 174 (15.1 %) — the square is a source, but no pseudo-legal move from it reaches
  an allowed promotion destination (338 observations in the whole set have no
  move from the square at all, 40 have moves but none to an allowed promotion
  destination);
* 0 — the destination is allowed and reachable but every promotion target type
  has zero empty mobility there;
* 12 — the promotion variant is pseudo-legal, alive and allowed, yet absent from
  `legal_actions`.

The 12 are not promotion-specific. In every one of them the unpromoted sibling
move from the same square is also absent from `legal_actions`, so the
anchor-safety filter refuted the parent move and its promotion variants with it;
there are 0 cases with a legal unpromoted sibling and 0 forced-promotion squares.
The zero in the dead-target row is measured on geometrically reachable
destinations and also has no library-side counterpart, because
`movegen._promotion_variants` only emits a variant whose target type has mobility
there.

What this changes is the reading of the Stage 8 contact count, not its size. For
most of the observed mass the bonus pays at squares from which the compiled rules
cannot promote at all, so the zone term and the promotion term should not be
expected to coincide on these rulesets; a minority is destination-side, where the
same rulesets can bind promotion in principle and the absence belongs to the
position. It is still not a rate contrast: nothing here compares in-zone with
outside-zone, and nothing here shows that any term changed a chosen action, an
outcome or a strength. Scope: board 4, `classic_like`, these six stored files.

`verify_zone_promotion_source_classification.py` re-implements the start walker,
the geometric destination enumeration and the bucket derivation without importing
the scan under test, and reproduces every bucket count with 0 replay mismatches;
its 14 checks pass and its output is published as
`verification_zone_promotion_source_classification.json`. One defect was found
and fixed before publication: the first private run cached the promotion table by
`id(compiled)`, and because each game builds a fresh ruleset whose id can be
recycled, one ruleset's promotion table could be reused for another seed — seed
77 lost cases. An independent per-case probe reported 8 pseudo-legal-but-illegal
promotions in seed 77 while that run reported 6, which is how the leak surfaced.
The cache is now keyed by `compiled.ruleset_fingerprint`; both discarded runs are
recorded by SHA-256 in `defect_corrections` and no number from them is used.

#### The two seeds the disjointness artifact left open

`results_zone_promotion_disjointness.json` carries the nonclaim that seeds whose
zone does intersect a promotion source yet show no in-zone contact are not
explained by that artifact, and names seeds 61 and 72. The same replay
accounting settles both on the stored corpus, again with no new games and no
search:

* seed 61 — four stored games, 32 in-zone paid observations, 0 contacts. All 32
  belong to the side to move and all 32 sit on squares that *are* promotion
  sources, but no pseudo-legal move from them reaches an allowed promotion
  destination.
* seed 72 — six stored games, 17 in-zone paid observations, 0 contacts. Twelve
  belong to the idle side and so cannot be contacts by turn order; the other 5
  are sources without a reachable allowed destination.

Neither seed contributes an observation to the dead-target bucket or to the
anchor-safety bucket, so on these two rulesets a zero contact count is still
forced by the compiled promotion pairs and by turn order rather than left
unexplained — but the mechanism is destination geometry and turn order, not the
absence of a source square that dominates the pooled mass. This is a statement
about the stored observations only: it compares no in-zone observation with an
outside-zone one, and it shows nothing about what search would choose or about
strength.

### Was the promotion actually played at those 53 contacts? (Stage 12, replay only)

`scan_stage12_contact_choice.py` replays the same six stored files once more and
asks a narrower question than Stage 11: at a contact, was the move the stored
game actually played the promotion from the paid square, another move from that
same square, or a move from a different square? The endpoint, the three classes
and the decision rule are in `plan_stage12_contact_choice.json`, which was
written before the run; no game, no search and no evaluator change is added.

The contact set is unchanged (53 contacts over 182 games, 34 duplicate move
lists dropped, 0 replay mismatches, every played move legal in the
reconstruction). The partition is 17 / 1 / 35 / 0:

* 17 — the played move *is* the promotion from the paid square;
* 1 — the played move leaves that same square without promoting;
* 35 — the played move comes from a different square;
* 0 — contacts with no recorded successor (the last ply of a game).

The pre-written rule therefore fires `contact_choice_is_mixed` (the leading
class is below half the contacts). The mass is also seed-concentrated in the
same way the Stage 9 re-partition showed: seed 77 contributes 4 promotions and
nothing else, seed 80 contributes 8 promotions against 10 moves elsewhere,
seed 90 4 against 2, seed 94 1 plus the single same-square non-promotion
against 11 elsewhere, and seeds 65, 68 and 89 contribute only moves from other
squares. `verify_stage12_contact_choice.py` rebuilds each position from the
stored move list with its own walker, re-derives the contact set and the class
of each played action without importing the scan, and reproduces all four
counts, every per-seed row and the decision; its checks pass and it writes
`verification_stage12_contact_choice.json`.

The reading is deliberately narrow. A played move is not a counterfactual: a
contact only says that a promotion from the paid square was legal in that
position, so choosing something else does not show that the promotion was
worse, that the zone term caused the choice, or that any outcome would have
changed. These 53 events are repeated plies of standing pieces in 30 of the 182
games rather than independent decisions. This artifact also carries no
in-zone-versus-outside rate, and the verifier rejects the withdrawn marker if it
reappears. What it does establish is that the stored corpus contains realised
promotions from paid squares (17 of 53), so a future cost-bounded utility
endpoint can build on stored events instead of having to construct every
counterfactual from scratch - and that such an endpoint is still required,
because availability is not selection.

### Was the played promotion a forced move or an eligible choice? (Stage 13, replay only)

Stage 12 counts what was played but not whether an alternative existed. If the
promotion from the paid square had been the only legal action at those 17
contacts, the record would carry no preference information at all: a forced
move is what any search plays. `scan_stage13_option_set.py` therefore replays
the same six stored files a fourth time, rebuilds each contact position and
lists its complete legal action set, with the endpoint and the forcedness
classes fixed in `plan_stage13_option_set.json` before the run.

The replay precondition is unchanged (182 games, 34 duplicate move lists
dropped, 0 replay mismatches, every played move legal in the reconstruction,
the contact total reconciles with Stage 12's 53). The result is
`no_played_contact_promotion_was_forced`:

* 0 of the 17 played contact promotions were the only legal action;
* 17 of 17 had at least one unpromoted sibling move from the same paid square;
* 0 contact positions had a single legal action, and legal-action totals across
  the 53 contacts run from 3 to 22;
* the paid square itself offered 2 actions in 4 of the 17 played promotions and
  3 in the other 13.

`verify_stage13_option_set.py` rebuilds the positions and their option sets
from the stored move lists without importing the scan, matches every event row
and every per-seed row, and reproduces the decision - 15 checks, all passing,
written to `verification_stage13_option_set.json`.

What this changes is only the precondition for reading Stage 12: those 17
events are *optional* promotions under this evaluator, so they are eligible
choice data rather than forced transitions, and the class partition is not an
artefact of zugzwang-like single-action positions. What it does not change is
the interpretation. Availability is not selection, a chosen action is not a
counterfactual, an overlapping optimal set or a tie in the depth-2/3 search can
produce the same single chosen action, and nothing here measures the value of
the promotion, the effect of the zone term on the choice, or strength. The
forcedness classes also describe one evaluator at depth 2-3 on board 4; a
deeper or differently weighted search would see different option sets
altogether. This artifact carries no in-zone-versus-outside rate and the
verifier rejects the withdrawn markers if they reappear.

### Does every zero-contact seed have a named structural closure? (Stage 14, re-read only)

Stages 10 to 13 left three seeds with a zero contact count and no stated
reason. That is an open loop: an unexplained zero is indistinguishable from a
measurement that failed, so the next step is bookkeeping, not new search.
`analyze_stage14_seed_closures.py` adds no compute at all - it reads the stored
per-seed rows of Stages 10, 11 and 12, re-aggregates them against the published
globals, and assigns exactly one closure class per seed using the six-class rule
and decision rule fixed in `plan_stage14_seed_closures.json` before the run.

The re-aggregation reconciles first: the per-seed contact counts sum to 53 and
the recomputed buckets reproduce the published ones (53 contacts, 1,972
zone-geometry-no-source, 378 no-reachable-allowed-destination, 0 dead promotion
target, 12 filtered by the parent move's legal-safety rule, 74
would-promote-but-not-to-move). Of the 36 seeds examined, 14 carry in-zone paid
observations and all 14 are explained by the decision
`every_zero_contact_seed_has_a_named_structural_closure`, with no seed left in
an unexplained class:

* 7 `contact_observed` - seeds 65, 68, 77, 80, 89, 90, 94;
* 2 `source_present_but_no_allowed_destination` - seed 61 (32 observations from
  24 zone squares that are all promotion sources, every one with no reachable
  allowed destination) and seed 72 (17 observations from 8 source squares: 5
  destination-blocked and 12 where the piece could promote but the move played
  in the record was not the promotion);
* 5 `zone_disjoint_from_every_promotion_source` - seeds 63, 84, 85, 87, 93,
  the same 1,312 observations already described as structural above, where a
  contact is impossible by construction rather than merely unobserved.

One defect was caught before anything was written up. The first run read the
observation count from the Stage 11 per-seed row, where that key does not exist,
so it silently compared against zero and labelled all 14 seeds
`no_in_zone_observation`. That class covers every seed, which contradicts the
53 contacts stored in the same file, so the output was discarded and the count
is now read from the Stage 10 row with the buckets still taken from Stage 11.
The correction is recorded in the results file's `defect_corrections`, the
numbers did not change as a result, and the wrong output was never published.
`verify_stage14_seed_closures.py` re-implements the rule from the three source
files instead of importing the analysis, reproduces every per-seed class and the
decision, re-checks the bucket re-aggregation, and rejects the withdrawn rate
markers - 8 checks, all passing, written to
`verification_stage14_seed_closures.json`.

What this buys is a closed ledger, and nothing more. A closure class says why a
contact could not arise in that seed; it is not a valuation, and it does not make
the surviving contacts more informative than they were. Re-reading three files
written by the same scripts is bookkeeping, not independent measurement, and the
numbers inherit whatever error the earlier stages carry. No in-zone-versus-
outside rate is produced - the withdrawn 0-versus-53 contrast stays excluded and
the verifier rejects its markers if they reappear - and no strength,
playing-quality, utility or causal claim follows. Scope remains board 4,
`classic_like` and the six stored Stage-8 files.

### Is the board-4 exclusion a small-board artefact? (Stage 15, geometry only)

Every measurement above is board 4. With Stages 10 and 14 now resting the
zero-contact seeds on zone geometry, the obvious objection is that a 4x4 board
may simply be too small for a paid zone to meet a promotion source. If so, the
low in-zone contact rate would say nothing about larger boards and the next
valuation step should move there; if the exclusion persists, it is structural
for reasons independent of board size. `scan_stage15_board_scale_zone_disjointness.py`
answers that by regenerating the *same* 36 seeds at board sizes 4, 6 and 8 with
`classic_like` and recomputing the identical partition - no search, no replay,
no new games, ruleset regeneration and set arithmetic only. The endpoint, the
three boards, the two-measure decision rule and the handling of an unsupported
board were fixed in `plan_stage15_board_scale_zone_disjointness.json` first.

The disjoint share shrinks with board size but far too little to call the result
an artefact: 25 of 36 seeds at board 4 (0.694), 22 at board 6 (0.611) and 20 at
board 8 (0.556). The pre-written rule fires
`disjointness_persists_across_board_sizes`, since both larger boards stay above
three quarters of the board-4 share. The same picture appears in the continuous
measure: the median seed's share of zone squares that are promotion sources is
exactly 0.0 at all three sizes, so the typical ruleset still has no promotion
source anywhere in its paid zone. `verify_stage15_board_scale_zone_disjointness.py`
regenerates every ruleset through its own `Square.rank`/`Square.file` index
arithmetic rather than the scan's helper, matches all 108 seed-by-board rows,
re-derives the decision from the stored shares, and cross-checks the board-4
disjoint set against the separately published Stage 10 list (25 seeds, equal) -
8 checks, all passing.

The limit is that this is geometry, not behaviour: it says whether a promotion
action can exist on an in-zone square, not whether search would choose it, and
not what the zone term is worth. Larger boards give both bigger zones and more
sources in absolute squares, so the modest decline is consistent with a mild
dilution rather than a qualitative change, and nothing here rules out a
different preset behaving differently. No contact count and no in-zone-versus-
outside rate is produced, and no strength, playing-quality, utility or causal
claim follows. Scope is boards 4, 6 and 8 with `classic_like` only.

### Is the exclusion specific to one setup preset? (Stage 16, geometry only)

Stages 10, 14 and 15 all measure one preset, so the natural companion objection
is that the zone/promotion-source exclusion is a property of `classic_like`
rather than of the generator. That matters for scope: if the exclusion is
generic it can be stated for generated rules generally, and if it is
`classic_like`-specific then every earlier structural sentence has to be
narrowed and the next valuation step should sample presets instead of boards.
`scan_stage16_preset_dependence_zone_disjointness.py` holds the board at 4
(Stage 15 already varies it) and regenerates the same 36 seeds under
`classic_like`, `bilateral_random` and `free_random`, recomputing the identical
partition - no search, no replay, no new game, ruleset regeneration and set
arithmetic only. Endpoint, presets, the explicit `reference_preset` and the
two-measure decision rule were fixed in
`plan_stage16_preset_dependence_zone_disjointness.json` first.

The disjoint share is 25 of 36 seeds under `classic_like` (0.694), 27 under
`bilateral_random` (0.750) and 25 under `free_random` (0.694); the median seed
has no promotion source anywhere in its zone under all three, 16 seeds are
disjoint under every supported preset, and no (seed, preset) pair failed to
build. Both non-reference shares exceed three quarters of the reference, so the
pre-written rule fires `disjointness_is_generic_across_presets`. One
definitional caveat is worth carrying: a seed whose promotable types have no
zone at all is counted as disjoint, since the intersection is empty, and that
count differs by preset (6, 10 and 5 seeds respectively). Recomputed without
those vacuous cases the shares are 19/36, 17/36 and 20/36, the smallest ratio to
the reference is about 0.89, and 9 seeds rather than 16 are disjoint with a
non-empty zone under all three presets - the decision does not depend on the
empty-zone seeds. Those two numbers are a re-read of the stored
`per_seed_preset` rows, not a new run.
`verify_stage16_preset_dependence_zone_disjointness.py` regenerates every
ruleset through its own index arithmetic rather than the scan's helper, matches
all 108 seed-by-preset rows, re-derives the decision from the stored shares and
cross-checks the `classic_like` column against the separately published Stage 10
disjoint list (8 checks, all passing). The first run of the scan is kept as a
defect: it read the plan's prose `reference` field as if it were a preset key,
so the lookup always failed and the decision fell through to
`insufficient_supported_presets` while the same run printed three complete
preset summaries; the plan now carries `reference_preset` and the thresholds
are unchanged, no measurement moved and the wrong output was never published.

The limit is the same as Stage 15's, with a second edge. This is geometry, not
behaviour: it says whether a promotion action can exist on an in-zone square
under each preset, not whether search would choose it, and not what the zone
term is worth. The other two presets were regenerated, never played, so
reachability in play remains entirely unmeasured for them and nothing here says
they are balanced, playable or comparable to `classic_like` as games. No contact
count and no in-zone-versus-outside rate is produced, and no strength,
playing-quality, utility or causal claim follows. Scope is board 4 with the
three presets the generator offers at this place in the code.

#### The shares are aggregate; the seeds are not

`disjointness_is_generic_across_presets` is a statement about the regenerated
rule population, not a per-seed invariant, and the gap is large enough to
matter. Classifying each seed on the stored `per_seed_preset` rows as vacuous
(no zone), disjoint with a non-empty zone, or intersecting, 20 of 36 seeds
change category between `classic_like` and `bilateral_random` and 15 between
`classic_like` and `free_random`. The played stratum is also not a typical
sample of the panel: the 14 seeds that carry in-zone paid observations are 5/14
disjoint under `classic_like` against 19 of the panel's 30 non-vacuous seeds, a
gap of about ten seeds of 36 that survives excluding vacuous seeds; under
`bilateral_random` three of the seven contact seeds have no zone at all. Only
`classic_like` was ever played, so none of this contradicts the decision, but it
bounds what the decision says: the exclusion is not a `classic_like` artefact
in aggregate, and it is neither a property of the same seeds under other
presets nor a property of the stratum that produced the contact data. Those
contact seeds classify as intersecting under the played preset, which is the
definitional side of the Stage 10 statement - a disjoint seed cannot contribute
a contact - and not an independent confirmation of it. Every count in this
paragraph is a read-only join of two already-published tables: the
`in_zone_paid_observations` field of the Stage 14 rows and the `zone_squares` /
`zone_disjoint_from_every_promotion_source` fields of the Stage 16 rows. No
search, replay or new game was run.

The same join against the Stage 15 rows shows the board axis is the steadier
one, and that the played-stratum gap is not a preset artefact either. Changing
the board from 4 to 6 or to 8 moves 10 of 36 seeds between categories, against
20 and 15 for the two presets, so 26 of 36 seeds keep their classification; the
seven contact seeds keep theirs at all three sizes and stay intersecting. The
played stratum is again the minority case, in the same direction and at a
similar size: 5/14, 4/14 and 4/14 disjoint against 19/30, 20/34 and 19/35 among
the panel's non-vacuous seeds at boards 4, 6 and 8, gaps of about -0.28, -0.30
and -0.26, and all 14 played seeds have a non-empty zone at every size. So the
seeds that produced play are consistently less disjoint than the panel across
both axes, while the contact seeds themselves are stable. The mechanism is not
identified here; the gap is reported as a property of this panel, not explained
by it, and no test statistic is attached to 14 or 7 seeds.

#### One tautology this does not rest on

The zone is built from `compiled.empty_forward_mobility[type][owner][idx]`:
a square is in it when the base type has no forward move from there
(`evaluator.py`, zone construction). Promotion eligibility is a separate
generated mask of `(from, to)` pairs (`compiled.promotion_allowed`, validated
as an explicit per-type set), so a promotion source can sit on a square with no
forward move at all - and on the stored rows it does: 11 of the 36
`classic_like` seeds have a non-empty intersection between zone and sources
(9 under `bilateral_random`, 11 under `free_random`), and on seeds 61, 72 and 77
every zone square is a promotion source (share 1.0; seeds 74 and 89 under
`bilateral_random`; seeds 60, 61, 62, 79, 88 and 93 under `free_random`). So
"the zone contains no promotion source" is a majority statement about these
generated rulesets, not an arithmetic consequence of how the zone is defined,
and the disjoint count must not be re-read as "the zone can never hold a
promotion source". Those per-seed counts are a re-read of the same published
Stage 16 rows, with the mechanism checked in the two source files named above;
nothing was re-run.

## UNKNOWN

* whether generated rule families outside `classic_like` also lack backward
  atoms on promotable types, or whether that is specific to this preset;
* whether reachable positions in real games put promotable pieces in the zone
  often enough for the term to matter — partially answered for the stored
  board-4 games (Stage 7: 30.8% of promotable observations are in zone;
  Stage 8: only 2.13% of those in-zone payments have a legal promotion against
  13.98% outside the zone), still open for deeper search, other board sizes
  and other presets — Stage 15 now shows the *structural* availability
  (a promotion source inside the paid zone) also fails on boards 6 and 8, but
  no played positions exist at those sizes, so reachability there remains
  entirely unmeasured — and Stage 16 shows the same structural failure under
  `bilateral_random` and `free_random` at board 4, but those presets were
  regenerated only and never played, so their reachability is unmeasured too;
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
