# Rule-only static prices and learned decision fidelity â€” 2026-10-17

Keep the existing unfitted rule-only static material table as a cheap comparator.
It improves finite actual outcomes over Unit on this registered four-rule panel.
The frozen learned endpoints change real floating-price preferences, but their
utility improvement over their own initial models remains unresolved. This is
method diagnosis on TRAIN-exposed generated rules, not Elo, unique piece prices,
unseen-rule transfer or a product/default change. No new learner or training ran.

## Frozen question, scope and actual cost

The changed premise was portable Generic endpoint models plus a cheap Native
consumer; previous evaluation lacked the existing rule-only baseline. The plan
was recorded before fitness. Use four original generated 4x4 promotion/drop rules
271001â€“271004, ALL initial/trained models from seeds1977/8173 in AUX89, and
`build_ruleset_profile(EvaluationConfig())` generic-v2 material tables. Static
board/hand integers are divided by1000, explicitly quantized at256 for Native;
no divide-by-P, learned normalization, label fitting or dynamic coefficients.
Unit is the SAME fixed opponent for every candidate and both roles. Rule-only
here means its coefficients use rules rather than these game outcomes; it does
not imply the full existing evaluator or an all-domain price theorem.

Eight new family draws per rule (151001â€“151008) give32 complete starting records,
four uniform typed-binding prefix plies, retaining early terminals and history.
New PRNG streams do not prove distinct states or unseen rules. D2/q0/TT0,
8192nodes and2seconds/query, root-window pruning off; administrative H128 after
prefix. Frozen producer cap600seconds/256MiB, forecast120seconds; no extension.

All352 physical games returned in53.656seconds:306 actual terminals,46 H128
UNKNOWN,0missing. Their384 logical role cells reuse each of32 Unitâ€“Unit physical
records in opposite roles; these are not384 independent executions. Eleven
physical configurations terminate before the first query and are retained.
There are12744 actual D2 queries/2684467nodes,0fallbacks; recorded kernel7.848s,
caller20.552s, maximum caller.007693s. Whole producer time includes Core commit,
hashing and journals; preparation, qualification and analysis cost are additional.
Equal requested limits are not equal actual nodes or universal runtime evidence.

## Actual W/L/D and UNKNOWN

Each row contains64 logical cells, balanced roles on the same32 families.

| Candidate | W | L | D | UNKNOWN |
|---|---:|---:|---:|---:|
| Unit |20|20|12|12|
| Rule-only static |39|17|3|5|
| Initial1977 |36|24|1|3|
| Trained1977 |37|22|1|4|
| Initial8173 |13|31|5|15|
| Trained8173 |13|33|5|13|

Reward is candidate Wâˆ’L in[-1,+1]; every UNKNOWN remains a variable in[-1,+1],
never a draw. Bounds below are finite identification bounds, not confidence
intervals or complete game-theoretic bounds. The separately stated resampling
envelope uses2000 family resamples within these FOUR FIXED exposed rules; seeds,
roles and repeated static cells remain correlated, not128 independent families.

| Paired contrast | Cells | UNKNOWN bounds | Conditional 95% family envelope |
|---|---:|---:|---:|
| Static âˆ’ Unit |64|[.265625,.421875]|[.109375,.59375]|
| Trained âˆ’ own initial |128|[-.265625,.28125]|[-.40625,.421875]|
| Static âˆ’ trained |128|[.171875,.59375]|[-.0078125,.7734375]|

For explicitly reused Unit records, logical reward is `s_owner * Z_physical`.
Aggregate each physical coefficient FIRST, then add Â±absolute coefficient for
an unknown physical result. Opposite Unit roles cancel algebraically, including
six unknown physical games; this does not impute those games as draws. The first
analysis treated these variables independently and gave looser conservative
bounds; both outputs and the explicit coupling derivation are retained. Merely
identical past records under different policies do NOT justify this coupling.

Staticâˆ’Unit per rule is .75/.625/[-.3125,.3125]/0. Staticâˆ’trained per rule is
[.625,1.0625]/[.875,1]/[-.6875,.4375]/âˆ’.125. Rule271004's learnedâˆ’initial contrast
is0: its advantage over static already exists in the initial models, and cannot
be credited to learning. The weak8173 initialization is retained. Static is useful
here, but neither aggregate averages nor these conditional intervals select a
universal method winner or a new installed checkpoint.

## Real preference changes, not just ties or quantization

Among128 learned/own-initial pairs,107 have both outcomes resolved,103 have
identical full records,3 improve and3 worsen. Across all three contrasts there
are165 first divergences. Each occurs on the candidate's turn with the same
full parent hash and fixed foe; it is not caused by jointly changing the foe.

A prospectively bounded first-divergence control selects up to4 unique parent/
profile contexts per rule without reward selection:16 parents/1867 Core visits.
All32 actual choices are optimal under their own quantized D2 value, with exact
scores;10 strict preference conflicts and6 one-sided strict preferences,0 joint
ties. It is a finite D2 check, not WDL or all12744-query optimality.

A separate registered check includes ALL25 learnedâˆ’initial first divergences,
not just winning cases. Independent Core D2 evaluates both original floating
and actually served256 tables (3453 visits). Every Native choice is optimal
under both its own quantized and source-float model;25 floating optimum-set
changes,0 joint floating ties,0 choices outside source-float optimum sets.
Thus the learned differences are real finite preferences. They do not establish
useful learning given the retained paired outcomes above. Keep explicit256 for
this scope; higher precision or a new diagnostics API has no observed need.

## Complete-state reader and preserved errors

