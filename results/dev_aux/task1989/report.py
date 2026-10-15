"""Generate concise segment66 delivery from closed audited evidence only."""
from pathlib import Path
from collections import Counter
import json
BASE=Path('results/dev_aux')
def read(p):return json.loads((BASE/p).read_text(encoding='utf-8'))
def run():
 main=read('task1980/result.json');pool=read('task1988/result.json');same=read('task1995/result.json');probe=read('task1984/probe.json');fil=read('task1984/filter.json');restore=read('task1989/restore.json');selection=read('task1985/selection.json');precision=read('task1988/precision-diagnostic.json');archives=read('ARCHIVE_MANIFEST_20261016_66.json');dom=read('task1993/cost-summary.json')
 assert main['status']=='PASS' and restore['status']=='PASS_INDEPENDENT_RESTORE'
 p=next(c for c in pool['contrasts'] if c['label']=='POOLED');seed=next(c for c in pool['contrasts'] if c['label']=='SEED1');mixture=pool['pooled_vs_learner_mixture'];m=main['aggregate'][0]
 outcomes={c['label']:dict(sum((Counter(x['outcomes']) for x in c['per_opponent'].values()),Counter())) for c in pool['contrasts'] if c['label'] in ('UNIT','POOLED','SEED1')}
 race=sum(c['race_seconds'] for c in main['cohorts']);full=sum(c['fullTRAIN_seconds'] for c in main['cohorts'])
 text=f'''# DEV_AUX segment66 — balanced opponents, pooled TRAIN and executable proofs

Science: **OPEN**. This is a safe research checkpoint, not universal piece-value recovery.
Own sidemission only; PRIMARY, product/defaults/UI remain untouched. The repository
stays PUBLIC for anonymous Dot/Chat access; the failed PRIVATE experiment is superseded.

## Main finding

Two independently trained16-family prices are1 and3; their original independent
32-family validation gives only {m['mean']} finite-event W-L gain,
stratified family interval {m['stratified32family_interval']}. Balanced-opponent
training alone did **not** establish broader transfer or a stable exact price.

Pooling the already-paid832 TRAIN cells (32 families total) selects R/N1.75,
tied with2; numerical ascending ties were frozen beforehand. This selector read
only the TRAIN prefixes. Before drawing any further inputs, it locked prices
1,1.75,3 for a new full crossed32-family confirmation. All768 physical games
completed and independently replayed. The pooled price gains **27/256** actual
finite-event W-L versus UNIT, family interval {p['bootstrap32family_interval']}.
The separate learned price3 gains25/256, interval {seed['bootstrap32family_interval']}.

This is evidence for useful learned prices under the declared complete player,
root and opponent distributions. It does not identify a unique ratio:1.75 minus3
is {precision['mean']}, interval {precision['bootstrap32family_interval']}.
The latter is a labeled posthoc precision description on the same cases.
No human prices or human holdout were used to choose anything.

|New confirmation policy|Actual W|Actual L|Actual D|UNKNOWN|
|---|---:|---:|---:|---:|
'''
 for label in ('UNIT','POOLED','SEED1'):
  o=outcomes[label];text+=f"|{label}|{o.get('WIN',0)}|{o.get('LOSS',0)}|{o.get('DRAW',0)}|{o.get('UNKNOWN',0)}|\n"
 text+=f'''
UNKNOWN remains unresolved, not DRAW. Primary rewards are actual rule WIN+1,
LOSS-1 and0 for actual draw or unresolved finite-horizon event. They are **not**
unlimited win probabilities; pooled-minus-UNIT unresolved WDL bounds remain
{p['UNKNOWN_WDL_bounds']}. No material-count or theoretical-win reward exists.

Pooled minus the equal mixture of the two16-family learner policies is
{mixture['mean']}, interval {mixture['bootstrap32family_interval']}.
That mixture is the expected payoff of two frozen policies via shared cells,
not averaged prices, two new training runs or an independent extra validation.
Pooling used complete paid TRAIN controls, not free observations from racing.

## Equal proof capacity on both actors

The earlier complete policy gives the candidate PN1024 and the fixed opponent
PN16; normal search is4096 on both. It is a controlled price comparison, but
cannot be described as equal endgame-solving capacity.

Before inspecting the new confirmation result, the full32-family followup froze
512 UNIT/POOLED cases, four opponents and both roles, with BOTH actors using
PN1024, verification16384, identical phase/normal budgets, and separate cold
per-actor proof banks. An initial8-family128-case proposal was retired at0 calls;
its source/plan and retirement reason remain. It was replaced before any policy-
variant labels, rather than split, executed twice or extended after outcomes.
One1800-second clock applies to the full replacement.

Actual new within-condition price gain: **{same['mean_price_delta']}**,
32-family interval {same['bootstrap32family_interval']}.
Same32-family old-condition gain: {same['old_same32family_price_delta']}.
Interaction: {same['interaction']}. Changing opponent PN **and** cache policy
means the interaction is not an isolated PN-only causal estimate. These are
shared families/policies, not another independent training replication.
Outcome counts: {same['outcomes']}.

## Frozen player and inputs

The exact legacy4x4 K/R/N capture-remove law has one R and two N per side,
no drops/promotion/auxiliary/declarations; public GameSession owns history and
actual mate/stalemate/repetition/max-ply adjudication. Input sampling is uniform
KkRrNNnn placement followed by both kings safe, >=4 legal moves per actor,
legal enemy-N capture and no legal enemy-R capture. D4/color duplicates and all
prior input orbits are excluded. Root generation never uses prices/search/WDL.

Two32-root cohorts split first16 TRAIN/last16 DEV. Each TRAIN family receives
one independently shuffled balanced opponent from R/N{{.5,1,2,4}}, common to all
arms/both roles. DEV crosses every family with all four equally weighted foes.
New confirmation uses another32 ALL-DEV families, frozen before labels.

The13 price grid is .25,.5,.75,1,1.25,1.5,1.75,2,2.5,3,3.5,4,5 at N720.
FULL means this finite grid, not a continuous global optimum. Prices jointly
change leaf/native/capture tables of the modified Fairy/Stockfish-derived
material-only Native search. This is neither unmodified Stockfish/NNUE,
YaneuraOu12-parameter convergence nor the whole generated rule domain.
Proof search, independent verification and rank-decreasing executable strategy
are material-price independent; all actual moves and outcomes are retained.
H24 allows only an existing verified rank<=64 tail; no new proof after H.

## Cost, uncertainty and mechanisms

- Exposed128-case PN1K cost probe: {probe['actual_game_seconds']:.3f}s versus
  historical4K {probe['old_game_seconds']:.3f}s.127 outcomes match; one WIN becomes
  UNKNOWN, with121 identical full paths. Cheaper proof is not policy equivalence.
- Prospective RACE208 matches FULL416 in both new cohorts. Combined observed
  TRAIN cost is {race:.3f}s versus {full:.3f}s. The study still pays full controls;
  no claim that its overall game count was halved.
- All768 TRAIN arm/UNIT comparisons:440 first differences are candidate NORMAL
  actions,328 complete paths identical, no fixed-opponent-first differences.
  Prices enter decisions; changed actions alone are not evidence of gain.
- Only19/32 TRAIN families have a nonflat empirical W-L table. Four families are
  fixed-proof first-player one-move wins for all26 price/role cases
  (opposite candidate roles receive opposite labels), but cost merely
  {dom['trivial_seconds']:.3f}s of {dom['all_TRAIN_seconds']:.3f}s TRAIN. They waste
  sample quota, not most compute; nine other flat families remain unexplained by
  that trivial mechanism. No current cases were discarded or relabeled.
- Stratified TRAIN bootstrap and equal-nu LOFO preserve opponent weights and
  show price instability. Resampling is not new training replication.
- Two posthoc32-family racing chronologies on the complete observed table choose
  1.5 (raw TRAIN regret1/64) and1.75 (regret0), using288 table cells. These are not new physical
  runs or timing measurements; no favorable chronology/default was adopted.

## Strict opt-in no-WIN census transport

The old exact-fingerprint inventory filter is unchanged. A separate opt-in helper
compares **every compiled execution field**, allowing only setup roots,
fingerprint and descriptive initial entity count to vary. Unsupported execution
changes are rejected. Current compiled object identity and full current-record
replay are required; no old provenance/certificate is relabeled.

Across three target rulesets,45,720 complete census states and208,080 edges
match old actual Core frontiers/terminals, including KKR positive controls.
The closed KK/KKN classes have no winning terminal; draw-only history cannot
create a win. This justifies UNKNOWN/no new PN action, **not** exact DRAW/WDL or
a generic dead-position rule.17 new guards include changed win mechanisms,
movement/history policies and corrupted full records. No current learning run
uses this filter; no default/UI integration follows.

Its predeclared64 exposed cases retain {fil['identical_full_records']}/64 complete
paths, transitions {fil['outcome_transitions']}, with game cost
{fil['actual_game_seconds']:.3f}s versus historical {fil['old_game_seconds']:.3f}s.
Filter initialization is separately retained in task1983/filter-init.json;
all global wall/caps remain in completion.json. Historical timing and ordinary
concurrent load do not establish a noise-free speedup or universal policy identity.

## Reproduction, failures and delivery

All producers are closed. Restored-source Python-S computation passes50 related tests,
{restore['replay']['games']} actual games, {restore['replay']['moves']} physical
moves and {restore['replay']['native_bindings']} Native history/profile bindings;
complete census checks also replay. Proof-adopting wins are not marginal solver
wins. Same OS/interpreter/Core limitations remain; study Native/search/proof
queries were not rerun. Unit mechanism tests do execute actual provers.

Four archives are required: original SOURCE/EVIDENCE in
ARCHIVE_MANIFEST_20261016_66.json, historical comparison dependencies in
SUPPORT_MANIFEST_20261016_66.json, and real python-chess source/license in
RUNTIME_SUPPORT_MANIFEST_20261016_66.json. Use the late direct-Git entry
`python -m results.dev_aux.task1989.restore_complete` on this qualified host.

The first restore passed50 tests then lacked task1968/games.jsonl. A separate
3-file byte-exact historical support archive fixes that omission. The second
passed50 tests but the actual transport adapter could not import chess; its real
package and GPL license are now explicitly archived. The adapter assumes producer
cwd/neighbor PRIMARY, so restored computation binds its unchanged real stop check
to the actual live project stop roots via a private runtime path. No fake or
cleared flags, weakened semantic assertions or study reruns are used. This is not
a fresh-machine turnkey claim. Both failed directories/logs remain private.

Original SOURCE/EVIDENCE and the first support archive remain byte-unchanged;
late corrected helpers/report generator/notes are direct Git outside them.
Exact Native journals are public archive-only to avoid duplicate huge Git blobs,
retained locally. No unique evidence was deleted. Retired0-call1991/1992 sources,
old65 failures/caps/source archives remain unchanged. Final report/session/restore,
QA and delivery receipts are outside sealed archives, without claiming otherwise.

PRIMARY cd30db453003ebc0b6c40373287071a27c0a548d is an OWNER MESSAGE here.
It reports reading AUX64/65 reports, without solver/learning source execution or
adoption. AUX has not executed/adopted its new search code or pooled work units.
See its fixed CHECK_ONLY_TT_AND_HISTORY_CONTEXT_20261016.md report and our
COLLABORATION_LOG. No routine receipt reply or cross-checkout write occurred.

Science remains OPEN. Next freeze learning against the common proof-policy
opponent, cost it from these actual results, and use fresh inputs/validation;
do not pick prices, roots, weights or a longer cap from current DEV. A possible
price-free initial-proof root filter changes conditional mu and needs a new
before-input protocol; current evidence is preserved. Final actual session and
remote-publication receipts are separate; validator acceptance is not scientific proof.
'''
 path=BASE/'SEGMENT_20261016_66.md';path.write_text(text,encoding='utf-8')
 print('Report generated from closed audited evidence:',path.as_posix())
if __name__=='__main__':run()
