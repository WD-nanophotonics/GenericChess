# ADR-074: evaluator representation reassessment

## Status

F23Z is complete and closes the F23 evaluator-foundation series. The selected
conclusion is `CONTINUE_WITH_MINIMAL_CHEAP_EVALUATOR`; the next boundary is
`F24A_MINIMAL_CHEAP_RULE_DERIVED_EVALUATOR_SIGNAL_PROBE`.

This is an architectural classification and pre-registration decision. F24A
is not implemented here, and no F23Z corrective or automatic optimization
generation is created.

## Accepted F23Y evidence ledger

F23Y established executable local semantic direction evidence: M1–M10 passed,
the actual M9 positive-gain `P -> G` witness passed with gain 635, contract-
specific type renaming passed, and P0/P1 mathematics matched within `1e-12`.
P0 median evaluation was approximately 38.3 ms, P1 12.9 ms, and production v1
0.510 ms; P1/P0 speedup was approximately 2.97x. P1 legal-action construction
dominated its remaining cost; aggregation was negligible. Paired candidate/v1
NPS ratios were approximately 0.161 and 0.263, with evaluator fractions 0.844
and 0.865. Both fixed-time gates failed.

Both evaluators completed the valid 2048-node matrix. Candidate-v1 top1 delta
was `-1`, one valid frozen control regressed, and root-rank instrumentation
remained unavailable. Playing-strength evidence was `NOT_RUN`. These results
are not individual-feature causal effects and do not authorize feature or
coefficient tuning.

## Responsibility map

The current implementation supports the following split:

| Area | Current responsibility | F23Z classification |
| --- | --- | --- |
| Board material and hand value | production evaluator, static profile lookups | `LEAF_STRUCTURAL` |
| Cheap pseudo mobility | production evaluator, compiled geometry traversal | `STATIC_PROXY_CANDIDATE` |
| Anchor escape/check | bounded evaluator term plus search/qsearch checks | `STATIC_PROXY_CANDIDATE` |
| Promotion potential | production evaluator from static promotion profile | `STATIC_PROXY_CANDIDATE` |
| Legal mobility/control for both sides | search runtime and move generation | `REJECT_LEAF_HOT_PATH` |
| Full attack/defense/anchor safety | semantic search/qsearch checks and continuations | `REJECT_LEAF_HOT_PATH` |
| Captures/recaptures | qsearch, ordering, history/countermoves, continuation | `SEARCH_RESIDENT` |
| Immediate promotion/drop tactics | qsearch, ordering, and search | `STATIC_PROXY_CANDIDATE` for structural proxy; tactical part remains search-resident |

The exact source checks and complete term matrix are stored in the F23Z
fixture. In particular, search already owns legal actions, push/pop transitions,
terminal/repetition/history state, TT, and recursive continuation. Qsearch
explicitly expands captures, promotions, terminal actions, checking moves, and
checking drops. Ordering handles captures, promotions, killers, countermoves,
and history; checking-action classification was deliberately avoided because
it requires expensive per-action legality/attack probes.

## Why the dynamic representation is rejected as a leaf

F23 metamorphic success means the concepts have semantic meaning; it does not
mean every concept belongs in a hot leaf evaluator. F23Y showed that full legal
mobility, attack maps, safety, and history-linked tactical pressure replay
phenomena already represented by search/qsearch/order. Recomputing them at
every leaf introduces duplicated work and search/evaluator coupling while
remaining far slower than v1 and not improving the benchmark result.

The preferred conceptual split is therefore:

> generic adversarial search + TT/order/qsearch + small cheap RuleSet-derived
> structural leaf evaluator

The same split applies to Standard Shogi, Western Chess, and future mixed
mechanics without game-name branches. The static profile/compiler already
provides board value, hand value, promotion gain, empty-board mobility and
forward mobility, drop freedom/mobility, anchor identity, current/base type,
and occupancy inputs through bounded lookups.

## Four strategies

F23Z scored all four required strategies on the fixed planning matrix; scores
are 1–5 fit ratings, not empirical proof and include no existing-infrastructure
bonus:

| Strategy | Total | Main assessment |
| --- | ---: | --- |
| `CHEAP_RULE_DERIVED_LEAF_WITH_SEARCH_RESIDENT_TACTICS` | 72 | simplest, generic, cheap, low coupling and duplication |
| `LEARNED_SMALL_RULE_DERIVED_LEAF` | 52 | cheap but label dependence weakens generic falsifiability |
| `FULL_DYNAMIC_SEMANTIC_LEAF` | 44 | semantically expressive but repeats search work and misses cost gates |
| `INCREMENTAL_DYNAMIC_EVALUATION_STATE` | 43 | may reduce leaf cost but adds state, rollback, and coupling burden |

Incremental dynamic state is not selected merely because it could speed up the
current five features. Learning is not selected as a rescue for a representation
that has not shown cheapness and generic real-game signal.

## F24A pre-registration

F24A freezes four cheap structural concepts:

1. material and inventory;
2. RuleSet-derived positional capability;
3. bounded anchor structural space;
4. promotion and drop structural capability.

The exact formula must be frozen from existing normalized profile data before
implementation. `evaluate()` may not enumerate semantic legal actions, perform
a second-side legal pass, sweep a full semantic attack map, run multi-ply
tactics, or use search-policy hidden state. No coefficient fitting, AlphaSho
supervision, game-name branch, piece-name logic, or per-game coefficient table
is allowed. The concepts must remain applicable to Shogi, Chess, and mixed
mechanics and preserve type-name invariance.

The micro pre-gate is candidate median <=2.0x v1 and p95 <=3.0x on the frozen
F23Y Standard Shogi leaf sample. A failure stops before full Shogi search. If
it passes, the existing gates remain unchanged: at completed 2048 nodes,
candidate top1 must be at least v1+2 with zero frozen-control regression;
fixed-time candidate evaluator fraction must be <=25%; paired candidate/v1
NPS ratio must be >=0.65. No gate is lowered because F23Y failed.

F23Y, F23X, F23W, F23V, and V1–V12 artifacts remain read-only and preserved.
F23Z changes no production code and keeps master locked.
