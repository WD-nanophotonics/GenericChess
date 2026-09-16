# F94 Chess zero-residual anchored update

- Work order: `GENERICCHESS_F94_CHESS_ZERO_RESIDUAL_ANCHORED_UPDATE_ARENA2`
- Baseline: `3b8bcce28a543eeb6117e5c658a0c5d7aa675c4a`
- Ruleset: `A_CANONICAL_WESTERN_CHESS`
- Parent: `55249ef226ce60e51da8b6172881ea331757de0c72dbf918e48d84779dea1d5e`
- Frozen F61R4 raw child/model used only for provenance and residual cap: `68136a6ea36fc9ab764bc7164e1fdb58c7cfbead718500dc9f51c0feedf0649f` / `855537bd5f473c557e22eba7b2fccd51142d5572599e4075d93dd127c2942950`
- Training data: exactly the cached F61R4 D1_V2_SELFPLAY evidence, 24 roots and 161 action rows; no new self-play or teacher searches.

The width-32 seed-59012 anchor reused the F61R4 input mean, input scale, and target scale; hidden weights were deterministically initialized with the F61 fitter rule, hidden bias and output weights started at zero, and output bias stayed fixed at zero. The correctness gate passed: zero-anchor residual max abs `0.0`, exact zero residual, parent total-Q reproduction exact, and parent board/hand/dynamic/spatial/localized fields unchanged.

One candidate was fit from that anchor with POINTWISE_Q, 100 full-batch Adam steps, learning rate `0.001`, and proximal coefficient `0.001`, training only hidden weights, hidden bias, and output weights. Objective before fitting was `0.5011332981263108`; raw objective was `0.09458714216525925`. Raw parameter-delta norms were hidden weights `2.2120531505892895`, hidden bias `0.26605077542490574`, and output weights `0.5938144008928445`; delta SHA256 was `385cade7dec9b26d77fda1fbb679c59e1689ed4d522dd33e7c763faad5d1da93`.

| alpha | safe | objective | objective improved | q20-stable tops retained | upper-quartile tops retained | residual cap | max abs residual |
| ---: | :---: | ---: | :---: | :---: | :---: | :---: | ---: |
| 1.0 | no | 0.0945871422 | yes | no | yes | yes | 548.8061835 |
| 0.5 | no | 0.3035368663 | yes | no | no | yes | 238.4582221 |
| 0.25 | no | 0.4277494242 | yes | no | no | yes | 86.0392073 |
| 0.125 | no | 0.4739136240 | yes | no | yes | yes | 30.8672061 |
| 0.0625 | no | 0.4901111426 | yes | no | yes | yes | 13.0743384 |
| 0.03125 | no | 0.4962812701 | yes | no | yes | yes | 5.9333397 |
| 0.015625 | no | 0.4988725646 | yes | no | yes | yes | 2.9515129 |
| 0.0078125 | no | 0.5000442546 | yes | no | yes | yes | 1.4864310 |

No allowed alpha satisfied all safety conditions; in particular, every candidate failed the q20-stable-top retention condition. Classification: `NO_SAFE_ANCHORED_UPDATE`. No child checkpoint was frozen and no Arena2 was run. Per the work order, do not try another seed, objective, data distribution, optimizer setting, alpha family, architecture, Arena stage, Shogi run, or promotion.