Search-disabled Core replay checks all352 root/final records,12744 committed
edges,25193 PV edges, complete history/witness/state hashes and actual rewards.
All12200 ordinary and544 actual-terminal PV scores agree after a reader-only
oracle correction. The first oracle used full-game ply in mate-distance scores,
producing515 residuals. ALL515 equal the signed parent-ply offset: the Native
API uses current-query-root-relative mate distance with root_ply_offset0.
No ordinary leaf mismatch or product defect follows. Corrected reader returns
zero mismatches and zero missing PVs; no fitness rerun or cap change occurred.
A producer syntax error occurred before execution and was fixed before any slot.

The first unpublished capsule omitted a lazy-import rule execution module and
failed immediately in a fresh source tree. That failed package remains private;
the corrected package adds the actually loaded source, preserves data bytes,
parks sealed derived outputs before regeneration, and checks exact non-time
results. Final fresh-source qualification PASSES:202 payload hashes,seven independently
regenerated outputs exactly equal apart from fresh execution times; all five
readers/analyses, an isolated Native build,48 signed consumer calls and613
normalization inputs complete in47.5seconds. See the external qualification
receipt for individual costs.
It never runs the frozen producer. No binary, raw Slack/account output or private
path is included. Qualification costs are not original producer timings.

A subsequent outcome-independent record-scope check compares all32 new root
GameRecords (canonical complete actions/resignation/fingerprint/schema) against
ALL647 unique saved AUX89 TRAIN before/after records, including failed-query
inputs. All32 are mutually distinct and none matches that saved record set
(.047s,0search). This proves only that exact-record distinction: it does not
exclude equal Positions, unrecorded TRAIN exposure or shared rules. No root was
filtered, regenerated or relabeled as holdout. The executable post-seal script,
prospective question and result are in the compact data folder; fixture/source
roots already reside in the sealed capsule.

## New AUX90 evidence: actually executed, and what changed

Published AUX90 report final340694acff94ccdfbc9ed06d42faa55066aad26b was read;
source6ab620e7423cfe01b64f28a8b030ab998f635cc1 capsule SHA256
c682ab793866421f014c3b81ec730747265ffca26cba78449d1aecee787d55a0.
PRIMARY verified196 payload hashes, ran38 owner controls and regenerated NINE
owner-authored audits after parking their sealed outputs. All non-time fields
match;107984 logical legal plies,78.264s. The private dispatcher binds the stop
reader to actual PRIMARY flags and verifies extracted module origins. This is
actual owner-source reproduction, not PRIMARY-independent mathematics; original
training/EVAL is not rerun. Its48 D2 and2 component verification queries are not
new fitness. AUX checkout, running91 and unpublished code remain untouched.

The new90 plainD2 curve records4M TRAIN nodes,4697 episodes/4628 terminal69U,
3098 updates;1971.885s. Uniform EVAL has512 cells/475 terminal37U; random-foe EVAL
has512/495 terminal17U. Final trainedâˆ’initial bounds are[0,.25] and
[.2265625,.3671875], but descriptive family/seed envelopes both cross0. Foe-switch
interaction[-.0234375,.3671875] includes0, not opponent invariance. These differ
from the small89 models used in OUR study: do not compare their unmatched fitness
as a method effect. Roots remain four exposed rules; new draws include four
TRAIN overlaps and four already-terminal roots, all beginning densely occupied.

The separate published post-seal leaf-span audit was also actually executed.
Exact free-coordinate PV ranks are5/5/5/5; rules002/004 now contain2153/2120
board-A â‰  hand-A leaves, with199/265 actual episode null-component drifts.
The old89 short-sample rank5/4/5/4 is not a permanent representation gate.
New stream, initializations, work and horizon differ; this is not a pure
more-data ablation or proof of unique prices, convergence or full-domain transfer.
The six-free-model component preflight releases P and demonstrates a finite
P update; it is not six-free learning benefit. AUX91 owns the actual paired study.

The new91 request and its complete Dot reply were read, not unpublished source.
Adopt the design caution for any FUTURE consumer: candidate-turn TD uses one
frozen per-episode theta and a declared candidate-decision clock, white-oriented
predictions/targets/outcome; candidate utility flips sign for black only in WDL
acceptance/reporting. Charge both candidate and foe searches, both WDL proposals
and baselines, and failed work. This is reference design reasoning, no change to
current91 or a new PRIMARY learner. A conservative WDL acceptance rule tests only
that frozen operational learner, not impossibility of terminal feedback.

## Delivery and next decision

The exact plan, models, roots, slots, all game/query journals, scripts and scoped
backend source are in `../archive/rule_only_static_comparison_20261017/evidence.zip`.
Its sibling manifest lists every payload hash; qualification lists actual restore
execution. Compact outputs are in `data/static_price_comparison_20261017/`.
The producer is provenance only; use the search-disabled readers to reproduce
existing evidence. Do not rerun frozen fitness under its old identity.

Native signed/zero-P serving already works through existing APIs. A future AUX
query accelerator must preserve AUX's optimizer: PRIMARY median normalization
changes294/613 old ordinary predictions at fixed scale10 (max.2406709681).
The new portable normalization companion and exact89 input in this capsule
reproduce this distinction; joint coefficient/temperature rescaling equality
is NOT fixed-learning-rate training equivalence. No adapter is activated here.

Retain static and learned candidates, actual outcomes and per-rule differences.
Next assess the fixed published91 free-P/fixed-P evidence if it becomes available;
otherwise inspect one concrete current consumer dependency, not repeat89/90,
launch competing training, add unneeded precision/API, or fit these evaluation
outcomes. Science remains OPEN; generic target still includes complete generated
promotion/drop/aux/history domain beyond this scoped four-rule diagnostic.
