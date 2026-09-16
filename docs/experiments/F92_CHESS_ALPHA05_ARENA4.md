# F92 Chess alpha=.5 Arena4 confirmation

- Work order: `GENERICCHESS_F92_CHESS_ALPHA05_ARENA4`
- Baseline: `579001a2d92efe8cd33483fa77bd73b545c09828`
- Ruleset: `A_CANONICAL_WESTERN_CHESS`
- Parent: `55249ef226ce60e51da8b6172881ea331757de0c72dbf918e48d84779dea1d5e`
- Frozen F61R4 raw child/model: `68136a6ea36fc9ab764bc7164e1fdb58c7cfbead718500dc9f51c0feedf0649f` / `855537bd5f473c557e22eba7b2fccd51142d5572599e4075d93dd127c2942950`
- Frozen F91 alpha=.5 child/model: `40d78f22eb90b24ef2f7318dee71dcd47d7dd2e7817fdc9a0eb64e426ff0fc0c` / `4c33ef1957a851e32c8b0d63cddf4d025c5044fd0680c370f5af1fa78ee8ff32`
- Candidate was restored from the persisted compact payload without refit or modification.

Fresh Arena4 used seed `623701`, four openings, one role-swapped pair per opening, 2,000 nodes/move, depth 12, TT 8 MiB, one worker, equal parent/child budgets. All 8 games completed; no `no_contest` or truncation occurred.

Opening position keys:

1. `f857f9ab53c740bad6ab0a6d6d7f2922a77ba246f2ff94e6edfb44bf828b1e09`
2. `cea473d815a12c99b230a657f2427899e5f93d15aa11a7825af8b73a040ade04`
3. `61426d1810a594ea6bdd26b540b7bc819f7936226e123f50379044b0cfaae88d`
4. `68b151bc4618cc6ead98bfa06235c441a52979e04035888d97ebc08ad0cfd149`

| pair | child owner 0 | child owner 1 | pair score |
| ---: | --- | --- | ---: |
| 0 | max_ply / 997 | checkmate / 83 | 0.75 |
| 1 | checkmate / 31 | max_ply / 997 | 0.25 |
| 2 | checkmate / 35 | checkmate / 85 | 0.50 |
| 3 | checkmate / 46 | checkmate / 35 | 1.00 |

Aggregate: pair scores `[0.75, 0.25, 0.5, 1.0]`, mean `0.625`, better/tied/worse `2/1/1`, W/D/L `4/2/2`. The positive rule (`mean > .5` and better > worse) passed. Per the order, retain alpha=.5 for a future Arena8 decision, but do not run Arena8 automatically, change the candidate, run another Chess/Shogi variant, or promote.
