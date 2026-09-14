# F61 Standard-Shogi R20 search-transfer witness

R20 reconstructed the fixed R16/R17 POINTWISE_Q child from the persisted 24
D0 spectra and evaluated exactly the four frozen seed-620700 Standard-Shogi
openings. No retraining, new roots, full F59 trust spectrum, Arena games, or
strength claim was made.

## Immutable execution

- Published checkpoint: `0f1fdb4a1edaefa0c3da05ff9c301ce617cf8d99`
- Parent: `2c98cdd7c9e7b878decb15c2baf91b9d0150c65953e22481ce607d926ae43362`
- Fixed child: `78bfa7cad9cc21ecfc95fd166566b25d3c954033b413660a7c398498dd6c571b`
- Model SHA256: `c6330b17fc11093cd404e204d3a6f461307971f2458e55d0147c4cc21c0f239c`
- Training reconstruction: seed `59013`, 24 persisted D0 roots, 157 actions
- Witness artifact: `.generic_chess_flow/f61-gen0-gen1-strength-triage/pointwise_search_transfer_witness.json`

Each witness used the parent cheap-1k top six, parent 2k and 80k actions, and
the child 2k action, deduplicated. Each retained action received one parent
q20 label at 20,000 nodes using the existing successor-root-Q semantics.

## Value-transfer layer

Across 87 comparable action pairs:

| prediction | MSE | pairwise ranking accuracy |
| --- | ---: | ---: |
| base-Q | 48,870.5667 | 0.9540 |
| base-Q + POINTWISE_Q residual | 116,489.6736 | 0.8736 |

The learned one-ply top action had zero teacher regret on all four roots, but
the base-Q top action also had zero regret on all four. Thus the learned value
did not improve top-action regret and was materially worse in MSE and ranking.

## Search-transfer layer

The parent 2k search selected a zero-regret teacher action on all four roots.
The child 2k search selected actions with q20 regrets `[398, 773, 393, 401]`,
mean `491.25`. The learned one-ply best action had zero regret on all four.

## Interpretation

This witness is classified `LEARNING_UPSTREAM_FAILURE`: the fixed child does
not improve held-out value prediction over base-Q, while recursive child search
also loses the locally available teacher action. The result points first to
learning/generalization, not a search-only fix. It is diagnostic evidence only
and does not authorize promotion or another Arena block.

