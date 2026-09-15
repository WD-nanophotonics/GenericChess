# F87R1 compact rebuild and Arena4 closeout

The corrected fixed-slot parent was rebuilt exactly once with seeds 870401 and
870402. Both trajectories passed the Stage-A gates (128 roots, 5928 action
rows, objective 395.79037498687774 to 11.7279282253657, finite residuals and
the existing residual safety bound). The compact candidate is checkpoint
`0c94b1d6b0a0b66939707d1e4184e23cc1391678c7bda67267d834a7565a5c42`.

The single approved role-swapped Arena4 pair used opening index 2 from corpus
`593652dd655ddc67f38d9a194b9b2a44f7eef3e28d22a83c5f01abeb35b971a1`, seed
820401, 512 nodes/move, depth 12, TT 8 MiB, and TT reset each move. Both games
completed: one parent-side win and one candidate-side win, for pair score 0.5.
Per the work order this is a neutral triage result; no second pair or follow-on
compute is authorized.

Durable result: `artifacts/f87_two_trajectory_native_search_distillation/arena4_result.json`.
