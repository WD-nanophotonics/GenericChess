# AlphaBeta child-node declaration decisions — 2026-10-20

## Question

Does the public AlphaBeta caller account for a declaration that becomes
available to the opponent after a candidate move, and can that option change
the parent decision?

## Controlled fixtures

The product-test `opaque_claim` fixture gives owner 0 a zone-based material claim.
The parent is owner 1 to move, with an owner-1 rook on b8 and owner 0's rook on
b1. A b8-b1 capture lowers the claim score; other legal moves leave the claim
available to owner 0 on the child. The search is depth 1, qdepth 0, with a
test-only evaluator, no native legality provider, and the production TT and
move-ordering path enabled. `reference_minimax` is the bounded control.

For a child `WIN`, both AlphaBeta and the reference choose the claim-removing
rook capture, score 0, and leave the submitted parent state unchanged. With the
same board but no declaration rule, both choose a king move instead. AlphaBeta
records child declaration checks and WIN options. Thus this result is sensitive
to the opponent's child-node declaration, not just a root declaration.

A second fixture uses the same transition with a `RESTART` claim. Its test-only
evaluator assigns -5 to a child retaining owner 0's rook and -1 after the
capture; these values only separate branches and are not utility evidence. With
the neutral child option, AlphaBeta and reference choose the capture at score
1; with declarations removed, both choose the king move at score 5. Repeating
the source probe across TT/order on/off combinations preserved reference scores
and the respective action contrast for this evaluator.

The same controlled child-floor regression is parameterized over `RESTART` and
`NO_CONTEST`; both outcomes produce the same score/action contrast and both
leave the root unchanged. This verifies the public search's neutral treatment
without claiming that a `NO_CONTEST` declaration is a draw in external game
accounting.

## Interpretation and scope

The current search implementation already handles child WIN, RESTART and
NO_CONTEST outcomes; no production search or interface change is warranted.
Two focused product regressions protect the decision-changing WIN and neutral
floor cases on the production TT-plus-ordering path and check reference
agreement and root immutability. A separate adjacent persistence defect was
found: the record writer serialized valid NO_CONTEST declarations but the
reader rejected them. The reader now uses the rule schema's shared outcome set,
and a four-outcome session serialize/deserialize/replay regression covers it.
The real benchmark game caller is also parameterized to keep both neutral
declarations unresolved rather than turning either into a draw or failure; see
`DECLARATION_NO_CONTEST_RECORD_ROUNDTRIP_20261020.md`. This is a synthetic
one-ply search contract plus a focused persistence fix, not a generic
strength/WDL result, a broad declaration-rule survey, or evidence about price
ratios. The test-only evaluator is not a fitted or reported playing evaluation.
