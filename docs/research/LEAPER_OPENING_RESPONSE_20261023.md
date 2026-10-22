# Leaper opening distribution and resource response — 2026-10-23 JST

PRIMARY_SANDBOX / sandbox. User-confirmed pure-Leaper forward/inverse direction;
no default, learner, optimizer, AUX solver or role change. This continuation
separates cheap direct policy separation, opening distribution, resource response
and measured cost. Frozen missing/UNKNOWN slots remain in every denominator.

## Closed original-opening direct control

All 32 registered AB512/FLOOR games finish: 11 wins, 21 rule draws, zero losses;
signed utility 11/32. These are four exposed codes, both controller roles and
four actual FLOOR streams, not 32 independent rule samples.

| A/B masks | Games | AB512 wins/draws/losses | Signed utility |
| --- | ---: | --- | ---: |
| 1/2 | 8 | 2/6/0 | 1/4 |
| 1/3 | 8 | 5/3/0 | 5/8 |
| 2/4 | 8 | 0/8/0 | 0 |
| 4/8 | 8 | 4/4/0 | 1/2 |

Actual cost is 399.967658 seconds, 3,267 controller turns, 1,637 search returns
and 832,408 counted AB nodes. Native legality has 284,007 calls, zero fallbacks
and zero operational failures. The 21 draws are 17 rule-max-ply, two stalemates
and two repetitions; they are not caller timeouts. All eight 2/4 games reach the
rule clock despite an early capture. This does not prove that rule unsolvable.
All 11 available immediate wins are chosen; no selected one-ply danger has a
known safe alternative in the complete root/reply diagnostic. Those checks are
not full WDL labels. Shared Core validates 3,267 actions and 6,681 literal PV edges.

## Incoming short-mate advice: evaluated without changing old fitness

The exact two new Chat comments and five relevant complete threads were privately
saved before assessment. ChatGPT's existing framework remains the user-confirmed
direction. Claude's extra short-mate and deterministic-repetition cautions are
useful diagnostics; its proposed AUX work remains AUX-owned.

On the previous 16-code proposal, all 128 existing cold root returns across all
eight D4 geometries identify the SAME four positive mate-band codes: 26/31,
28/31, 27/31 and 14/29. Their score is 999999997, with a legal three-half-move PV
ending in a win for side 0. The production terminal band is MATE_SCORE minus
search ply. This is a bounded search/PV observation, not a new all-defense proof
or proof that a missing mate-band score means no forced short win. No search or
solver calls were added for this assessment.

| Posthoc stratum | Original 4-stream guided minus control | All 8 geometries, first 2 streams |
| --- | ---: | ---: |
| Positive opening mate band | -1/8 | -11/64 |
| Remaining six codes per group | -7/48 | -11/96 |

The original registered -9/64 primary and -33/256 all-geometry result stay
unchanged. The negative proposal result is not rescued by this stratification.
There is no population significance/power claim, outcome-based deletion, new
short-mate admission gate or assertion that every role must win because side 0
has a mate line. Representation stability here is finite evidence only.

## Frozen shared-opening panels

The four complete existing 4x4 KAB rules keep capture removal, max-ply 128,
repetition 4, full histories, Static evaluation/order, node-only maxdepth64,
ordinary q0/forced-check8, fresh actor/game TT retained within the game and disk
cache OFF. For each code, eight fixed seed draws choose two successive legal
Core actions uniformly in canonical action order; stop on a real terminal, never
reject/replace. Sampling actions is not uniform sampling of positions. The 32
sampled prefixes contain 28 unique full histories, no terminal prefix, and one
five-piece prefix; all others retain six pieces. Rule clocks are NOT reset.
Both controller roles consume exactly the same complete prefix for a given draw.

Resource panel: AB2048/AB512, 64 planned games, expected 2400 seconds, cooperative
whole cap 3300 seconds. All 64 real complete-prefix cold calls precede fitness;
they cost 16.045125 seconds. The sampled-maximum projection is 4968.198701 seconds,
separately retained and above cap. The preregistered empirical full-game estimate
has a different basis; its 2400-second reserve forecast does not guarantee coverage.
No cap extension or new run refills this panel. Five of 32 cold root choices
change with budget; neither budget has a positive mate-band root here. Root
choice/depth changes alone are not utility evidence.

