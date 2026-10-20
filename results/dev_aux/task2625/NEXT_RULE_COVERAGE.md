# Next rule coverage after task2625

## Decision

The next learner-transfer question should add one existing 4x4 generated rule
with semantic actions, keeping board size fixed.
`results/dev_aux/task2433/rules-0.json` is a concrete candidate (SHA256
`33020d8bb1bb06115f7314aed32db28218033bbc7d7ce47203cd832979fa90a0`). It has
the same board size and four pieces as task2625, while adding a semantic capture
that moves a captured piece to hand, promotes the mover, and sets a boolean
auxiliary right that expires next turn. The task2411 fixture
`rules-0.json` (SHA256 `ccadfa3e1d8f1ff3d42961abb6363bdab6bdeac856739ad9d853e742707ef7a4`)
instead has a hand-count zone guard on drops combined with a separate
capture/promotion action. These are concrete mechanics, not a claim about their
frequency in the complete generator domain.

The 16 task2433 rule files share one identical semantic-action DSL and one
movement profile; its input corpus has one prefit root per rule file. Choosing
`rules-0.json` by fixed file order therefore selects a single existing rule
mechanism without selection on measured outcomes. Its one old root and all
other task2433 histories still count as exposed and must be excluded from a new
root panel. The task2411 rule is a distinct, more coupled control and is lower
priority for the first learner result.

One qualification changes how to describe that candidate: its `temp_right`
auxiliary boolean is written and expires, but the saved DSL has no guard or
trigger that reads it. Do not treat the bit itself as a decision-relevant
history test. The behaviorally relevant new mechanics here are capture-to-hand,
promotion, and consuming an R from hand to unlock a quiet rook ray move. The
saved task2411 rules also contain a board-count guard on drops, but that fixture
is authored and more coupled; the 16-rule task2433 family remains the generated
candidate. The saved DSL inventory has no example where a rule condition reads
auxiliary state, so a later genuinely aux-conditioned generated rule would be
needed to validate that specific capability.

The causal question should be narrow: can the unchanged task2621 fixed-scale
TDLeaf learner produce useful actual-terminal outcomes on an outcome-blind,
history-disjoint panel for a semantic-action ruleset, with the complete
GameSession retaining authority over auxiliary state, captures, hand inventory,
promotion and history? The adapter currently counts current board types and
base hand types; it does not encode auxiliary state. A result would therefore
test this representation's limits on a fully executed rule, not claim that the
learner models every rule variable.

## Coverage inventory

Task2625 measured four 4x4 rules, each with a king and three non-anchor piece
types using leap/ray atoms. All four permit drops for non-anchor types; their
promotion targets and forced-promotion maps vary. None has `semantic_actions`
or explicit auxiliary state. Across the saved `results/dev_aux/rules-*.json`
inventory, a simple schema-feature scan found 477 files and 14 coarse signatures
(board size, leap/ray presence, promotion/drop types, semantic-action/auxiliary
state presence and extra top-level fields). This is an artifact inventory, not
477 unique rules or a representative sample of generated rules.

| Capability absent from task2625 | Existing evidence | Added value for the learner question |
| --- | --- | --- |
| Semantic actions / capture-to-hand / hand-consuming movement | task2433 has 16 generated rule files with this DSL; task2411 has a related authored fixture | Highest: actual promotion, captured inventory and hand-conditioned move generation go through the unchanged learner and full history |
| Zone-guarded drops and hand-consuming move effects | task2411 `rules-0.json` | High, but couples multiple new effects if used as a single first candidate |
| Board size 3x3 or 5x5 | task2128 and task2588 | Lower for a first follow-up; primarily changes geometry/branching and task2625 already varies movement geometry |
| Other promotion/drop combinations | task2525 and task2588 | Mostly represented already; useful later only if a specific unsupported interaction is isolated |

## Exposure, cost and limits

Task2433's saved pre-fit corpus contains 16 roots (8 train, 8 reserve), one per
rule file, 112 generation attempts and zero fitness queries. That establishes no fitness-label
selection in that corpus, but it does not make those roots independent: its
saved legal-prefix histories must be considered in a new root audit. They are
not fitness/search queries; that status does not restore independence. The
task2411 records are separate constructed controls and also must be included in
the exposure audit. Select roots only from rule definitions,
history disjointness and predeclared feature-excitation criteria; do not inspect
W/L/D, UNKNOWN, model weights or search-target values when choosing them.

No next experiment is registered or launched here. Task2625's whole-task
estimate was 66.70 minutes for four rules and is not a source-matched estimate
for semantic-action rules. A new plan must price the candidate on the unchanged
task2621 learner and task2625 actual-terminal evaluation path, retain UNKNOWN
and missing slots, and keep its all-in run under 120 minutes; if the revised
estimate reaches 120 minutes, the mailbox assessment is required before launch.
Task2621 already has finite semantic-state, record-replay and auxiliary-expiry
interface witnesses, so the follow-up should measure learner outcomes rather
than repeat those interface checks. It should not try to resolve task2625's
frozen H=128 UNKNOWN by extending its panel.

A fair scoped comparison can preserve task2625's per-rule budget: four seeds,
120 train roots per seed, 250,000 combined candidate-plus-foe nodes per arm,
and 16 evaluation roots per seed for each of the two model endpoints (256
slots total). This is one rule, not a claim of domain coverage. Pure linear
scaling of task2625's 66.70-minute whole-task estimate gives about 16.7 minutes,
but semantic-action cost may differ; use only as a planning reference and bind a
fresh source-matched feasibility run before registration. Generate a new fixed
root pool, audit complete-history disjointness against task2433's 16 saved roots
and task2411 controls, and require nonzero R-hand / promotion-feature exposure
using no outcome or search-target fields.

The decision-changing outcomes are predeclared: a complete finite panel whose
UNKNOWN-completion lower bound is positive supports only this one generated
rule; a bound spanning zero leaves usefulness unresolved; repeated zero updates
or an UNKNOWN-heavy panel points to feature excitation or horizon feasibility
before any learner redesign. No result authorizes a new material scale, learned
Chess-weight transfer, or a product/default change.

This is a rule-coverage decision only. It creates no registration, sample,
learner update, strength conclusion or mainline completion claim. The task2625
finite-panel result and task2622/2623 failure records remain unchanged.
