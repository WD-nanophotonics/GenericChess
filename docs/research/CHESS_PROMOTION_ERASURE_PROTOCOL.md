# New captured-current-type erasure controls

Use exact saved root-child states from chess_knight_interposition selections;
do not regenerate them. Full history stays ply1/two records/counts1. The Q
promotion child's Q h8xe8 mate is already observed; never rerun that edge.
NEW edges are the identical enemy public capture in the three previously
unobserved B/N/R promotion children. Enumerate each full reply list before apply,
then one actual public capture and exact terminal. Expected same resulting board,
origin/aux and checkmate, retaining distinct preceding history keys.
No reply batches beyond three named edges and no new coefficient/source queries.

Same accumulated caps:77 prior recorded events plus0..5 unrecorded upper plus
3 new events<=128; prior2696 explicit entries plus new complete enumeration/
membership<=5000;128 choices/node;15sec cooperative cumulative computation with
1.656sec conservatively charged previous/failure phases. Save all results.

If all four promotion branches admit an actual immediate checkmate reply, their
root-player minimax values are exactly-1. Remaining Kxd7 branch is[-1,1]; it
is therefore weakly optimal, not proved nonlosing or strictly better. Contact
regret interval is[0,2], unit/zero regret0 for this FULL root table. Conditional
proof uses only payoff range and preserved public mate witnesses, not Gaviota.
This is a noncutoff independent certificate; no full-game improvement claim.
