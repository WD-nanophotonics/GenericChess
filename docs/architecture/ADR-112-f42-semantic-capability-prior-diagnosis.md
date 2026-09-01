# ADR-112: F42 semantic capability-prior diagnosis

- Status: Accepted diagnosis-only F42 boundary
- Baseline: `fa9a9c334fce331a5059f05a3e261e1fd85fbc7c`
- H42A protocol: `tests/fixtures/f42_capability_prior_manifest.json`
- Audit implementation: `scripts/audit_f42_semantic_capability_prior.py`
- Production change: none; no evaluator formula was integrated

## Decision

The primary diagnosis is `RAY_OR_DIRECTIONAL_SCALING_PRIMARY`. The next
boundary is `F43_CAPABILITY_GEOMETRY_SCALING_PROTOTYPE`.

The accepted F41 R1 reproduction matched exactly before diagnosis: Western
raw scores were P `1.06228880393026`, N `4.815702525575447`, B
`6.217622245358478`, R `9.08791486310959`, Q `15.163483676173186`; normalized
values were P `171`, N `775`, B `1000`, R `1462`, Q `2439`. The normalized
ratios were N/P `4.5321637426900585`, B/P `5.847953216374269`, R/P
`8.549707602339181`, and Q/P `14.263157894736842`. Standard Shogi retained
cosine `0.9999953399256223`, Spearman `1.0`, pairwise ordering `1.0`, and
hand/board ratios within the accepted `0.8..1.0` gate.

## Causal component ledger

The four terms are measured from the same executable semantic candidate graph:
density-weighted expected mobility, one-hop destination coverage, transitive
reachable-pair ratio, and reciprocal average shortest path. Weighted
contributions below are `mobility*1.0`, `coverage*0.10`,
`reachability*0.05`, and `path efficiency*0.05`; complete per-type curves,
shares, counts, relation kinds, and Shogi rows are in
`.generic_chess_flow/f42_component_ledger.json`.

| Ruleset/type | Raw | Mobility | Coverage | Reachability | Path efficiency |
|---|---:|---:|---:|---:|---:|
| Western P | 1.062289 | 0.949648 | 0.087500 | 0.014236 | 0.010904 |
| Western N | 4.815703 | 4.652813 | 0.100000 | 0.050000 | 0.012890 |
| Western B | 6.217622 | 6.074621 | 0.100000 | 0.024603 | 0.018398 |
| Western R | 9.087915 | 8.919915 | 0.100000 | 0.050000 | 0.018000 |
| Western Q | 15.163484 | 14.994536 | 0.100000 | 0.050000 | 0.018947 |
| Shogi P | 0.890705 | 0.787778 | 0.088889 | 0.002500 | 0.011538 |
| Shogi N | 1.321939 | 1.225432 | 0.077778 | 0.002654 | 0.016075 |
| Shogi S | 3.747505 | 3.588765 | 0.100000 | 0.050000 | 0.008740 |
| Shogi G | 4.709792 | 4.551605 | 0.100000 | 0.050000 | 0.008187 |
| Shogi B | 6.914414 | 6.771508 | 0.100000 | 0.024691 | 0.018215 |
| Shogi R | 9.985306 | 9.817449 | 0.100000 | 0.050000 | 0.017857 |
| Shogi TB | 10.088832 | 9.922619 | 0.100000 | 0.050000 | 0.016213 |
| Shogi TR | 12.786550 | 12.618437 | 0.100000 | 0.050000 | 0.018113 |

All relevant types also retain density/mobility curves, empty-board mobility,
reachable-pair ratio, shortest path, source/destination counts, ordinary and
conditional pattern counts, leap/ray composition, and quiet/capture relation
counts in the component ledger.

## Normalization and ablations

Normalization is non-primary: the inflation is already present in raw ratios,
and median/scale/round/clamp preserves the ordering. The full raw ratios are
N/P `4.533327`, B/P `5.853043`, R/P `8.555032`, Q/P `14.274351` before
normalization. The frozen one-at-a-time ablations retain existing weights and
are counterfactual only:

