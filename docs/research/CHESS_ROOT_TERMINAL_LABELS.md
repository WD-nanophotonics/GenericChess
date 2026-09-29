# Frozen Chess root with independently checked immediate outcomes

**Unknown.** Is there a compact real Chess RuleSet root with root-action outcome labels obtained from legal transitions and terminal rules rather than from the searcher's material score?

**Smallest observation.** Reuse the position already present in the native mate-in-one test (`tests/test_h50b2a_semantic_native_search.py`) as FEN `8/8/8/1R6/8/8/5R2/k1K5 w - - 0 1`. Enumerate every legal root action and apply it once with Python semantic transition and, independently, native guarded action plus checked transition. Compare exact action identities and terminal status/winner. `scripts/audit_chess_root_terminal_labels.py` runs this finite check; `tests/test_chess_root_terminal_labels.py` freezes its expected result.

| Immediate child result | Root actions | Exact scope |
| --- | ---: | --- |
| Checkmate, White wins | 2 | Rb5a5, Rb5b1 |
| Stalemate, draw | 19 | Terminal draw |
| Ongoing | 10 | Eventual W/D/L unknown |

Both backends agree on all 31 legal actions and their immediate result. The root itself is ongoing. The two mate actions are certified winning choices under this RuleSet because the child is terminal; they supply a known achievable upper W/D/L outcome. Stalemate actions are certified draws. The remaining 10 actions are **not** labelled as losses or draws; that would require deeper exact analysis. Thus the fixture can test whether a search chooses an immediate win over an immediate draw, but cannot assign full root-action regret to every possible selected move.

**Decision.** Use these terminal labels as a bounded Chess validation fixture when a search comparison needs independent outcome evidence. Do not select a material formula with it. A quiescence-policy difference on this root would be informative only if the compared actions have certified distinct outcomes; if both select mate or an ongoing child, this fixture does not settle decision quality. Keep Standard Shogi as a later control and Xiangqi values sealed.
