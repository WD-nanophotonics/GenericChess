# F93 Chess alpha=.5 Arena8 confirmation

- Work order: `GENERICCHESS_F93_CHESS_ALPHA05_ARENA8`
- Baseline: `b325fed31d0a939ea9ddeb1552fb4c35a4542882`
- Ruleset: `A_CANONICAL_WESTERN_CHESS`
- Parent: `55249ef226ce60e51da8b6172881ea331757de0c72dbf918e48d84779dea1d5e`
- Frozen F61R4 raw child/model: `68136a6ea36fc9ab764bc7164e1fdb58c7cfbead718500dc9f51c0feedf0649f` / `855537bd5f473c557e22eba7b2fccd51142d5572599e4075d93dd127c2942950`
- Frozen F91 alpha=.5 child/model: `40d78f22eb90b24ef2f7318dee71dcd47d7dd2e7817fdc9a0eb64e426ff0fc0c` / `4c33ef1957a851e32c8b0d63cddf4d025c5044fd0680c370f5af1fa78ee8ff32`
- Exact Heavy run: `f93-chess-alpha05-arena8-v1-d7168a05d850`; the monitor died after 10 games, but the exact child completed the same resumable run. Runtime state was reconciled to completed after verifying all 16 terminal records.

Fresh Arena8 used seed `624701`, eight deterministic openings, one role-swapped pair per opening, 2,000 nodes/move, depth 12, TT 8 MiB, one worker, and equal parent/child budgets. All 16 games completed; no `no_contest` or truncation occurred.

Opening position keys:

1. `861f1f84f6991bc1c25cd8b775395439785b7816eab48d2004f4dc8d74e015b4`
2. `35fbe2c7fe45fb6917985fe6a8c66dfd33955dd8321d475c4ea482e20b7a9555`
3. `da771782336deffb0b041cc04908912135d15be91b512272358d2b43bd7e9321`
4. `0aca1c679567946ebace9438db1ecb734fe0ea467552fde9fd914a8ecbae41fb`
5. `e115659868df7d8aa38060bafc259d0db740b6889eaa858d3a616e997b912658`
6. `98419e77cad02502e216d6c135131a8d900cb6398a539e314b77290480076e8b`
7. `7f1122a3952bf1ee802d7631471d54e3eee1382f09fe7f410e095482597e3e02`
8. `e06382c886f8f6e76ede2a494a70915968eba700d531146baf50d2ed61eb380b`

| pair | child owner 0 | child owner 1 | pair score |
| ---: | --- | --- | ---: |
| 0 | checkmate / 136 | checkmate / 115 | 0.00 |
| 1 | max_ply / 998 | max_ply / 998 | 0.50 |
| 2 | checkmate / 25 | max_ply / 996 | 0.75 |
| 3 | checkmate / 65 | checkmate / 12 | 0.00 |
| 4 | max_ply / 997 | checkmate / 49 | 0.75 |
| 5 | max_ply / 995 | checkmate / 42 | 0.25 |
| 6 | max_ply / 997 | checkmate / 40 | 0.25 |
| 7 | checkmate / 80 | checkmate / 124 | 0.50 |

Aggregate: pair scores `[0.0, 0.5, 0.75, 0.0, 0.75, 0.25, 0.25, 0.5]`, mean `0.375`, better/tied/worse `2/2/4`, W/D/L `3/6/7`. The positive rule (`mean > .5` and better > worse) failed. Historical non-pooled context was F91 Arena2 mean `0.75` and F92 Arena4 mean `0.625`; these are not pooled with F93.

Decision: close the alpha=.5 Chess route. Do not run a final confirmation automatically, change alpha/objective/distribution/model seed/microvariant, run Shogi, or promote.