| Variant | N/P raw | B/P raw | R/P raw | Q/P raw | Shogi cosine |
|---|---:|---:|---:|---:|---:|
| Full | 4.533327 | 5.853043 | 8.555032 | 14.274351 | 0.999995 |
| Mobility only | 4.899511 | 6.396706 | 9.392860 | 15.789566 | 0.999925 |
| Full minus coverage | 4.837665 | 6.275844 | 9.220371 | 15.453074 | 0.999955 |
| Full minus reachability | 4.547197 | 5.909072 | 8.623530 | 14.420538 | 0.999987 |
| Full minus path efficiency | 4.568083 | 5.896249 | 8.626638 | 14.404375 | 0.999993 |
| Graph-global only | 1.446107 | 1.269534 | 1.491472 | 1.499883 | 0.903130 |
| Mobility + coverage | 4.582577 | 5.953460 | 8.696841 | 14.553883 | 0.999985 |
| Mobility + reachability | 4.879020 | 6.327754 | 9.306005 | 15.608235 | 0.999948 |
| Mobility + path efficiency | 4.857310 | 6.343243 | 9.304971 | 15.630047 | 0.999933 |

Every variant reports normalized ratios, ranking changes, per-piece reduced or
worsened inflation, and all three Shogi comparison metrics in
`.generic_chess_flow/f42_formula_ablation.json`. Removing graph-global terms
does not make the Western bands pass; it makes raw relative inflation worse.
Graph-global-only nearly removes the ratios but also materially degrades the
Shogi ordering, so it is not a candidate formula.

## Geometry controls and Pawn decomposition

The synthetic families were compiled through the existing RuleSet and semantic
compiler and measured with the same F41 analyzer. Multi-square ray versus
one-step leap increased raw score by `0.896870` (mobility factor `2.145725`);
long versus short ray increased it by `0.888770` (mobility factor `1.678155`);
multi-direction versus single-direction increased it by `0.229176`, including
reachability growth factor `2.0`. Quiet-only versus capture-only differed by
`-0.675938` in raw score under the frozen density endpoint model. Full case and
pair ledgers are in `.generic_chess_flow/f42_synthetic_geometry.json`.

For Western Pawn, ordinary semantic geometry has 3 patterns and 3 conditional
patterns excluded from ordinary capability; target relations are 4 quiet and
2 capture patterns. It has 56 candidate destinations per owner, reachable-pair
ratio `0.2847222222`, average shortest path `3.5853658537`, and path efficiency
`0.2180851064`. The density-weighted mobility is `0.9496484375`; removing the
endpoint factor would yield `2.40625`, showing that quiet/capture endpoint
semantics materially suppress the density term without any pawn-specific
branch. The largest weighted gap from Pawn to each Western N/B/R/Q is mobility,
with differences `3.703164`, `5.124973`, `7.970266`, and `14.044888`
respectively. Directionality, endpoint semantics, conditional exclusion,
source coverage, and graph terms are separately recorded in
`.generic_chess_flow/f42_pawn_suppression.json`.

The same four mechanisms are present in Standard Shogi, whose complete positive
control remains accepted. Shogi's broader and more varied movement population
does not exhibit the same compression relative to its Pawn anchor; a diagnosis
that breaks the Shogi cosine/order/hand gates would therefore be insufficient.
The cross-rule ledger is `.generic_chess_flow/f42_shogi_cross_rule.json`.

## Scope and boundary

The diagnosis did not use AlphaSho, search, self-play, TDLeaf, R37, coefficient
fitting, human-value regression, a second compiler, or production evaluator
changes. Focused deterministic F42 tests pass. The accepted F41 full regression
remains the governing regression evidence: candidate `1288` collected, `1285`
passed, `1` retained F24F failure, `0` errors, `2` skipped; no candidate-only
failure. F42 does not authorize F43 execution or promotion.

