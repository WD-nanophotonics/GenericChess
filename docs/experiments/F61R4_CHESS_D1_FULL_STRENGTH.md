# F61R4 Chess D1 full-strength diagnostic

## Frozen route

- Ruleset: `A_CANONICAL_WESTERN_CHESS`; parent checkpoint
  `55249ef226ce60e51da8b6172881ea331757de0c72dbf918e48d84779dea1d5e`.
- Distribution: `D1_V2_SELFPLAY` only; objective `POINTWISE_Q`; model seed
  `59012`; source seed `620100`; unchanged representation, width,
  regularization, optimizer, update count, and full F61 search budgets.
- Source configuration: 2 games, 2000 nodes/move, depth 12, 24 maximum
  plies, epsilon 0.1, TT 8 MiB. Source ID
  `b3e97260cc3d437f756180bd767cf2ff890775f74e01e27ec2db5432911ecad9`;
  24 training roots, 161 actions. No D0 or D2 roots were admitted.
- Fresh Arena: opening seed `621701`, 4 deterministic openings, 2-6 opening
  plies, 4 role-swapped pairs / 8 games, equal parent/child budgets at 2000
  nodes/move, depth 12, TT 8 MiB, one worker.

Training root keys, in deterministic order:

`9429cdba551765e4b135f2f86d9e699020fbd513c2c129472488a326be753d2f`,
`7e10222207d572e1be97e8221ff68705d024cc8390dcc0b8835d3c436bf12ef1`,
`3766c4ce3e3264b3a05718ae7abb03818563edc47a022c46b4a42f68bb5676e9`,
`37cb96b6e7afd48cac781d40028ad87e73fb0d8bfcbc6a80b3945902b9c7ebb8`,
`f3079d3238a7b9481e4258486e15466fe569b062545e60936e71f9b86567f393`,
`11ac2d545f77769f60150a1e746f8277a2a95fc8f93b705da7ea622729156e3f`,
`ba49b8574a11aeb523f4f09262930b5b29f8e0d17a276cc4eb05f163e6d86ba0`,
`731e93a531e2ea14a6d93c63cbcc74da52a33672eef17ae2d4f074a076e0e78e`,
`4a0b5fdf57e5c09d4745655cf71aaca277a68b389c20445d738ef6a3798d19d`,
`d8aa92009fae63d8d49b24390ca1221bd3c90d6c89f1fa866db43a9a9e36d14c`,
`981ba3bd8a30726407711de562d8b245e7679171a08cc7a7be918dffd3ef7806`,
`fe151596e2ce9ce958036946797762064a0a7376d9a5c85f6ab630f622abf12c`,
`e3a3cb15583138468db1dd1fe01b2040d5a97a305e17c85f18c99d3c10d7f344`,
`3961ac4ca865914fc8eef8f3a0ff8c8a333d93c3e6cf73f7a92b085e37eca16c`,
`c7efd11f9487e5ae6553cf7cfefe5156e146acd9b984b2c063694741325b5bfd`,
`0d158957f870563eac669947472e42cfe7173f3c5d783569cba5df010211a604`,
`ee01e9d7a534fdf9c83f20ab97a92109bf458d0f5f2e15d9acaf57d1e153df61`,
`a7cd0395632b7565449003c3d0c742850c1b6a5a2d745ffb80af2464a7e9bb25`,
`b9b61df56063d4877715908729475b6231ac5a5bcd7f7b2516a35dbe96e93104`,
`4f245eebeef1208a3e2aa466fe6f89981c761dfe5e77b488d44cb4c23e1c10f8`,
`983b1c4e147e48d66df0237ff2a7e8ad3e5cc441a7a83e02030baa06db583aba`,
`0f158ec517b49ce32dfefd204b5e9d1988351c3a23033d05026acf489eda9969`,
`12a3aac0bfe999afb809d1fb4243ced6c9dfb31bf746c741a590170c7e02a3c0`,
`f50ec7a08070fdfabb97e204d844d42dbac031c643e06e2be77ef67ecbf78649`.

## Result

Child checkpoint: `68136a6ea36fc9ab764bc7164e1fdb58c7cfbead718500dc9f51c0feedf0649f`;
model SHA256 `855537bd5f473c557e22eba7b2fccd51142d5572599e4075d93dd127c2942950`.
Arena opening keys, in order:

`a97e06ff5ecc29db867809f02f86fd039ffe5de2d23b44eaa988fbe40fde7c69`,
`d68fb0a87c4967c4aa432eab1434b88a38bcac50f763e19a11408300f4cda521`,
`1165bfe998c91e4de8ee011b5c675a964049df293fc8217b10a177f8344e67e6`,
`9cc9891d7788d7913a89f1b06280b800e4418e1e90029027bf1f94128b5387c9`.

Pair scores were `[0.25, 0.25, 0.5, 0.5]`, mean `0.375`, with 0 better,
2 tied, and 2 worse pairs. Game W/D/L was `1/4/3`. Terminal games were:

| pair | child owner | result | plies |
|---:|---:|---|---:|
| 0 | 0 | max_ply | 996 |
| 0 | 1 | checkmate, parent win | 63 |
| 1 | 0 | max_ply | 997 |
| 1 | 1 | checkmate, parent win | 60 |
| 2 | 0 | checkmate, parent win | 57 |
| 2 | 1 | checkmate, parent win | 29 |
| 3 | 0 | max_ply | 996 |
| 3 | 1 | max_ply | 996 |

The run is complete, with `zero_or_truncated=false` and no incomplete state.
The predeclared positive boundary (`mean > 0.5` and child better pairs greater
than child worse pairs) was not met; `directional_failure=true`. Stop this
Chess D1 + POINTWISE_Q micro-diagnostic: do not run F61R5, alternate Chess
micro-variants, or Arena8. Return to Chat for the Shogi comparison / learner
redesign decision.
