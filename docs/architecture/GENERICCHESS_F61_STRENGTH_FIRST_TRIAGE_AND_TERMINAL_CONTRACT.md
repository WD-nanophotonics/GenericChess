# F61 strength-first triage and terminal contract

Status: offline evidence only; no promotion.

F61 was run from parent repository SHA `9d5c208f9486ccbbe8c7fb20dbb8ba5ab34b766c` and parent checkpoint `2c98cdd7c9e7b878decb15c2baf91b9d0150c65953e22481ce607d926ae43362`. The authoritative result is the transient JSON `f61_results.json`, SHA-256 `0CB77E4884C3D44CD41229E1B2076B060769B401B71203674C9CE7D0A8C084F3`; exact model parameters are preserved in the accompanying tracked F61 model-parameter artifact.

## Candidate provenance

The three candidates were reconstructed from the F60 fit/development source with disjoint source groups. F60 source IDs were D0 `b2c6f0a194ee781e86440c1537cc95c84a7b2982cda8c77236b5d5c91b3a0cec`, D1 `0223dc817fe1876e714d66f91c9c6fecf444af38b215b42078049beacdae987d`, and D2 `c7810c8fd1fd083b90b7939d72e75224642a6d829f1795a84e7417a77d903773`. The overlap matrix reports zero cross-distribution overlap and `d2_independent_from_d1=true`.

| Candidate | Objective | Seed | Model SHA-256 | Checkpoint ID |
|---|---|---:|---|---|
| F60_D0_PAIRWISE_SEED_59012 | PAIRWISE_RANKING | 59012 | `4c7198565335c67a2642e94a8855366d743e34b1acea27ae1f51611f832b31ab` | `15ea86075a15379bfa7758886ddb5855ceddcdbf540b33763130c3551875662a` |
| F60_D12_MEDIAN_DEVELOPMENT_SEED | PAIRWISE_RANKING | 59013 | `ba0b3ecc0b123dceba4e7649eef696593b6d7a64bf8616d856c5fd4c923b7224` | `1768912761b6dfc2826889f6ec80d024eb79ece06a6f61e9cd8087c2c2367f87` |
| F60_D2_MEDIAN_DEVELOPMENT_SEED | POINTWISE_Q | 59011 | `255bd567ab001b6e4a7a8a449b4c6d267b85b058b22cb13d52bfc83de8da752d` | `b352edefee0ebd226dca8345d60949f4d77122dd0592910bffefebec415168ae` |

All models have input dimension 2301 and width 32. The exact means, scales, weights, bias, target scale, regularization, and seed are in `GENERICCHESS_F61_MODEL_PARAMS.json`.

## Strength-first evidence

Search validation used 8 openings at 2,000 nodes per move. The first parent/child decision divergence is auditable as the first `decision_changed` row in each authoritative result; the runner now also records it directly as `search_validation.first_decision_divergence` for future runs. D0 changed 4/8 decisions and scored 3/8 paired games (0.375); D12 changed 6/8 and scored 3/8 (0.375). D2 changed 8/8 and won all 8 triage games (4/4 pairs), then won all 16 games in the 8-pair extension (8/8 pairs), and scored 56-0-8 in the 32-pair confirmation (24 better pairs, 8 tied, 0 worse; mean paired score 0.875; bootstrap interval 0.796875–0.953125). Wins were present for both child-owner roles (27/32 as owner 0 and 29/32 as owner 1 in the confirmation games).

The four-pair decision rule is explicit: a candidate is catastrophic only when mean paired score is at most 0.25 and it loses at least all but one pair; such a candidate is early-stopped. Otherwise `not_clearly_bad_after_4_pairs=true` and it may receive the 8-pair extension. Only a candidate that remains credible after that extension receives 32-pair confirmation. Teacher/development metrics remain diagnostic only; Arena parent/child behavior is the gate. No baseline contamination, role-label inversion, opening reuse, or parent/child asymmetry was found in the persisted provenance and paired-role counts.

## Terminal contract

`TrainingTrajectory` now records `termination_reason`, `truncated`, and optional `bootstrap_value`. Ongoing or truncated trajectories fail closed in `terminal_z` and TDLeaf unless a finite explicit bootstrap is supplied. Self-play marks max-ply cutoffs as `ongoing`/`truncated` with reason `max_plies`; serialization preserves the fields. Historical F50–F53 evidence is not reclassified.

The F61 result is a credible offline Arena signal for D2, not a promotion authorization. Any next-generation work must remain receipt-bound and preserve the same parent/child behavioral gate.
