# Actual auxiliary training/DEV entry contract —2026-10-15

Scope: the working `python -m scripts.generic_proof_scaled_study run FOLDER`
entry used by frozen1797/1798. This is an inspected call-chain map, not a new
production API or permission to rerun a frozen study. No entry was deleted.

| Stage | Actual dependency and state conversion | Evidence / boundary |
|---|---|---|
| Frozen plan | `generic_proof_scaled_study.execute` reads plan and checks its own and SizedNativeDriver SHA | Plan carries roots, TRAIN/DEV labels, prices, opponent budgets, H and all run caps |
| Shared study | `generic_proof_native_study.run(...driver_class=SizedNativeDriver)` checks study/player/prover/tail/roles/PN hashes | Current multi-H successor additionally checks scheduler hash; old frozen files are retained |
| Driver | `generic_proof_native_driver.SizedNativeDriver` checks binary, variant.ini and RoyalActor source | Sized route uses RoyalActor(width), not the legacy stock/tablebase driver; no stock-win reward, no cache |
| Public state | `generic_proof_rnb_bridge.from_actor` builds full initial GameState; `compile_rnb` compiles same K/R/N/B movement rules | Price/root selection does not alter rules. Full public apply_action owns terminal/history/repetition/max_ply |
| Frontier | Study compares public legal set and every child with literal RoyalActor at roots/children and actual search frontiers | Authoritative GameState is retained between moves; actor tuple is a scoped no-drop/no-promotion bridge, not generic full-history serialization |
| Player | `ProofMaterialPlayer.choose` uses fixed prover and independently verified cursor; ordinary external callback receives remaining visits/time | Proof/verification each at most quarter; actual Native overshoot/time retained. Post-atomic terminal and cursor polls close the observed cancellation gap |
| Mature callback | Full board actor tuple -> engine FEN; cold profile ACK -> `devauxleafrnbp` -> bounded go -> legal returned action | Leaf, native and capture prices aligned. Engine repetition/50-move rules disabled; public Core history adjudicates actual games. This is modified material-only Fairy, not stock NNUE |
| Training | Complete actual TRAIN grid before `selection.json`; strict adjacent paths share paid grid; tie policy frozen | Unfinished finite game contributes zero W-L events, remains UNKNOWN. No DEV price fitting or human-price tuning |
| DEV | Prior TRAIN-selected and baseline prices; both physical roles/colors/opponents; opponent_proof explicitly fixed in1797/1798 | Earlier A/C vs B/D changed opponent policy and cannot isolate candidate solver interaction |
| Completion | Every actual move observed by both cursors and applied publicly; at H only already verified rank-limited tail admitted | No proof after H; actual Session/Core terminal earns reward, theoretical certificate alone does not |
| Output | run/start, games, choices, acks, INTENT/SENT journal, game_events, result and selection | Partial game remains explicit. Audits independently replay states/actions, actual prices/budgets and complete planned slots |

Configuration/result coupling is real: older study result cells aggregate proof
and price and assume a single H. New H16/H24 report must audit separate recorded
H views and preserve exact source-order receipt slices, then compare families;
never feed mixed horizons into the old single-H contrast. The shared runner still
imports the old driver module to define its fallback class even when Sized is
used. This is an engineering dependency, not evidence of stock/tablebase use.

This audit does not establish complete source closure from plan hashes alone:
bridge/compiled-rule dependencies extend beyond the direct hash fields. Preserve
exact execution source snapshots and relevant tests with evidence archives.
Do not replace historical file paths or bulk refactor configuration/result APIs
merely to reduce this map; qualify one supported entry before changing consumers.

## Already-paid factorial correction

`generic_proof_factorial_report` consumes only existing1797/1798 records and
TRAIN selections (0new games/go,0retraining). It requires fixed opponent policy,
reports C-to-D beside A-to-B and the interaction (D-C)-(B-A), with whole-family
paired intervals, all W/L/draw/UNKNOWN transitions and actual time/go/nodes.

1797: C/D both net10/64; +2wins and +2losses, eventdelta0; actual game time
30.440679->54.943160s. All8 family net effects0 does not establish future null.
1798: Cnet8/64->Dnet10/64; +2 UNKNOWN->WIN; delta+.03125, family95[0,.09375],
interaction+.03125 same interval. Actual time26.791882->43.912238s. One of8
families supplies the signal. This is exploratory, not evidence that the solver
caused price learning to succeed in general. Old large both-policy cohorts
cannot isolate this interaction; their B-to-D price contrast remains valid.
