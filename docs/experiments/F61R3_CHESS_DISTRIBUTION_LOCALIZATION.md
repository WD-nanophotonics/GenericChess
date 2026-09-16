# F61R3 Chess training-distribution localization

## Purpose

Compare native self-play and PV-corridor training distributions while holding
the F61R2 `POINTWISE_Q` learner and Chess Arena configuration fixed.

## Frozen configuration

- Ruleset: canonical Western Chess; same parent checkpoint, model seed `59012`,
  model width, regularization, optimizer/update count, features, and q20
  supervision/search budgets as F61R2.
- Source construction: one deterministic Chess pass using native self-play for
  D1 and an independent native-self-play pool followed by native-search PV
  continuation for D2. The resulting D1 and D2 root sets are disjoint. The
  source pass used 8 self-play games at 500 nodes/move because the default
  4-game/50-node Chess smoke pass produced fewer than F60's required 3
  nonempty source groups; this adjustment affected source acquisition only.
- Arena: opening seed `620701` and the same 2 deterministic openings; 2
  role-swapped pairs per candidate (4 games); 100 nodes/move; depth 4; 2 MiB
  transposition table; 1 worker; equal parent and child budgets.

## Candidate bindings and outcomes

- `D1_V2_SELFPLAY`: source ID
  `47bcaff6ae8149fd61b800a4b95ede3de3864454ef48f191118ec0348021de54`;
  training roots 6, actions 20; child checkpoint
  `23df6e647a038c1471f77af9231a5c707166c0e5f4b70e6cbe929b057a4879bf`;
  model SHA256 `79aa51637fbd01d4c935c7c5851a6edc4dbd2af9b1e61cb397c2ad023570d2e4`;
  pair scores `[0.5, 0.5]`, mean `0.5`, 0 better / 2 tied / 0 worse pairs,
  WDL `0-4-0`, `directional_failure=false`. Training root keys:
  `9429cdba551765e4b135f2f86d9e699020fbd513c2c129472488a326be753d2f`,
  `7e10222207d572e1be97e8221ff68705d024cc8390dcc0b8835d3c436bf12ef1`,
  `2f7af188c4becc6e83f325a6c1d7008baef2c2972b99269d9d416e70bb508064`,
  `c5a76da961cb3322086dde3c62045ba1eb1df2a7d39c65053c2e919a4ec8e922`,
  `3766c4ce3e3264b3a05718ae7abb03818563edc47a022c46b4a42f68bb5676e9`,
  `37cb96b6e7afd48cac781d40028ad87e73fb0d8bfcbc6a80b3945902b9c7ebb8`.
- `D2_V2_PV_CORRIDOR`: source ID
  `a7cd67a36d9e7d7bb084dd8d17bc9b2877a1e38c768a788573191b93760c3b1b`;
  training roots 2, actions 5; child checkpoint
  `af5c2e93ca6e9e1d948d965df783f715e365d286407a21a1bf98d41165c2ca1b`;
  model SHA256 `3ea3bc46e07c26a89320d9af2cd8b357032119aaecb2f5e4335b7e557b363848`;
  pair scores `[0.5, 0.0]`, mean `0.25`, 0 better / 1 tied / 1 worse pair,
  WDL `0-2-2`, `directional_failure=true`. Training root keys:
  `4a601daa050534950f8f305017e8614128d76cac1a2c2521ae54fe05a249cad3`,
  `d16eaf7c2e94aa89cb8fb2880b90404010653bed4480f062f40af33fc7945cfc`.

Both arms use record seed `620100` and the same arena opening identities:
`64587165d620ad1557b7e937e317b8045514e554f94faf9448ceb15806c24e38` and
`f199858b78f4e1bd5eccf1acec532a53f71a30e4ed22209d30bef26031757b0c`.

## Interpretation and limitation

D2 is rejected from immediate expansion because it is a directional failure.
D1 is neutral at 0.5 and is not a positive strength signal. This tiny pilot is
not a stable win-rate estimate or a general claim about either distribution;
it is sufficient to stop this comparison and return for the next algorithmic
decision. No distribution mixing, extra roots, seeds, objectives, or Arena
pairs were added.
