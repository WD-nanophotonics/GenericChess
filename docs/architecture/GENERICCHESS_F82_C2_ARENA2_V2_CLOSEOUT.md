# F82 C2 Arena2 v2 closeout

- Work order: `GENERICCHESS-C2-PARENT-ANCHORED-FULL-RESIDUAL-REPEATABILITY`
- Published implementation SHA: `35388df61b13dbfcff63d5b9b571361dd48699aa`
- Compute plan: `f82-c2-arena2-v2`
- Plan SHA: `d8be6bfbcb3889ca60dbab6d9fbc82f40d8d8570d4f237df95dfe1384050877c`
- Supervisor-bound envelope SHA: `ca7885343e0604262a60207f2888a35c87b4364910a34650a0382fac082b7458`
- Chat approval response SHA: `9e93a2b710bf29b16c1b45e165c17ac1c50920579272c019b827feda7b4eefa2`
- Heavy run: `f82-c2-arena2-v2-f86119dc26a0`

The repaired CLI was tested and published before Heavy. The run used only the
registered Arena2 corpus (`6eca12faa0981e1c71f637eae7f66ee4a053193a752fbe592d2b0edafbdffd2a`),
the single candidate checkpoint `86f026ef85d60e600bc1bd6bc7b7285f11e5ce7e6528911b2ea361a489dc5983`,
512 nodes/move, depth 12, TT 8 MiB, one lane, and the approved 4-game/2-pair
caps.

Outcome: `INCOMPLETE`, with 1 of 4 games complete and 0 of 2 role-swapped
pairs complete. The runner stopped at the registered `stage_wall_seconds`
boundary. The valid atomic checkpoint for `game-000000-owner-0.json` remains
in runtime state; no Arena4, Arena8, final-confirmation, promotion, candidate
change, or resource expansion was performed.