Independent forward-axis panel: AB512/FLOOR on the SAME 32 frozen prefix records,
64 planned games, expected 1000 seconds, whole cap 1500 seconds. All 32 AB512 cost
returns are exact references to the preceding cold calls, not new calls. Its
468.008859-second sampled forecast likewise does not bound later calls.
The inherited `seed_world=code` means different prefixes of one code/role share
FLOOR streams. This is explicit common-random-number coupling, not 64 iid games.
There are 56 distinct prefix/role frames before additional trajectory coincidences;
all duplicate sampling weights and physical costs remain.

One inherited resource-panel hypothesis sentence mentions eight original budget
frames, and its selection prose says roles swap budgets. Those are stale in the
FLOOR registration: its actual frozen question, pairs, 64 slots and inputs specify
AB512/FLOOR. The registration is preserved byte-for-byte with a separate dated
interpretation note. No old-baseline contrast is claimed as that panel's
preregistered primary; no result, slot, seed or cap was changed to repair prose.

## Closed opening, resource, board and material results

All five executed panels close with every planned game: 224 NEW physical games,
18,539 controller turns and no missing/caller-UNKNOWN slot. The following are
separate finite axes, not entries in a fitted quality score:

| Masks | Original 4x4 AB/FLOOR | Prefix AB/FLOOR | Prefix AB2048/AB512 | 5x5 AB/FLOOR | First4-prefix Static/M0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1/2 | 1/4 | 1/8 | 1/16 | 0 | 0 |
| 1/3 | 5/8 | 11/16 | 1/8 | 7/8 | 1/4 |
| 2/4 | 0 | 0 | 0 | 0 | 0 |
| 4/8 | 1/2 | 1/8 | 1/16 | 0 | 0 |
| All four | 11/32 | 15/64 | 1/16 | 7/32 | 1/16 |

The prefix resource panel finishes 6W/56D/2L in 2614.009762 seconds, with 54
unique complete records. Its old fixed-opening reference is 1/4; this new 1/16
is a different opening distribution, not evidence of a universal resource slope.
All 64 actual first search returns match the corresponding cold full-prefix
return in action, score, PV, completed depth, nodes, qnodes and result source.
The two budgets pay 814,344/3,234,912 actual nodes and 383.812694/2186.335625 policy
seconds. Maximum 2048-call time is 13.449150 seconds versus 0.485167 in the cold
sample. Both sides have zero Native legality fallback/operational failures.
History, board/branching and concurrent load confound causal wall-cost attribution.
The 64-game incremental check covers 3,195 actions/17,170 PV edges; its 32.625 CPU
seconds are distinct from the reader's waiting/elapsed clock.

Prefix AB/FLOOR finishes 15W/49D/0L in 834.139159 seconds, with 56 unique complete
records. All eight duplicate prefix/role groups have literal identical final
records. The original 11/32 and prefix 15/64 use different prefix/random-stream
laws; no pure opening-only causal effect is claimed. Core replay covers all
6,444 actions/13,399 PV edges.

The new 5x5 direct panel finishes 7W/25D/0L in 338.110017 seconds. Original 4x4
role/seed frames have exactly the same nominal actor seeds; larger minus smaller
is -1/8. Geometry, full default profile and legal ordering/RNG consumption can
all change. The 1/3 code improves to 7/8 while the other three give zero. Thus the
old eight 5x5 AB2048/AB512 draws do not imply zero cheap AB/FLOOR separation.
No old game is replayed or filled. New validation covers 3,351 actions/6,158 PVs.

The material panel was frozen on FIRST FOUR prefix indices per code before any
of its fitness: 16 unique complete starting histories, both roles, 32 games.
Both arms use the same three-method adapter and common Static ordering. Static
finishes 4W/26D/2L, signed 1/16; all net gain is the 1/3 code (1/4). All 32 full
records differ. The old original-opening eight draws remain unchanged. Actual
2282 turns cost 590.446592 seconds; Static/M0 pay 581,558/580,929 nodes and
267.030045/290.537999 policy seconds, with zero Native fallback/operational
failures. This is finite leaf-material utility, not learning, optimal prices or
a generic winner. The 2,282 actions/10,468 PVs pass full replay.

There are 127 NEW cost calls: 64 prefix-resource, 32 material and 31 next-proposal.
Reused cost returns are never counted again. Preparation seconds measure the
recorded script phase, not all Agent design/document/publication overhead. Whole
resource/cost forecasts and old sampled projections remain separately available.


