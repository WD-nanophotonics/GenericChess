# GenericChess F82 C2 Native Decision Audit Closeout

Date: 2026-09-15  
Mode: Courier  
Work package: mechanism-level audit after three tied Arena pairs

## Question and cheapest sufficient procedure

Chat requested a bounded check of whether the C2 parent-anchored residual changes real 512-node native search decisions before any further Arena sampling. The audit used the existing frozen C2 training corpus and teacher evidence:

- 36 unique `train` roots from `artifacts/f83_c1_relative_evidence/root_corpus.json`.
- Parent and the published C2 candidate loaded through the existing identity-gated loader.
- One fresh `SemanticSearchEngine` search per checkpoint per root: 512 nodes, depth 12, 8 MiB TT, root-window pruning enabled.
- The seven registered teacher action rows at each root were scored with the frozen parent and candidate compact residual models. Their deterministic order and top-two margin were compared; this is a teacher-row ranking diagnostic, not a replacement for the native search result.
- No Arena, Arena8, promotion, or candidate mutation was performed.

The three Heavy chunks used the small/medium bounded envelope `f82-c2-native-decision-audit` (12 roots per invocation, 24 native searches, 512 nodes/search). The transient runner and JSON outputs remain under `.generic_chess_flow/` and are not tracked.

## Identity and evidence binding

- Published sandbox before audit: `eb05543b8abf4c07c615458ff220ad748a784954`
- Parent checkpoint: `f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4`
- Candidate checkpoint: `86f026ef85d60e600bc1bd6bc7b7285f11e5ce7e6528911b2ea361a489dc5983`
- Candidate model SHA-256: `b2308bea76ba55a533b95036f9b0ca37265c15d772ce5fbd14f7b6b098677e95`
- Allocation SHA-256: `f0de3d7175da6e5551457d0669e7efd87dc8f0dad446f6b956c1482b8b2a364e`
- Root corpus SHA-256: `a5fdbb12e3ee443448a1e9ec09a8405857bcf72fd3687777afbe69548a021fa4`
- Teacher evidence SHA-256: `3160e3935f8b862209d5be802ee9739a0d7d4e590730fa423099603cfe827aad`
- Envelope SHA-256: `05f4b73ca9b2208e126f5730d2ca1da1973ff57dc5ff0e8c6d4b61a1b3971996`

Chunk result SHA-256 values:

- roots 0–11: `e8cd4748b06622391d49ba4c1f3a8ca0bc65eac42d3e25c91392c04af132fdd9`
- roots 12–23: `79e206aca30f7fa5b12a10c5c4f1cfbca8dd585f6ee91f05537130a7e6e1e232`
- roots 24–35: `9f775bcf968ce2bf02b1319fc46aa7ebe9aa9351875da06a6ec35446dc7a9b3f`

## Results

| Root stratum | Roots | Native root-action changes | Teacher-row ranking changes | Parent top-2 margin | Candidate top-2 margin | Margin delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `c1_on_policy` | 12 | 6 | 12 | 1318.33 | 1429.30 | +110.97 |
| `c1_pv_corridor` | 12 | 10 | 10 | 2218.87 | 1150.19 | −1068.68 |
| `reachable_random` | 12 | 5 | 10 | 2380.34 | 2081.19 | −299.15 |
| **All roots** | **36** | **21** | **32** | **1972.51** | **1553.56** | **−418.96** |

The candidate changed the native root action on 21/36 roots (58.3%) and changed the teacher-row ordering on 32/36 roots (88.9%). The overall teacher-row top-two margin fell by 418.96 units (21.2%). Mean absolute native root score delta was 1,748,392.5 fixed-point units.

## Decision

C2's residual is not inert: it materially reaches the 512-node native search and changes action selection on a majority of frozen roots. Therefore the conditional route “residual has almost no search effect; immediately redesign the learning target only to create behavioral change” is not supported by this audit.

The Arena result remains three valid role-swapped pairs at exactly `0.5`, so C2 still has no promotion evidence. Do not add another C2 Arena pair under the prior sequence. The next learning decision should address alignment between these substantial decision/margin changes and strength outcomes (especially the large margin contraction in the PV-corridor stratum), then define a separately approved successor candidate or small triage. No promotion was requested or performed.

## Verification

The existing focused F82 regression suite remains the gate for this closeout:

```text
tests/test_learning_arena_integrity.py
tests/test_f63r1_game_atomic_arena.py
tests/test_f82_c2_parent_anchored_repeatability.py
```
