# F95 Chess fixed-feature output correction Arena2

Work order: `GENERICCHESS_F95_CHESS_FIXED_FEATURE_OUTPUT_CORRECTION_ARENA2`

Baseline: `7ec61fdb465abb77eaabcae4b343b12495b2c821`

Scope was exactly `A_CANONICAL_WESTERN_CHESS`. The experiment reused parent
checkpoint `55249ef226ce60e51da8b6172881ea331757de0c72dbf918e48d84779dea1d5e`,
the frozen F61R4 raw child
`68136a6ea36fc9ab764bc7164e1fdb58c7cfbead718500dc9f51c0feedf0649f`, raw
model SHA256
`855537bd5f473c557e22eba7b2fccd51142d5572599e4075d93dd127c2942950`, and
the cached 24-root / 161-action F61R4 D1 evidence. No new self-play or
teacher search was used.

## Construction

The nonlinear feature map (input normalization, hidden weights, and hidden
bias) was frozen exactly. A zero-output anchor reproduced the parent on all
161 rows with exact zero residual; parent total-Q and the other evaluator
fields were unchanged. The persisted feature-map identity was
`edf581036fd635468159d034a4c295ee49a25ad088893f35cd7a2ed6fa51b278`.

The output-only correction solved

`mean((h_i · w - (q20_i - base_q_i) / target_scale)^2) + 0.001 ||w||^2`

directly with no Adam, alternate objective, seed, regularization, or feature
refit. Objective improved from `0.5011332981263108` to
`0.00005379242749125763`. Raw output-weight norm was
`1.3167486746675228`, with SHA256
`4b8267c5259edb98a8c57aa0f36b7e676e0907f8c5e51afe73175cd8724e487f`.

## Analytic safety gate

The upper-quartile parent-gap threshold was `13.5`. Nineteen exact protected
root/competitor breakpoints were recorded. The limiting breakpoint was
`alpha=0.9950113038270905` at root 4, where parent action
`Q(6,3)->(1,3)` meets competitor `Q(6,3)->(6,6)` under the upper-quartile
gap protection. The deterministic key tie rule was included; the selected
candidate was exactly half that boundary:
`alpha*=0.49750565191354523`.

At the selected alpha, all outputs were finite, the objective was
`0.12701009914160694`, protected parent tops were retained, and maximum
absolute residual was `518.0167119663854`, below the failed raw F61R4 cap
`1036.234945679445`. At alpha 1, protected-top retention and the residual cap
failed, so the analytic boundary rule was required.

Candidate checkpoint: `d2ca69ede6b7a874c8f50287c1a762192c709f156f859a760b08ee7e90a65bd1`

Candidate compact model SHA256:
`0238eec36fb9ae930bd2a58ceab42f967f3b99533aa82a55c8481e4b0fbd6960`

## Fresh Arena2

The candidate was evaluated with the declared envelope
`f95-chess-fixed-feature-output-correction-arena2-v1`, opening seed `626701`,
two deterministic openings, one role-swapped pair per opening, 2,000
nodes/move for both sides, depth 12, 8 MiB TT, one worker, and resumable
semantics. Opening position keys were:

* `31709de946b149dc18ab4f3da12b2c8705df2e508d8d28dde6e4c401eb968c5f`
* `1c261fd7bf411e16c3b77f8647ff38ab41cb8be8bb1f0ad8d221f7c08dce7047`

All 4 games completed with no no-contest/truncation. Pair scores were
`[0.5, 0.25]`, mean `0.375`, with 0 better / 1 tied / 1 worse pair and game
W/D/L `0/3/1`. The games were:

* Pair 0, owner 0: max-ply, 998 plies, draw.
* Pair 0, owner 1: max-ply, 998 plies, draw.
* Pair 1, owner 0: checkmate, 18 plies, parent win.
* Pair 1, owner 1: max-ply, 998 plies, draw.

## Decision

The fixed-feature output-correction route is rejected because the mean pair
score was not greater than 0.5 and the child did not win more pairs. No
Arena4, alternate feature map, regularization, objective, seed, architecture,
or Shogi run was started, and no promotion was requested.
