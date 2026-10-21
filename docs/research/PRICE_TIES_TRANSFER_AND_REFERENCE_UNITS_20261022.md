# Price ties, opponent dependence and reference units — 2026-10-22

No price or search default changes. The new prospective cohort identifies an
opponent interaction, rather than a universal Unit winner. A complete linear
instance-reference table remains a cheap research candidate; its utility is not
established. Product code, Native binaries, public result fields and cache
algorithms are unchanged in this segment.

[summary.json](data/price_ties_transfer_20261022/summary.json) is the short entry;
[evidence.json](data/price_ties_transfer_20261022/evidence.json) contains complete
inputs, 141 new episode records, action/PV projections, protocols, sources,
failures and validation. Every registered RuleSet, GameState and GameRecord was
losslessly decoded and compared with its private original. Selected decision
counters are an explicit projection, not every original diagnostic field. Exact
originals stay ignored locally. Source/old controls are pinned at
[d1017250](https://github.com/WD-nanophotonics/GenericChess/tree/d1017250c8720113000105b7519f6beffa774d0a).

## Policies and the third-opponent result

A = Static leaf, dynamics OFF; C = Static leaf, dynamics ON; D = Unit leaf,
dynamics ON. Unit assigns ordinary board/hand values 1000/900 and anchor 0.
All actors use the same original Static material ordering. Thus D is not a
profile-free agent. Existing dynamic weights are mobility 2, escape 5 and
promotion 3; Unit's derived promotion gain is zero. Qsearch, TT and root tactical
scan are OFF. Full promotion, custody, auxiliary fields and histories remain.

The prepared check executes only 36 new D/A games on the previous 18 exposed
roots, both subject roles. Its 36 C/A baseline frames are exactly the previous
A/C games with subject-role transpose and utility negation. There are 649 new
queries, 36 reused first moves, 16 D wins, 15 losses and 5 UNKNOWN. Requested D2,
512 nodes, 48 total plies and the 180-second batch fuse stay fixed; actual batch
cost is 27.792 seconds. Independent Core replay verifies all 36 new plus 36
baseline frames, 2,943 PV plies and 1,970 final history entries.

D−C against A is **[-4/9, 7/18]**. The old fixed-C result [1/18, 1/2] therefore
remains conditional. Eleven C/A and D/A records are identical and naturally
terminal; none is an identical UNKNOWN. A broader early cancellation explanation
was corrected: identical censored pasts do not identify equal future utility for
different C and D policies. Bounds here are unchanged. Same-whole-policy C/C
role-frame cancellation, and identical-state continuation under the same fixed
Pi, remain valid. Never substitute UNKNOWN with draw.

## Tie advice tested at actual policy divergences

The new incoming Claude comment was saved exactly and its complete thread read.
Its tie/utility distinction is useful; its cited sandbox 5442 predates the later
whole-policy work. Leaper TD/logistic cell scans, enumerator/scaling and AUX's
prefix plan remain in AUX's lane. No reply, @mention or new worker was sent.

Uniform root tie adjudication can be computed from the old complete D1/D2 Core
argmax sets. There are 84 full child states, 44 with existing fixed-Pi receipts.
Every contrast bound still crosses zero. This is one randomized root choice then
a common continuation, not a randomized whole-game policy or a WDL error rate.
No new games or extensions of old censored paths were required.

For the 72 C/D policy pairs against A/C, 50 have an observed first divergence;
22 have the same observed history. All first divergences are on the subject's
turn. Deduplication uses the entire state/history and root owner: 35 states,
62,912 independent Core tree entries. At D2:

| Explanation at the selected divergence | Cases |
| --- | ---: |
| Strict selected-pair reversal, with disjoint full argmax supports | 45 |
| One strict preference and one tie | 3 |
| Unit completed only D1 under its node cap | 2 |

All 100 selected action/score checks match Core at their **actual completed**
depth. Alternate D1 classifications of a completed D2 choice are not bugs. A
separate promotion-bonus ablation uses 61,744 entries: removing promotion changes
none of the C argmax sets; 45 supports remain disjoint. With material alone only
5 are disjoint. The common mobility/escape contribution interacts with different
material tables through minimax. This is conditional on selected divergences,
not all positions, not WDL correctness, and not proof that promotion never matters.

## New-rule prospective check

Before generation, freeze 18 seeds across 4/6/8 boards, three existing presets and
two replicas. Use canonical prefix zero, the same A/C opponents, both roles and
C/D subjects. Every actor requests D4 with 16,384 nodes, q0, no per-query clock,
96 total game plies and a 2,700-second cooperative batch fuse. This changes both
rules and search envelope; it cannot isolate a causal effect of depth.

Fifteen rules generate successfully; three fail the original six-attempt
limit, without replacement. No new fingerprint duplicates an old or new rule;
this does not prove behavioral non-isomorphism. All 4x4 free-random slots fail,
so the accepted cohort is not the intended balanced distribution. Preserve all
126 planned episode slots: 105 executed episodes, 21 missing from generation.

| Accepted 15-rule contrast, both roles | Finite utility interval |
| --- | --- |
| D−C against fixed C | **[-1/15, 0]** |
| D−C against fixed A | **[1/6, 1/6]** |
| Opponent interaction: the second contrast minus the first | **[1/6, 7/30]** |

There are 104 natural terminals (103 checkmates, one rule repetition) and one
batch-censored UNKNOWN after 8 plies. No 96-ply or old UNKNOWN cap is extended.
Hypothetically completing the failed-generation slots gives sensitivity bounds
[-2/9, 1/6] against C and [-7/36, 17/36] against A. A failed generator has no
actual game utility: these are completion sensitivities, not unconditional
18-rule performance. All families, including negative effects, remain reported.

Actual cost: **1,819 new queries, 60 first-query reuses, 15,090,201 paid nodes**;
2,674.466 measured query seconds and 2,701.463 total batch seconds. The 1.463-second
overshoot is the already-running cooperative query, not a chosen cap extension.
Paid completed depths are 1,261 D4, 484 D3 and 74 D2; no claim that every query
reached D4. Native fallback count is zero. C/C slots consume 482.102 paid query
seconds for role-specific and trajectory controls. Their symmetrized baseline is
analytically zero, so a future aggregate-only check need not pay for full C/C
self-play; some initial-query cost would move to another match.

Independent Core replay verifies all 105 full states/histories, 1,984 final
history entries and 6,464 PV plies. Legal PVs alone are not literal-score/WDL
proofs. The optional, hash-ordered actual-depth reference uses its frozen 250,000
entries: 2 of 18 state-depth references complete, matching 4 retained-query
checks. The other 52 checks remain budget-incomplete, including references not
expanded after the fuse; they are not passes or partial reference scores.

## Declaration bias: complete tables without provenance filtering

The old typed-closure prototype passes 16 additional valid fixtures and 5,304
Core edges. Compiler contracts matter: promotion masks include forced masks;
alternate setups preserve the full typed inventory. Public initial hands are
empty. Real same-type and converting drops show that initial closure does not
cover arbitrary positive-stock imports; conversion stays conservative/all-types.
No production type filter or normalizer is activated.

Two explicit candidate routes retain every declared type value:

* R uses rounded relative raw material, 1000(own−other)/(own+other), zero for
  zero denominator, board CURRENT, hand BASE with weight 0.9, and existing
  mobility/escape but no promotion bonus. It is nonlinear in quantities.
* E uses the positive median of raw opportunities contributed by initial piece
  **instances**, including base/current identities and stock counts, as a fixed
  rule-level unit. Every type is still valued; the existing floor/clip and
  promotion-target table remain. Empty positive reference uses the explicit
  raw-unit-one fallback. It is a linear material table with existing dynamics.

Both pass 1,197 paired state-score comparisons under dormant declarations;
these are not 1,197 independent games. R also passes positive-unit lifts 1/161
and 161. A simpler *unique-initial-type* reference also passes declaration tests,
but fails a qualified file-locked type split on all 103 checked history states.
The instance reference passes all 103 states/102 edges. The inverse split is
fixed by file, with no drops, promotion or auxiliary effects; this is not a
universal actor-splitting equivalence claim. Initial-setup permutation and
zero-reference controls pass. Do not infer linear conservation for other splits.

R has 35 retained public queries and 36 complete Core D1/D2 references; one
requested-D1 return was lost and its slot remains missing. E has all 36 public
queries/references; its full argmax supports overlap C at every tested root,
not necessarily a theorem about capped policy equality. Its frozen private
harness uses the local response label R for E; the protocol states that alias.
Reuse of existing Pi receipts identifies D2 R−C = [0,0], while optimal-continuation
bounds remain [-2/9,2/9]. That is not equality of whole R/C policies. No whole-game
utility supports replacing C or D with R/E.

A further *material-only* route accepts raw projected typed-IR profiles without
any legacy handle: six fixtures cover cannon, rectangular 7x5, castling rights,
en-passant auxiliary state, type effects and complete drop history. Eleven
public queries match 1,512 complete Core entries. Excluded semantic patterns and
unvalidated hand scaling remain explicit. Re-unitization initially reintroduced
nonzero hands into two proved-inert projections; the private composition restores
that supplied scope before querying. This is not the earlier full-dynamic E
policy and does not validate every DSL mechanism's price.

The next paired semantic study is actually begun: a dormant zero-movement type
in an auxiliary castling rule preserves original values and all 15 complete
one-ply child/history correspondences without stripping pattern/geometry IDs.
The other fixtures, longer histories and interacting effects remain executable
next work. No generic IR-isomorphism or default-admission API is introduced.

## Failures, capture and delivery limits

The prospective recorder mistakenly accessed `GeneratedGame.report` after the
in-memory contexts were ready. Fifteen metadata AttributeErrors left the input
list empty while those valid contexts continued; three GenerationErrors are
separate. Exact same-seed inputs were rebuilt with the real `generation_report`
field and verified against **every** actual initial record/fingerprint. No game
was restarted. Raw copied pre-execution status is retained separately from final
execution status in the public projection. Both executed and future repaired
sources are clearly labeled; the repaired recorder was syntax-checked, not used
for this frozen cohort.

One requested R query returned before a harness serialization comparison failed;
its result was not saved. It remains one unretained execution, not a zero-query
attempt or a refilled slot. A direct timing probe similarly lost 8,421 evaluations
(401 actual inputs, three warmups and 18 timed batches) before a private metadata
field check. The timings were not rerun, imputed or used for a speed claim.
The original 399-input forecast had collapsed two alias histories; actual inputs
were retained in the diagnosis. Only zero/alternate boundary checks were recovered.

The pure-IR feasibility's legacy-generated carrier failed before its query stage.
Only that failed stage was resumed with the existing legacy-to-semantic adapter;
the ten completed DSL queries were retained, never repeated. Other fixture/API
failures and partial evidence remain in the packet/private originals. No expected
number was changed merely to match output. LOCAL_AGENT now specifies input capture
before context readiness and return capture before downstream assertions.

No application source or Native build changed. Relevant publication tests and
artifact round trips are the delivery gates; the previous 3,598-check regression
is not repeated for unchanged product code. Science remains OPEN.
