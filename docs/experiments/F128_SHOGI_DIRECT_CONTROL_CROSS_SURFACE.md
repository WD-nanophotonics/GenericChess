# F128 Standard Shogi Direct-Control Cross-Surface Diagnosis

## Scope and classification

F128 uses baseline sandbox commit `41277d6001b2f546cf5591f02cb29a108b241647`.
It is Standard Shogi only. No T1 labels, depth-2 search, self-play, MCTS,
Arena, generated rulesets, or production learning paths were used.

The classification is:

`F125_ELIGIBILITY_CONDITIONING_SHIFTS_DIRECT_CONTROL_GATE`

The historical full F122 control reproduces exactly, while the full
eligibility-conditioned population exceeds the historical absolute `0.05`
holdout nRMSE gate. This attributes the binary gate miss to population
conditioning, not to the F127 subset alone.

## Frozen corpus and eligibility

- Full corpus: 4,500 ordered states
- Full corpus identity SHA256:
  `a1cb1bcf2d461c3bddc4f87928ed4d6260673de268356eec5741b9b534d4aa8b`
- Oracle SHA256:
  `dda316e263a8f6e5a12678199e87cbedea7e4d40358d3087e8c78ddb3894a316`
- Corpus seed: `1220201`
- Valid Heavy runtime: 1329.5779 seconds
- Ignored raw result SHA256:
  `62DD0FC02829C9188CD51E29F8D5AB7DB104486414ED2067E770D6EBD96327CC`

Eligibility was screened over all original F122 states before feature
materialization. Only terminal-child status, root declaration availability,
and immediate-child declaration availability were inspected.

| split | total | terminal-child excluded | root declaration | child declaration | retained |
|---|---:|---:|---:|---:|---:|
| train | 3000 | 77 | 0 | 0 | 2923 |
| dev | 750 | 13 | 0 | 0 | 737 |
| holdout | 750 | 5 | 0 | 0 | 745 |

Retained identity SHA256s:

- train: `74f9778dff9a2a5c08a6623d5452cdf2d15971cc20eab0c3e12a9c5d01d0a15b`
- dev: `5c9d3acbc6adbd366c8c2b3739fe80b322e67a83e13b3eb1c1153871d70f0448`
- holdout: `4238175784283f3338294290bb70b1330930a427a213f1a56223471b44d1d456`

F127 selected identity SHAs were reproduced exactly, and the selected retained
SHAs were also persisted in the raw result.

## Reproduction controls

Surface A, the original F122 full model, reproduces the F124 matched-ridge
holdout nRMSE exactly:

- expected and observed nRMSE: `0.04928567033125049`
- RMSE: `211.20558564541074`
- R2: `0.9975709226999993`
- Pearson: `0.998823430253524`

Surface C, the F127 eligibility-retained subset, also reproduces exactly:

- expected and observed nRMSE: `0.05158006312777384`
- RMSE: `222.54533883442718`
- R2: `0.9973394970877348`
- Pearson: `0.9986711427840449`

## Cross-evaluation matrix

Values below are matched-ridge metrics; nRMSE is normalized by each evaluation
surface's oracle standard deviation.

| model | holdout surface | RMSE | nRMSE | R2 | Pearson |
|---|---|---:|---:|---:|---:|
| Original F122 | full eligible | 210.8122 | 0.0493294 | 0.9975666 | 0.9988183 |
| Original F122 | F127 selected eligible | 210.2558 | 0.0487317 | 0.9976252 | 0.9988449 |
| Full eligible | full eligible | 216.4690 | 0.0506531 | 0.9974343 | 0.9987629 |
| Full eligible | F127 selected eligible | 215.8907 | 0.0500377 | 0.9974962 | 0.9987899 |
| F127 subset | full eligible | 222.6792 | 0.0521062 | 0.9972849 | 0.9986434 |
| F127 subset | F127 selected eligible | 222.5453 | 0.0515801 | 0.9973395 | 0.9986711 |

The decomposition is:

- holdout-surface effect: `-0.00061535` nRMSE, `-0.5782` oracle units
- training-subset effect: `+0.00154236` nRMSE, `+6.6546` oracle units

The full eligible model itself is above `0.05` on the complete eligible
holdout, so the primary attribution is eligibility conditioning. The subset
generalization penalty is classified as
`F127_SUBSET_GENERALIZATION_PENALTY_SMALL` because it is below `0.01`.

## Design and holdout diagnostics

| training surface | retained rows | active features | numerical rank | nullity | retained-spectrum condition |
|---|---:|---:|---:|---:|---:|
| full eligible | 2923 | 663 | 651 | 13 | 455.9660 |
| F127 subset | 1995 | 657 | 638 | 20 | 525.1657 |

The subset has 429 features constant in the subset but variable in the full
eligible training surface. Their aggregate oracle RMS contribution on the
F127 holdout is `0.2438094` oracle units (maximum absolute aggregate
contribution `0.8433333`).

Using the fixed full eligible holdout, 64 deterministic cyclic pseudo-subsets
of 254 indices were evaluated with
`((offset + floor(j*N/K)) mod N)`, for offsets 0 through 63. The full eligible
model's subset nRMSE distribution had mean `0.0507046`, standard deviation
`0.0012448`, min `0.0483432`, median `0.0502855`, max `0.0536071`, p10
`0.0492568`, and p90 `0.0526776`. The fraction above `0.05` was `0.671875`.
The actual F127 selected holdout was at the `35.9375` percentile, so it is not
an unusually difficult holdout surface within this fixed population.

## Dormant gate correction

The dormant T1 representation gate now uses a dedicated
`_search_representation_gate()` with thresholds nRMSE `<= 0.15`, R2 `>= 0.95`,
and Pearson `>= 0.975`. A regression test confirms that synthetic metrics
nRMSE `0.10`, R2 `0.97`, Pearson `0.98` fail the direct-control gate but pass
the search-representation gate. F128 itself generated no T1 labels.

The first bounded execution stopped on an implementation-only distinction
between selected and selected-retained identity SHA bookkeeping; the same
bounded work order was rerun after correction and produced the valid result
above.