## Actual caller defect and scope

A new contract test first fails because run() discarded a nonempty initial_record
and constructed GameSession(c) at ply 0. The intended scientific input was a
complete shared opening, not a new initial-position rule. Run now replays that
record; the qualifier validates its preserved prefix and only zips new suffix
queries, and the portrait starts at the same replayed state. Original empty
records retain behavior. The test observes ply 2 before the first new action,
checks both controller roles and runs full qualification/portrait. Fifty-two
related tests pass without changing the expected contract. An initial system
pytest temp-directory permission failure was separated from the real red test
by using an ignored project-local basetemp. Product Core/search/evaluation are
unchanged. Original-opening actual producer bytes are preserved separately from
the new prefix producer, rather than silently relabeled current source.

Portrait plies are absolute rule plies; queries and captures describe the played
suffix, not the random prefix. Packet replay is shared production Core and strict
serialization, not an independent WDL engine. Only immutable newly completed
resource receipts are incrementally validated; wait time is explicitly separate
from verifier CPU work. Operational failures, partial games and missing slots
must remain visible.

## Research implication and literature boundary

Do not revive the failed upper-degree proposal, optimize earliest wins or choose
a universal quality scalar from these exposed results. Preserve all four axes,
including missing direct/resource/learning information, role effects and cost.

[Browne and Maire, Evolutionary Game Design](https://cambolbro.com/cv/publications/ciaig-browne-maire-19.pdf)
separates rule features, outcome viability and trends in play, and uses random
legal opening moves. This supports checking an explicit opening law. Its
human-aesthetic coefficient fitting and administrative abandoned-as-draw
convention do not transfer to this project: no human fit, new weighted objective
or relabeling of caller UNKNOWN is adopted. The paper is context, not validation
of our controller quality or small generated domain.

## Next step already begun, with zero fitness

The remaining metadata-exposed original-layout pool has 310 codes after the
previous 60+16 exclusions. A new explicit hypothesis requires each A/B empty-4x4
movement graph connected, total mean degree in [6,12], and min/max degree at least
1/2. It leaves 58 eligible codes. This is hypothesis generation from exposed
findings, not demonstrated quality or an independent holdout.

A separate before-selection registration then draws eight uniform controls FIRST,
then eight feature-guided codes excluding controls, with fixed generator seed.
All 16 complete inputs round-trip, compile and retain zero initial one-ply wins.
Thirty-one NEW initial/natural-eight-ply cost returns are qualified; one natural
cost prefix terminates early and is recorded, never replaced. Each group has one
positive opening mate-band root; those diagnostic strata precede fitness and do
not change membership or prove mate absence. Mean degree is 11.1875 for controls
and 9.84375 for guided, with overlap; this is not a clean one-feature causal test.

The next 128-game direct AB512/FLOOR plan is PREPARED / ZERO FITNESS, expected
2100 seconds with fixed 2700-second cooperative whole cap. The primary is written
unambiguously as guided mean signed direct utility minus control mean over all
64 planned cells in each group, retaining completion intervals. No score fitting,
new admission/default, learner, extra worker or old frozen-panel refill follows.
Execute its saved run on the next segment after source/input/stops checks.

## Technical delivery and acceptance

[The compact packet](data/leaper_opening_response_20261023/README.md) is 4,393,171
compressed bytes (SHA256 d5d4df3b3c88246caf16c87c82993e5c136a83a6ac0ea864d8d8fa5c132a93b3).
Actual exported replay passes 224 games, 18,539 actions, 53,876 literal PV edges
and 6,523 FLOOR policy/stream checks. There are no RNG-policy turns in these
panels; the zero RNG-policy count is not a missing FLOOR-stream validation.
Another 66 allowlisted files match private originals exactly in value; all 104
complete inputs round-trip with matching fingerprint/initial history. Exported
cost records pass 792 literal PV edges and the material copy repeats all 116
component checks. Source capsules retain exact UTF-8 byte hashes. Exact private
originals are untouched; the technical JSON has its own canonical serialization.
This uses shared production Core and is not an independent WDL certificate.
Fifty-two related regression tests passed before publication. The existing tested
publisher remains the required final delivery gate. Science remains OPEN.
