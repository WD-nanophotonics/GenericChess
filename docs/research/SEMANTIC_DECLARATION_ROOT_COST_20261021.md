# Semantic declaration root-assessment cost — 2026-10-21

## Question and decision

Does the AlphaBeta declaration path impose avoidable cost for an unfamiliar
accepted RuleSet with many declarations, and does that cost invalidate its
reported time-limit behavior?

The compiler accepted Standard-Shogi-shaped RuleSets with 256 and 1,024
distinctly named owner-0 declarations; the schema/compiler has no declaration
count ceiling. The old search bridge iterated the list and resolved each item
by scanning the full list for its ID, making resolution quadratic in the
declaration count before guard, metric and check assessment. The bridge now
assesses the declaration it has already selected. Core public enumeration uses
the same direct helper. Rule meaning, declaration order, winning results,
terminal priority, and caller-visible result fields are unchanged.

## Measurements

`data/semantic_declaration_root_cost_20261021/declaration_cost_paired.py`
recreates the former lookup and compares it with the current bridge on identical
compiled inputs. Seven-repeat median isolated assessment cost was:

| Accepted declarations | Former lookup | Direct assessment | Change |
| ---: | ---: | ---: | ---: |
| 256 | 4.734 ms | 3.629 ms | −23.4% |
| 1,024 | 30.450 ms | 14.463 ms | −52.5% |

The old and new non-losing assessment tuples were equal in both cases. A product
regression builds 128 distinct declarations that are all valid WIN claims and
checks exact Core/search ordering and outcomes. The focused declaration,
AlphaBeta-root, completed-root-win, and Standard Shogi tests pass (68 passed).

The normal Standard Shogi caller contains two declarations. A seven-call 20 ms
search probe completed depth 1 and returned a legal action every time; elapsed
median was 19.783 ms. Results vary with CPU load as expected for a cooperative
time budget.

A paired fixed-node probe is available in
`data/semantic_declaration_root_cost_20261021/fixed_node_probe.py`. For both
the normal two-claim and a 32-claim accepted ruleset, all five old/new pairs
returned exactly the same action (`legacy_112:g6-f1-g2`), score 9, 128 nodes,
depth 1, `node_limit`, and declaration-check counts (196 and 3,136
respectively). At 1,024 declarations, all five old/new fixed-eight-node runs
also matched exactly: same legal fallback, score 0, depth 0, `node_limit` and
1,024 declaration checks. Its paired full-search median was 34.256 ms before
and 16.856 ms after, consistent with the one root assessment dominating this
stress call. Do not generalize this synthetic-input timing to normal rulesets.

## Limits and interpretation

The 256/1,024 cases deliberately replicate one Standard Shogi declaration with
unique IDs; they establish an accepted-input stress boundary, not prevalence in
generated rules or an expected production count. The paired 1 ms end-to-end
search probe took tens of milliseconds and its depth-0 fallback action varied
across runs. That is not a useful action-quality or strict-deadline comparison.
Both versions reported `time_limit` and returned legal fallback actions. The
public `SearchLimits` contract explicitly defines time as cooperative, not a
strict execution deadline.

Root declarations must still be completely assessed before a legal move can be
returned safely: a later declaration may be a valid WIN. This change removes
redundant identifier scans, but it does not add cancellation inside the
declaration sweep or guarantee a deadline for arbitrarily large authored
rulesets. No rules/defaults, search semantics, generators, or price/evaluator
settings changed. Revisit cooperative checkpoints or a justified input bound
only if a named current caller demonstrates that the remaining linear
assessment cost blocks useful work; do not silently skip declaration semantics.

Reproduce the stress and normal-caller probes from the repository root with
`.venv\\Scripts\\python.exe docs\\research\\data\\semantic_declaration_root_cost_20261021\\declaration_cost_paired.py`
and `standard_shogi_budget_probe.py`.
