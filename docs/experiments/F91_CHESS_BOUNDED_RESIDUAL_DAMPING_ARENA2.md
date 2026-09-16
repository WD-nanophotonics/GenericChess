# F91 Chess bounded residual damping Arena2

- Work order: `GENERICCHESS_F91_CHESS_BOUNDED_RESIDUAL_DAMPING_ARENA2`
- Parent: `55249ef226ce60e51da8b6172881ea331757de0c72dbf918e48d84779dea1d5e`
- Frozen F61R4 raw child: `68136a6ea36fc9ab764bc7164e1fdb58c7cfbead718500dc9f51c0feedf0649f`
- Frozen raw model SHA256: `855537bd5f473c557e22eba7b2fccd51142d5572599e4075d93dd127c2942950`
- Ruleset: `A_CANONICAL_WESTERN_CHESS` (`7bc6cf3179f4eaea30b205576b9032dca47a16803e9cc8b3e29405cb1e820b35`)
- Data/fit: F61R4 cached spectra only; 24 roots/161 actions; `POINTWISE_Q`; model seed `59012`; no refit or new data.

## Construction and correctness

Each candidate retained the raw F61R4 input normalization, target scale, hidden weights, and hidden bias. Only `output_weights` and `output_bias` were multiplied by alpha; parent board, hand, dynamic, spatial, and localized fields were retained unchanged.

The alpha-zero correctness gate passed: compact residual maximum absolute value was `0.0` on the 161 frozen action rows and the parent evaluator was preserved. Candidate model/checkpoint identities:

| alpha | child checkpoint | model SHA256 |
| ---: | --- | --- |
| 0.5 | `40d78f22eb90b24ef2f7318dee71dcd47d7dd2e7817fdc9a0eb64e426ff0fc0c` | `4c33ef1957a851e32c8b0d63cddf4d025c5044fd0680c370f5af1fa78ee8ff32` |
| 0.25 | `2bb81731ef5227e6dad861ff73e03f08620e4a5821c03e57d8147e44ce969025` | `72fbb675b3b069e3cb9b9c7bfed2cdb8c1c5d19b43051a6b0834847d02670caf` |

## Fresh Arena2

Opening seed `622701` produced opening IDs `0140aa62a3e4faed4764f4ab4e950eb7d85e2cf6849c52400c531c09c1953c36` and `34de46ffbab9fd56eb15662baecbf3cff830b93d1f0640411fc71aa1a208f886`. Each candidate played two role-swapped pairs (four games), parent and child both at 2,000 nodes/move, depth 12, TT 8 MiB, one worker. All 8 games completed without `no_contest`.

| alpha | pair scores | mean | better/tied/worse | W/D/L | game plies |
| ---: | --- | ---: | --- | --- | --- |
| 0.5 | `[0.75, 0.75]` | `0.75` | `2/0/0` | `2/2/0` | `47, 998, 996, 76` |
| 0.25 | `[0.25, 0.25]` | `0.25` | `0/0/2` | `0/2/2` | `998, 117, 40, 996` |

Decision rule (`mean > .5` and better > worse) selects alpha `0.5` as the sole positive candidate. Per the order, stop the bounded damping probe here; no Arena4/Arena8, alternate alpha, objective, distribution, seed, or promotion is authorized by this result.
