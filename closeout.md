# F139 closeout

- Work order: `GENERICCHESS_F139_CORRECTED_SHOGI_RANK_COMPLETE_A1`
- Baseline: `ca19e3257b51cb6bdce6eb49e5692f51c1c15ce2`
- Scope: frozen F138 candidate-pool rank-capacity audit only; no new trajectories, A2/T1, self-play, MCTS, Arena, or feature changes.
- Heavy runtime: `439.9186713695526` seconds.
- Result artifact: `.generic_chess_flow/f139-shogi-result.json` (ignored transient evidence).

## F138 reproduction and dimension witness

- Corrected oracle SHA: `fdd6405ffa3f92de05f401dbd12d00a16191ac10c2ba2383fe5332694c9e7aa6`.
- Feature-name SHA: `6accfab1039a546071a23c885d582a2c10792e5db49f69bfa9556c131d516942`.
- Corpus: 3000/750/750, seed `1220201`, identity `a1cb1bcf2d461c3bddc4f87928ed4d6260673de268356eec5741b9b534d4aa8b`.
- Reproduced F138 candidate pool: `6125` candidates, `37066` inspected legal ongoing states, `342` trajectories, and `25` selected witnesses.
- Reproduced F138 training count `3044`, dev `731`, holdout `750`, and holdout scalar nRMSE `0.14352245864710567`.
- New active columns: `109`; added training rows: `44`; rank gain: `44`; excess nullity: `65`.
- Every newly active feature was constant on the original 3000-state training split.

## Frozen active-set capacity

- No-new-active candidates: `2096`; excluded candidates: `4029`.
- Current rank `696`; attainable rank with the full eligible candidate pool `751`; attainable nullity `23`.
- Required rank was `761`, so the existing deterministic pool cannot provide the required 65 independent witnesses.

## Classification and routing

`F139_EXISTING_CANDIDATE_POOL_INSUFFICIENT_FOR_RANK_COMPLETION`

The frozen F138 candidate pool cannot complete the active row space to rank 761 without activating additional coordinates. No additional trajectories were generated and no rank-completion fit was attempted. The next order may authorize targeted rank-generation; do not broaden random data or start A2/T1. F129-F138 semantic conclusions remain quarantined.
