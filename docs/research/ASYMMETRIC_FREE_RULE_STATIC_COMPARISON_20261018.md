# Rule-only static vs uniform material on six new free_random rules

Task `DEEPSEEK-SHARED-ASYMMETRIC-STATIC-20261018`;
AGENT_ID=PRIMARY_SANDBOX, EXECUTOR_ID=PRIMARY_SANDBOX_DEEPSEEK.
Executed in the PRIMARY checkout at source
[4c665474c176bbb84a32169a540ffbe1521bc6bf](https://github.com/WD-nanophotonics/GenericChess/blob/4c665474c176bbb84a32169a540ffbe1521bc6bf)
on 2026-10-18. Evidence: `.local_agent/asymmetric-static-20261018/`.
Technical inputs, readers and result files are also copied (with hashes,
rerun commands and scope limits) to
`docs/research/data/asymmetric_static_comparison_20261018/README.md`; the
classic4 raw outcome logs are not in Public Git and those rows remain
summary-only there.
No publication of this result has occurred yet; it awaits supervisor review.

### Provenance after the role split (DEEPSEEK_AUX)

The `AGENT_ID`/`EXECUTOR_ID` labels above are **historical**: the 1344 games ran
before the current role separation, through the shared DeepSeek executor in the
PRIMARY mainline checkout at `4c665474...`. The artifacts were then migrated to
the isolated `DEEPSEEK_AUX` worktree (`codex/deepseek-aux`), which owns this
copy, the portable-copy fixes and the public evidence directory. This is
auxiliary work; it is not claimed as PRIMARY-authored or as a mainline
publication, and PRIMARY has not adopted its conclusions. Frozen inputs,
outcomes and their hashes were not regenerated during migration.

## Question and changed premise

The closed mature-static comparison (`MATURE_LEARNED_PRICE_AND_STATIC_COMPARISON_20261017.md`)
found rule-only `rule_static_v2` material useful versus uniform material on
exactly four TRAIN-exposed bilateral `classic_like` 4x4 rules (271001..271004).
That evidence therefore covers one narrow mechanism class. The generic target
explicitly includes unfamiliar mixtures and recombined/generated movement, so
the premise "rule-only static is a cheap generic comparator" is untested outside
it.

This run is a **bundled sampled-domain change**, not an isolation of one factor.
Relative to the preceding mature-static comparator it changed board size
(4 -> 5), setup (`classic_like` -> `free_random`), movement symmetry
(left-right-symmetric classic atoms -> `movement_symmetry=none`), the rule seeds
and frozen roots (271001..271004 -> 281001..281006 with fresh fitness-blind
prefixes), and the post-prefix horizon (128 -> 64 plies; both `plan.json`).
The fixed-random foe channel spaces are also unequal: the preceding comparator
used `random99031`, while this run froze `fixed_random99031_channels` in the
free rules' channel space and states explicitly in its `plan.json` that it is
**not** the AUX random99031 vector; absolute channel counts also differ with
board size. Unchanged shared elements: the two profiles (`unit`,
`rule_static_v2`), the uniform foe definition, depth-2 / 8192-node / 2 s search
settings and the UNKNOWN treatment. Any difference from the preceding result is
therefore attributable to this bundle, not to "rule mechanism class" alone.

### What the new rules actually are (measured, not assumed)

`asymmetry.py` reads only the frozen `rules.json` and the compiled rulesets:

| seed | board | pieces/owner | layout 180-deg symmetric | any non-anchor type 180-invariant | any non-anchor left-right symmetric | fwd/back atoms |
|---|---|---|---|---|---|---|
| 281001 | 5 | 10 = 10 | yes | no | no | 4/2 |
| 281002 | 5 | 10 = 10 | yes | no | no | 3/4 |
| 281003 | 5 | 10 = 10 | yes | no | no | 3/3 |
| 281004 | 5 | 10 = 10 | yes | no | no | 4/2 |
| 281005 | 5 | 10 = 10 | yes | no | no | 3/3 |
| 281006 | 5 | 10 = 10 | yes | no | no | 3/2 |

For contrast, the four prior rules (`rule-27100*.json` in
`.local_agent/mature-static-20261017/`) are `classic_like` 4x4 with 8 pieces
per owner, every non-anchor type left-right symmetric, and pawn-like
rotation-variant atoms.

Two corrections to the working description follow directly from this:

1. `movement_symmetry=none` removes left-right mirroring; it does not make the
   two owners unequal. Every rule still shares one owner-relative atom set
   between owners (`piece_type` atoms are expressed in the owner's frame;
   player 1's absolute displacement is the 180-degree rotation). Because all six
   generated layouts are also 180-degree rotationally symmetric, each position
   is invariant under "rotate the board 180 degrees and swap owners". These
   games are owner-mirror-fair; the new property is orientation-biased
   (non-left-right-symmetric) movement.
2. The free_random draws did not create material imbalance: all six rules give
   both owners the identical type multiset. The changed premise is therefore
   "non-mirror-symmetric movement on a free random layout", not "one owner has
   better movement or more material".

## Frozen design

- Seeds 281001..281006; all generated on the first attempt, no fallback seed
  used, no generation failure.
- Rule dicts, weights, roots and slots were written and hashed before any
  outcome: `producer-source.json` records producer
  `93a6c1d4…aa29`, plan `ae935cef…7e14`, rules `cadb7f48…c02d`,
  models `77346b06…c5cf`, roots `d82884c8…a891`.
- Fitness-blind prefixes: 4 plies, up to 64 attempts per rule, first 32
  non-terminal kept (192 attempts, 0 terminal).
- Paid cells: 6 rules x 32 families x 4 label/foe/owner combinations plus one
  shared Unit-vs-uniform slot = 1344 physical games. Unit-vs-uniform owner 0 is
  reused as the owner-1 logical cell with `reward -> -reward` (192 reused cells),
  giving 1536 logical cells.
- Search: Native semantic engine, depth 2, 8192 nodes/query, 2 s/query,
  quiescence 0, TT 0 MB, `root_window_pruning=False`; frozen 64-ply horizon
  after the prefix and a 1200 s global cap.
- No fit, learner, optimizer, AUX checkpoint/state, profile or default change;
  no closed AUX92/93 cell was rerun.

## Actual execution and cost

`producer.py` completed with `status=COMPLETE` at
`.local_agent/asymmetric-static-20261018/result.json`:

- 1344/1344 physical games returned, 0 unstarted, 0 generation failures.
- 59,650 queries; 20,334,363 nodes; every query completed depth 2; 0 fallbacks.
- 746 physical terminals, 598 horizon UNKNOWN; the 192 sign-flipped logical
  copies raise the logical totals to 863 terminals and 673 UNKNOWN.
- Producer wall time 273.734 s; query kernel time 63.012 s and caller time
  116.542 s (max single query 0.0163 s). The 1200 s cap was not approached.
- The producer asserts, for every slot, ordered replay equality of the root
  state/witness hashes and pre/post-query equality of state, record, history and
  witnesses, and it asserts the final session/full-history replay equality.
  Those assertions ran inside the completed run without failure. This is
  in-run self-checking, not an independent rerun of the outcomes.

## Result

Paired candidate-minus-Unit reward (UNKNOWN kept as [-1,+1]), 384 pairs per
fixed foe:

| foe | pooled finite interval | conditional family envelope | resolved pairs | static better / worse / equal | both UNKNOWN | one UNKNOWN |
|---|---|---|---|---|---|---|
| uniform | [-0.596354, 0.940104] | [-0.697917, 1.044271] | 156 | 28 / 15 / 113 | 67 | 161 |
| fixed random channels | [-0.843750, 1.125000] | [-0.953125, 1.221354] | 114 | 30 / 14 / 70 | 108 | 162 |

Every per-rule interval also contains zero, under both foes:

| seed | uniform | fixed random |
|---|---|---|
| 281001 | [-0.6875, 1.03125] | [-0.953125, 0.640625] |
| 281002 | [-0.640625, 0.609375] | [-1.453125, 1.484375] |
| 281003 | [-0.625, 0.84375] | [-0.53125, 1.03125] |
| 281004 | [-0.828125, 1.359375] | [-0.90625, 1.53125] |
| 281005 | [-0.21875, 1.25] | [-0.609375, 1.390625] |
| 281006 | [-0.578125, 0.546875] | [-0.609375, 0.671875] |

Per owner: uniform owner 0 `[-0.536458, 1.005208]`, owner 1
`[-0.656250, 0.875000]`; fixed random owner 0 `[-0.802083, 1.062500]`,
owner 1 `[-0.885417, 1.187500]`. No owner split separates.

### Supported conclusion

Under this frozen 64-ply, depth-2 served comparison, the positive static
advantage measured on the four bilateral classic_like rules does **not**
generalize detectably to these six non-mirror-symmetric free_random rules.
Robustness is **unresolved**: every finite interval includes zero.

### Not supported by these data

- Not evidence of static/unit equivalence, and not a demonstrated reversal.
  Censoring is large (only 156/384 and 114/384 pairs resolve), and a single
  cell's W/L is a coarse outcome under a fixed horizon.
- Not a population statement about generated rules: six fixed rules with a
  conditional family envelope, not a sample of the generator.
- Not a claim about learned versus static material, per-rule optimal prices, or
  any default/profile change.
- Not a candidate-role comparison: the two owner cells differ in ply (0 vs 1)
  and candidate first-decision state from a shared game root, so a
  role-attributed difference is not supported.
- Not evidence that asymmetry between owners caused the difference; these rules
  are owner-mirror-fair (see above).

## Defects found and fixed during this segment

1. `describe.py` initially read `games.jsonl` directly and silently dropped the
   reconstructed Unit-vs-uniform owner-1 logical cell, so its resolved-pair
   table would have compared only materialized slots. It now rebuilds the 192
   reused cells exactly as `analyze.py` does (`reward -> -reward`) and reports
   1536 logical cells.
2. `analyze.py` built its family list by iterating the whole logical key set,
   so every `(rule, family)` appeared eight times. Pair counts were inflated
   eightfold (uniform "1248 resolved" instead of 156) and the family bootstrap
   resampled 256 duplicated units per rule instead of 32 distinct families,
   understating the family-level envelope. The fix uses distinct family sets;
   pair bounds are unchanged (duplicate pairs do not move a mean), and the
   envelopes widened to the values above. The pre-fix output is preserved as
   `analysis-before-count-fix.json`; `analysis.json` is the corrected run.
3. `LOCAL_MAINLINE.md` initially said the candidate's first *decision* was
   byte-identical under both labels. What is identical is the pre-decision
   root/state hash and ply (570/570 free, 342/342 classic); the served action
   itself differs in 305/570 free and 99/342 classic pairs, which is the
   measured effect. The mainline line now says so, and
   `report_consistency_check.py` asserts both the identity and the change count.
4. The published copy did not check itself. `report_consistency_check.py`
   resolved the report through a fixed `parents[1]/docs/research/...` offset
   that only works in the private directory layout, and it hard-required
   `LOCAL_MAINLINE.md` wording that is PRIMARY-owned mutable state. The copy now
   finds the report under the enclosing repository root, treats the five
   mainline wording assertions as opt-in via `--mainline PATH`, and prints them
   as skipped (not passed) when that flag is omitted. Raw `.jsonl` references
   are satisfied by the published `.gz` files, and the two pre-fix audit
   snapshots are shipped so every file the report names exists beside the
   checker.

The numbers quoted in this report are from the corrected scripts. The
`producer.py` outcome files were not regenerated.

### Numeric verification of this report (no new outcomes)

- `bounds_check.py` re-pairs the frozen `slots.json`/`games.jsonl` with a
  separate Fraction implementation and reproduces every W-L bound, pair count,
  resolved/better/worse/UNKNOWN count, and per-rule/per-owner interval in
  `analysis.json` exactly.
- `report_consistency_check.py` parses the markdown tables/prose and asserts each
  quoted value, the five frozen input hashes against `producer-source.json`, and
  the 570+342 same-state and 192/192 owner-0 duplication claims. Run from the
  public copy it prints 14 report/data checks as `PASS` and lists the five
  mainline wording assertions as skipped; passing `--mainline` to a document
  that carries those clauses restores the full 15. Logs: `bounds_check.log`,
  `report_consistency_check.log`.
- `owner_mirror_check.py` tests the owner-mirror-fairness statement itself on the
  frozen rules and roots with the same compiled executor (no search or outcome).
  It verifies that each initial position is its own 180-degree owner-swapped
  copy, that the compiled per-atom leap/ray targets, `drop_allowed` table and
  promotion tables map exactly under 180-degree rotation with the owner index
  swapped, and that for all 192 frozen roots the visible legal-action multiset of
  P equals that of M(P) (board rotated 180 degrees, owners and side swapped).
  Result: 6/6 initial positions, 6/6 compiled table sets and 192/192 roots exact;
  replay reproduces every frozen `legal_root_actions` count (0 mismatches), no
  visible binding is duplicated, and all six rules have `aux_slots=0` with empty
  root aux state, so aux mirroring reduces to the identity. Two negative controls
  differ on 192/192 roots: 180-degree rotation *without* the owner swap, and
  left-right mirror *without* the owner swap (the latter also records the
  non-left-right-symmetric movement). "Owner-mirror-fair" is therefore a checked
  property of these frozen rules and roots, not an inference from atom counts; it
  is not extended here to rules with auxiliary state. Log:
  `owner_mirror_check.log`.
  - Scope limit: this check covers initial positions, compiled move/drop/promotion
    tables and visible legal-action multisets at the 192 frozen roots (the script
    now asserts these gates and exits nonzero on failure). It does not prove full
    transition-graph isomorphism, per-query search-cost equality, or policy
    symmetry beyond a fixed state; no auxiliary-state claim is made beyond
    `aux_slots=0`.
- `paired_mean_crosscheck.py` takes the same both-resolved pair key set but
  re-reads the raw `games.jsonl` rewards and recomputes the mean, rule-cluster
  SE and exact sign-flip p with separate code, matching `mde_power.json`
  exactly: 166 / +0.295181 / 0.122031 / 0.0938 and
  255 / +0.341176 / 0.181968 / 0.1250. The key set is shared, so this is a
  second arithmetic path, not an independent rerun of the producer.
- Both new scripts were rerun from the frozen inputs: each exited 0 and rewrote
  byte-identical JSON (SHA-256
  `83C262ED699A092A143E608BC6EB6BBC5FA232E99CA6398AFE7DA8C1ACCCD08F` for
  `mde_power.json` and
  `DF0E6BCB19B62587F5306DF51278AE6FADB837A7DB296A7A5FB40B695C782D47` for
  `paired_mean_crosscheck.json`), i.e. deterministic arithmetic, not a producer
  rerun. Log: `determinism-check.log`.
- The normal-power constant was recomputed as `1.959964 + 0.841621 = 2.801585`
  (`quantile-check.log`). The t quantiles in `mde_power.py` are hardcoded
  standard-table values; an attempted independent scipy check failed because
  scipy is not installed in this venv (preserved in the same log), so those
  table values are not independently verified here.
- These checks catch pairing/arithmetic and transcription drift; they are not an
  independent rerun of the producer and cannot detect a shared design error.

## Secondary same-state served-score check (post-hoc, frozen data)

Only 156/384 (uniform) and 114/384 (fixed random) pairs resolve inside the frozen
64-ply horizon, so the W-L result is compatible with both "no effect" and "effect
too small to resolve". `score_margin.py` therefore reads only the already-frozen
`queries.jsonl` and asks a different, uncensored question on the same roots: at
the candidate's **first** decision the `unit` and `rule_static_v2` slots start
from byte-identical states (570/570 free pairs and 342/342 classic pairs match
both `root_state_sha256` and the pre-query state hash, in the same ply). The
served depth-2 candidate-perspective score difference is then a paired
ordering-price effect, not a game outcome.

A candidate query's served score depends only on the candidate profile and the
root state, so both foes measure the **same** owner-0 cell. `owner_duplicate_check.py`
confirms it: 192/192 owner-0 pairs share both root hashes and have identical
diffs under `uniform` and `fixed_random99031_channels`. The independent
information is the candidate **owner**, not the foe; an earlier four-row
rendering of this table double-counted the owner-0 cells and is superseded here.
That owner split is structurally tied to ply and root: every scorable owner-0
pair is at relative ply 0 and every owner-1 pair at ply 1. The game root itself
is shared (576/576 free and 3456/3456 classic both-owner game groups start from
the same `root_state_sha256`), but the candidate's first-decision state is not:
0/182 free and 0/92 classic `(rule, family)` cells have the same first-decision
state in both owners. Owner 0 acts at the opening position; owner 1 acts at its
reply after one opponent move from that same root. The two cells are different
decision contexts, not a matched role replication.

| dataset | candidate owner | pairs (families) | mean | median | +/0/- | sign p (2-sided) | changed action | family-cluster envelope |
|---|---|---|---|---|---|---|---|---|
| free6 non-mirror | 0 (both foes, identical) | 185 (185) | +38.30 | 0 | 92/19/74 | 0.187 | 105/185 | [-8.78, 83.74] |
| free6 non-mirror | 1 (`fixed random` only) | 182 (182) | -8.36 | +26 | 101/10/71 | 0.0267 | 95/182 | [-56.51, 36.03] |
| classic4 bilateral | 0 (both foes, identical) | 96 (96) | +42.53 | +26 | 53/12/31 | 0.0214 | 36/96 | [-22.88, 104.95] |
| classic4 bilateral | 1 (`random99031` only) | 92 (92) | +62.71 | +85.5 | 57/2/33 | 0.0149 | 27/92 | [1.04, 121.80] |

Scores are Native served units (`material_scale=256` per piece-weight unit; the
observed grid is 512), terminal-band pairs (>=1e6) are excluded and counted
(18 free, 58 classic). The read is:

- The envelope resamples the distinct `(rule, family)` clusters with
  replacement within each rule, keeps all pairs of a sampled family, and pools
  across rules. Each owner cell contributes one pair per family, so there its
  cluster bootstrap reduces to a pair bootstrap; the pooled both-owner cell
  (185/367/96/188 pairs from 185/185/96/96 clusters) has two pairs per family
  for the fixed-random foes. The earlier pair-level resampling was mislabeled a
  family envelope; the pre-fix output is kept as
  `score_margin-before-cluster-fix.json`. The sign-test p-values are exact
  two-sided binomials with zeros dropped and are **uncorrected** post-hoc tests
  over four reported cells; no multiplicity adjustment is applied.
- On the free rules there is **no served shift that repeats across the two
  owner cells**: owner 0 has a positive mean (+38.30) but a zero median and a
  non-significant sign test, while owner 1 has a negative mean (-8.36) but a
  positive median (+26) and a positive sign majority (101/71, p=0.0267) — a
  heavy left tail pulls the mean down. Both family-cluster envelopes include
  zero, and the cells differ in ply and first-decision state (not game root),
  so this is not a role test. The
  earlier "small positive served shift" reading came from the duplicated
  owner-0 cell.
- On the classic rules the shift is positive in both owner cells (+42.53 owner 0,
  +62.71 owner 1), and the owner-1 family-cluster envelope excludes zero. The
  leave-one-rule audit below shows each pooled owner-cell mean is carried by a
  different single rule, so this is *compatible with* but not an independent
  corroboration of the closed positive static-versus-unit result. It is the
  same four fixed rules and an uncorrected post-hoc statistic.
- The profiles are behaviourally distinct on identical states: static material
  changes the served action in 105/185, 95/182, 36/96 and 27/92 pairs.
- This observable was chosen after the W-L outcomes were seen. It reuses the
  same frozen producer (no new search, no independent rerun), scores one decision
  per pair, and its envelope is conditional on the four/six fixed rules. The
  `uniform` foe cannot contribute owner-1 candidate pairs (the reused logical
  cell has no owner-1 candidate query), so the owner cells are not a balanced
  design. It does not establish transfer, a per-rule price, or a W-L advantage.

### Leave-one-rule influence audit (post-hoc, same pairs)

`owner_role_influence.py` reuses `score_margin.build_pairs` and its family-cluster
bootstrap on the same frozen pairs; it adds no search. It asks whether each
pooled owner-cell summary is stable across rules or carried by one rule:

| dataset | owner | full mean [family envelope] | per-rule mean signs | leave-one-rule-out mean range |
|---|---|---|---|---|
| free6 non-mirror | 0 | +38.30 [-8.78, 83.74] | 5+/1- | [15.05, 48.99] |
| free6 non-mirror | 1 | -8.36 [-56.51, 36.03] | 4+/2- | [-28.27, 41.58] |
| classic4 bilateral | 0 | +42.53 [-22.88, 104.95] | 3+/1- | [-4.55, 79.11] |
| classic4 bilateral | 1 | +62.71 [1.04, 121.80] | 2+/2- | [1.10, 110.21] |

The pooled summaries are mixtures, not stable owner-cell effects:

- free6 owner 1: rule 281006 alone has mean -261.40 (envelope
  `[-479.03, -59.47]`); dropping it changes the pooled cell to +41.58
  `[6.91, 76.46]` (152 pairs, 90/10/52, sign p 0.0018). The other five rules
  are 4 positive / 1 negative; the median of the six rule means is +29.98. The pooled
  -8.36 and its p=0.0267 therefore describe a two-component mixture, not a
  shift shared by the other five rules.
- classic owner 0: the positive mean is carried by rule 271002 (+200.91);
  dropping it gives -4.55 `[-68.47, 57.24]`. Classic owner 1: the positive mean
  is carried by rule 271001 (+258.73); dropping it gives +1.10
  `[-66.13, 62.60]`. The two owner cells are driven by different rules, and the
  per-rule mean signs agree in only 1/4 classic rules.
- Cross-owner-cell check: **0/6** free rules and **0/4** classic rules have a
  zero-excluding family envelope in *both* owner cells. Per-rule mean signs
  agree in 3/6 free and 1/4 classic rules. No rule shows a common-sign
  excursion across the two cells.

The ply/decision-state difference is structural: every owner-0 pair is at ply 0
and every owner-1 pair at ply 1; the game root is shared (576/576 free and
3456/3456 classic both-owner game groups), but 0/182 free and 0/92 classic
families share the candidate's first-decision state across owners
(`owner_role_influence.json`). Owner 0's first decision is the opening position;
owner 1's first decision is its reply after one opponent move from the same
root. The two cells measure different decision contexts, so the cross-cell
agreement count is descriptive, not a replication test, and the pooled owner
means cannot be attributed to role rather than to the position/ply.

These are 20 rule-owner cells of 19-32 pairs, selected after seeing the outcomes;
individual per-rule excursions are not multiplicity-corrected and none is
claimed as a per-rule effect. What the audit does establish is that the pooled
means/medians and their sign tests cannot be read as a single role-level shift
in either dataset. Rules are owner-mirror-fair (equal type multisets,
180-rotated layout), so a role sign flip on one rule is compatible with the two
roles querying different decision states (opening vs one-ply reply) from the
same root; this audit does not separate that from a static-price/decision-state
interaction.

### Does the served-score margin track the paired outcome? (post-hoc)

`score_outcome_link.py` joins the same `score_margin.py` pairs to the frozen game
rewards and keeps only pairs where **both** games reached an actual terminal
result, then correlates the first-decision served-score margin with the paired
reward difference (`static - unit`, in {-2,-1,0,+1,+2}). Spearman is
tie-averaged, the envelope resamples `(rule, family)` clusters, and the
subsets are `terminal_band`-excluded and horizon-UNKNOWN-excluded:

| dataset | both-resolved pairs | Spearman | family-cluster envelope | nonzero-both | concordant/discordant | sign p | outcome diff -2/-1/0/+1/+2 |
|---|---|---|---|---|---|---|---|
| free6 non-mirror | 166 | -0.046 | [-0.180, 0.090] | 60 | 31/29 | 0.897 | 13/6/99/15/33 |
| classic4 bilateral | 255 | +0.094 | [-0.015, 0.200] | 91 | 55/36 | 0.0586 | 18/4/157/25/51 |

Split by the two gaming contexts that the pooled correlation merges:

| dataset | uniform owner 0 | random owner 0 | random owner 1 |
|---|---|---|---|
| free6 non-mirror | +0.003 (69) | -0.059 (55) | -0.144 (42) |
| classic4 bilateral | +0.217 (79) | +0.094 (89) | -0.031 (87) |

This near-zero correlation supplies **no positive support for the served-score
margin as a W-L proxy in this panel**: no cell exceeds |rho| = 0.22, the two
pooled envelopes contain zero, and the largest single-cell value (classic
uniform owner 0, +0.217) is uncorrected and itself does not exclude zero. It is
not evidence that the score is unusable generally, and it is not a categorical
statement about the score outside these rules and this horizon. The power is
also structurally low: 99/166 and 157/255 both-resolved pairs have identical
outcomes, so most pairs are ties in the outcome variable. The owner-0 score
margin is identical across foes (192/192 duplicated cells) while the outcomes
are different games, so the pooled correlations deliberately mix two gaming
contexts; the per-cell rows separate them and show no stronger link. This is a
post-hoc descriptive check on a both-resolved subset of already-frozen games; it
adds no outcome and does not change the W-L conclusion above, but it does mean
the served-score owner-cell means cannot be read as evidence of a W-L advantage
in this panel.

### Censoring and execution-cost controls (frozen files)

`resolution_and_cost.py` re-reads the raw `queries.jsonl`/`games.jsonl` without
rerunning search. It reproduces the report's cost claims exactly: 59,650 logged
queries and 20,334,363 logged nodes over the six free rules, every query with
`completed_depth=2`, 0 fallbacks, and 0 label slots without a query-log entry.
Those totals match `analysis.json`/`result.json`. For the four classic rules the
same recomputation gives 166,514 logged queries and 31,606,003 logged nodes over
all labels in that directory; the 49 unit/static slots with no query-log entry
all report 0 queries, i.e. games that ended before a search was issued.

The same script adds a same-state cost control: at the candidate's first
decision the two profiles face byte-identical states, and they used **identical
node counts in 570/570 free and 342/342 classic pairs** (mean 256.3 and 95.4
nodes). That establishes **paid-node parity only** at a fixed state. It does not
establish per-query time, one-time profile-construction or lifecycle cost
neutrality: caller/kernel time, table construction and the visited state
distribution are different quantities, and no timing campaign was run here. The
recorded active-run timing (producer 273.734 s wall, query kernel 63.012 s,
caller 116.542 s, max query 0.0163 s) is not a per-query comparison, so wall and
lifecycle cost neutrality remain unestablished. The pooled nodes-per-query
difference (free: 384.7 unit vs 306.0 static) is a composition effect of the
longer static games and the positions they visit, not a per-query budget
difference.

Finally, it splits the served-score margin by outcome-resolution status of the
two games of each pair (terminal-band pairs excluded, as elsewhere):

| dataset | group | n / mean served margin |
|---|---|---|
| free6 non-mirror | both resolved | 166 / +3.41 |
| free6 non-mirror | unit resolved, static unknown | 108 / +6.53 |
| free6 non-mirror | unit unknown, static resolved | 138 / +39.73 |
| free6 non-mirror | both unknown | 140 / +42.11 |
| classic4 bilateral | both resolved | 255 / +46.49 |
| classic4 bilateral | unit resolved, static unknown | 7 / -53.57 |
| classic4 bilateral | unit unknown, static resolved | 20 / +105.10 |
| classic4 bilateral | both unknown | 2 / +177.00 |

On the free rules the pooled both-resolved stratum has a much smaller served
margin (+3.41) than the strata containing an unresolved static game (+39.73,
+42.11). That gradient is **not consistent within rules** — it reverses on
281004 (+41.0 both resolved vs +7.0 static-resolved/unit-unknown) and is
non-monotone on 281003 (-89.6, +22.4, +138.9, +50.6) — so it is at least partly
a rule-composition effect and does not establish informative censoring. Its
concrete consequence for reading this report is narrower: the score-outcome link
above is measured in the low-margin both-resolved stratum, which further limits
its power and gives no positive support for reading the served margin as an
outcome proxy in this panel. The
classic cells with unresolved games are 2-20 pairs and are shown for
completeness only.

### Detectable shift of the frozen paired design (post-hoc)

`mde_power.py` asks how large a W-L shift the frozen design could have detected,
using only both-resolved pairs (`u = reward_static - reward_unit` in `{-2..2}`)
and treating rules as clusters. free6: n=166, mean +0.295 reward units per pair
(about +14.8 wins per 100 resolved pairs), rule-cluster SE 0.122, t(5) 95%
interval `[-0.019, +0.609]`, 80%-power MDE 0.426 units (about 21.3 wins/100).
classic4: n=255, mean +0.341, SE 0.182, t(3) interval `[-0.238, +0.920]`, MDE
0.757 units (about 37.9 wins/100). Both intervals contain zero, so the
both-resolved subset does not establish a static advantage either. The naive iid
SEs (0.083/0.065) with normal quantiles would have produced a falsely
zero-excluding free interval, which is why the cluster/t versions are the ones
reported. Between-rule SD of per-rule means is 0.333 (free) and 0.368 (classic),
so a common shift of 0.10 reward units/pair would need roughly 87 (free) / 107
(classic) independent rules at 80% power, and 0.20 units about 22 / 27.
An exact rule-level sign-flip test of the sharp null gives p=0.0938 (64
assignments, free) and p=0.125 (16 assignments, classic), and dropping any one
rule leaves the mean in `[0.201, 0.359]` / `[0.175, 0.452]`. The classic test
cannot go below 0.125 with four rules, so it is structurally unable to reject at
5% regardless of the data; the pooled positive means are suggestive and
leave-one-rule-out stable, not established.
Consequence: more families on the same six rules would reduce only the
within-rule sampling part of `sigma_rule` and would leave the rule-level df at
5 (3 for classic4). The rule counts quoted above are a **descriptive,
conditional forecast** from the selected both-resolved games, the estimated
rule-level variance and an exchangeable-rule, common-shift assumption. They are
not a universal prerequisite, not a mandate to launch tens or hundreds of rules,
and not a planned experiment. The current statement stays UNRESOLVED.
Assumptions: exchangeable rules, a common additive shift, and `sigma_rule`
estimated from six (four) rules; post-hoc selection on both games terminating is
not corrected. Log: `mde_power.log`.
An equal-weight variance decomposition (`variance-decomposition.log`) puts the
within-rule sampling share at 0.0385/0.1106 (35%) for free6 and
0.0157/0.1354 (12%) for classic4, leaving implied between-rule variance
0.072/0.120; a larger family count would shrink the minority sampling term, not
the dominant rule-level term.

## Cost and decision consequences

- Incremental cost of this diagnostic: one ~4.6-minute bounded CPU process plus
  analysis (all analysis scripts together rerun in <15 s wall time on the
  frozen files; the two new checks read 59.7k and 166.5k query records); far
  below the 120-minute prior-assessment threshold, no new infrastructure or
  search. The two profiles pay identical first-decision node counts at
  identical states (570/570 and 342/342 pairs), i.e. paid-node parity, not
  proven per-query or lifecycle cost neutrality; the pooled cost difference is
  game-length composition.
- What changed: the supported scope of the cheap rule-only static comparator is
  now explicitly bounded. The closed W-L comparison supports it on the four
  bilateral classic_like rules; the post-hoc served-score check is pooled-
  positive in both classic roles but does not reproduce that at rule level
  (each role mean is carried by a different single rule, and no classic rule
  has a both-role zero-excluding envelope). On the six non-mirror-symmetric
  free_random rules both the W-L and served checks are unresolved, and the
  pooled owner-1 negative mean is one rule (281006). Any generic-pricing claim
  must state that boundary rather than assume transfer. The served-score margin
  also shows no positive link to the paired W-L outcome (|rho| <= 0.22 in every
  foe/owner cell), so this panel gives no support for using it as a cheap
  outcome proxy.
- What would sharpen it, only if the decision needs a sharper answer: more
  independent rules (order tens; the descriptive forecast above), a longer
  horizon to cut censoring, or a paired same-root static-versus-static control
  to separate horizon noise from material effect. The free-rule role
  disagreement means the earlier "effect too small to
  resolve" reading is not established there either; a larger W-L run would need
  a fresh, preregistered endpoint. Neither is started here.

## Reproduction commands

```
.venv/Scripts/python.exe .local_agent/asymmetric-static-20261018/asymmetry.py
.venv/Scripts/python.exe .local_agent/asymmetric-static-20261018/describe.py
.venv/Scripts/python.exe .local_agent/asymmetric-static-20261018/analyze.py
.venv/Scripts/python.exe .local_agent/asymmetric-static-20261018/score_probe.py
.venv/Scripts/python.exe .local_agent/asymmetric-static-20261018/score_margin.py
.venv/Scripts/python.exe .local_agent/asymmetric-static-20261018/owner_duplicate_check.py
.venv/Scripts/python.exe .local_agent/asymmetric-static-20261018/owner_role_influence.py
.venv/Scripts/python.exe .local_agent/asymmetric-static-20261018/score_outcome_link.py
.venv/Scripts/python.exe .local_agent/asymmetric-static-20261018/resolution_and_cost.py
.venv/Scripts/python.exe .local_agent/asymmetric-static-20261018/score_margin_check.py
.venv/Scripts/python.exe .local_agent/asymmetric-static-20261018/bounds_check.py
.venv/Scripts/python.exe .local_agent/asymmetric-static-20261018/owner_mirror_check.py
.venv/Scripts/python.exe .local_agent/asymmetric-static-20261018/mde_power.py
.venv/Scripts/python.exe .local_agent/asymmetric-static-20261018/paired_mean_crosscheck.py
.venv/Scripts/python.exe .local_agent/asymmetric-static-20261018/report_consistency_check.py
```

`producer.py` is intentionally non-rerunnable in place (it refuses to overwrite
frozen rules/outcomes).
