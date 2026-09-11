# GenericChess F86D monotone-mobility mechanism ablation

Status: bounded static diagnostic and counterfactual ablation complete. The
default generator was not changed. No Heavy job, ladder tournament, F85 work,
C2 fit, or admission-threshold work was run.

## Question and separation of evidence

F86C found a fixed eight-seed population with 16/16 stalemate outcomes. The
mechanism hypothesis was that the generated movement atoms are predominantly
forward-only, so empty-board mobility may form a monotone directed acyclic
graph with sinks and little reversibility. F86D tests that hypothesis in two
separate layers:

1. Static diagnostics inspect every square-to-square movement graph, for both
   owners, for all eight frozen F86C rulesets.
2. Minimal counterfactuals change only movement atoms, then run the scoped
   V4-3 and V5-3 smoke pairs and one bounded terminal-only probe per
   counterfactual ruleset.

The static layer is graph evidence; the game layer is a small causal probe.
Neither is a general admission threshold or a claim about all future seeds.

## Frozen population and static result

The exact F86C rulesets were loaded from
`artifacts/f86c_generator_viability/rulesets.json`; they were not regenerated.
The static artifact contains 32 rows: eight `LEGACY` rows and eight rows for
each of the three counterfactual profiles. Each row records per-type,
per-owner empty-board vertices and edges, average out degree, sink fraction,
largest and nontrivial SCC fractions, direct reversible-edge fraction,
far-edge sink fraction, atom direction flags, and the monotone-DAG flag.

Every legacy row has the same structural signature:

- no backward atom;
- forward-only atom fraction 1.0;
- ordinary direct reversibility 0.0;
- ordinary nontrivial SCC fraction 0.0;
- `monotone_mobility_dag: true`.

The full-anchor ablation removes anchor sinks and creates a strongly connected
anchor graph on each finite board. The bidirectional-ordinary ablation gives
ordinary movement a direct reverse counterpart and raises ordinary
reversibility to 1.0 in the affected graph rows. The combined ablation has
both effects. These are static consequences of the requested atom changes,
not learned-game observations.

## Exact counterfactual profiles and fingerprints

The exact serialized rulesets are retained in
`artifacts/f86d_mobility_ablation/counterfactual_rulesets.json`:

| sample | A full anchor | B bidirectional ordinary | C combined |
|---|---|---|---|
| V4-2 | `ce38d544d11c1299b76ce9ac3396a37467535948e731fb967a9c5437c82aefb8` | `5e3778fa7cf70d86d98dfd14ad22a538b13fa89978af462c24079bb7f8856c26` | `53ed0e0f40bf05303225cf885302a63c6a45c6847dc58b23c814145e186dd243` |
| V4-3 | `7511327e944c195de71de536f818e8a2028136d4b04123937596f4dce46bda62` | `62777de71c9cbed23a4ac8262696a1e606b2b95514e688bb814c7a577dcb681f` | `85bbac150c5a5bb6c70b8701aaf00d83de5f5b003f4bfbb7164b818346f12b8f` |
| V4-4 | `6cec8e2262f057b6fb0680afca833c7440c0221e03bc6d96d0b307310bbc8b11` | `5aeaf03c866f98d88a39c1503071efc918f73229a18115814df02ceb77333c2e` | `732c1130e921a29831ec878c8de6dddcb590345fa780c6156705a1df41d27f8c` |
| V4-5 | `abc1cec911f5607ae41078b595c5a8ab1df668943d4b26ab83c2d354dca51ddc` | `6eda33d023b13a5d31beca9e421e89dca1e79b2e9a71ee733c48f03c453cc193` | `2eb8af9e4d46004bf84788401a11bdba0674a5427a119d35cac44b5c1f7a87a3` |
| V5-2 | `38e2ef27aba3b25ad9b2e827c151696ed96778da1bcba3fe6a3c9d18b1b342cb` | `1d1f81c19194a56062d9c86b2de9a65ef5a6314fa9eb3e03f276646cb55f8f74` | `475d11bc5c7cf30f4db3d9269d85028428da669032d4918db75eae04c1ab909d` |
| V5-3 | `8d77e9671449b2d6952aa7c80c898d7e390eff0fa534ac8be6d55e7f055ec1d8` | `d4a9f63b77c7d9bde045f98c26c634c5c036c3d7854fa245a95132b4dba704e9` | `e85acd9690bb3a82243f97a1b55c0a662b8ded1b9db6b82f4d9f74eb53519254` |
| V5-4 | `d64316e6ba2c5b366be7dc5f10451481c18a7caaeaa123fedfc90e2cb06eb0da` | `b1f581da589d6c1d8b7f470fb692a57c4e40816e045ce43a73b717dce2625140` | `ebfc8d8d994312a5220f3851c160d6f3c014a7f7f6e57bc2a953a9b8b477c8a5` |
| V5-5 | `831656b5b92d7e2a21b3e543d3103818df7b72d7b8f8cb354d67ca323a33d78b` | `a0f1dea429ee476a9dbe6ec17777ebaf99f195a30f15bc1feff7b9eb5a3d2d37` | `6c7cc8698607bc953cd517bc7b9fd0878fb52f673706e15a8baec5289dd5cdfe` |

Profile definitions are exact:

- `A_FULL_ANCHOR`: legacy ordinary pieces; Anchor becomes the full eight
  neighboring LEAP offsets.
- `B_BIDIRECTIONAL_ORDINARY`: legacy Anchor; every ordinary LEAP/RAY receives
  its reverse atom when absent.
- `C_FULL_ANCHOR_PLUS_BIDIRECTIONAL`: A and B together.

## Bounded game evidence

Legacy is referenced directly from the four existing F86C games for V4-3 and
V5-3; it was not rerun. Each counterfactual received one A/B and one B/A
policy pair, max ply 32: six pairs and 12 new games total.

| profile | games | stalemates | checkmates | ongoing | stalemate fraction |
|---|---:|---:|---:|---:|---:|
| F86C legacy reference | 4 | 4 | 0 | 0 | 1.00 |
| A full anchor | 4 | 0 | 0 | 4 | 0.00 |
| B bidirectional ordinary | 4 | 1 | 1 | 2 | 0.25 |
| C combined | 4 | 1 | 0 | 3 | 0.25 |

The three counterfactual stale-fraction improvements versus the legacy
reference are respectively 1.00, 0.75, and 0.75. These observations are
bounded smoke evidence, not a statistical tournament.

There were six terminal-only tactical probes, depth at most 4 and at most 256
nodes each, for 1,536 actual nodes total. F85 actual compute remained 0.

## Routing

The bounded ablation routes to `ANCHOR_MOBILITY_PRIMARY_CAUSE`: full Anchor
mobility produced the largest qualifying stalemate improvement, while the
ordinary bidirectionality ablation did not exceed it. The result supports
inspecting Anchor mobility and generator placement/occupancy interactions
next; it does not authorize a default-generator rewrite or a claim that
ordinary reversibility is irrelevant.

## Durable evidence

- `artifacts/f86d_mobility_ablation/static_diagnostics.json`
- `artifacts/f86d_mobility_ablation/counterfactual_rulesets.json`
- `artifacts/f86d_mobility_ablation/results.json`
- `tests/test_f86d_mobility_ablation.py`
