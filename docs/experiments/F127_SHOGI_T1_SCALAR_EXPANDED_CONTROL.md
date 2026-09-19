# F127 Expanded Standard Shogi Direct Control

## Scope and decision

This experiment implements
`GENERICCHESS_F127_SHOGI_T1_SCALAR_COMPRESSION_EXPANDED_CONTROL` from baseline
sandbox commit `3ddc285af219ed2a3bb7c3bb3f4309be0c21d86b`.
It is Standard Shogi only and excludes Western Chess, depth-2 transfer,
self-play, MCTS, Arena, generated rulesets, and promotion.

The final classification is:

`F127_EXPANDED_SUBSET_DIRECT_CONTROL_INSUFFICIENT`

The expanded matched-ridge scalar control still misses the preregistered
holdout nRMSE threshold. Per the work order, the run stopped before T1 label
generation and search-compressed fitting.

## Reproducibility

- Oracle SHA256: `dda316e263a8f6e5a12678199e87cbedea7e4d40358d3087e8c78ddb3894a316`
- Full ordered F122 corpus identity SHA256:
  `a1cb1bcf2d461c3bddc4f87928ed4d6260673de268356eec5741b9b534d4aa8b`
- Corpus seed: `1220201`
- Selection: `floor(j * original_split_count / selected_split_count)`
- Selected counts: train `2048`, dev `256`, holdout `256`
- Selected identity SHA256:
  - train: `c16db7cc19375820ca9a9866493922bf7a0d74eff64a8f909b225e9936f205fc`
  - dev: `91929864cab22ba1fc065f9acdc49855751a9761ebd28b9cda76202fe01e6e63`
  - holdout: `0173ba68eed4c779322214b3ef6c819726cb5476703214d00e4d8255a7b580b3`

The valid bounded Heavy run completed as `f127-shogi-expanded-control-v1` in
778.7433 seconds. The ignored raw result artifact SHA256 is
`413B498C7C5C54E137DBCC33FFDE47D77741BDF65D22DAC303719DBCD26E656B`.

## Eligibility staging

Eligibility is now separated from T1 generation. The production eligibility
stage creates children exactly once and inspects only child terminal status,
root declaration availability, and immediate-child declaration availability.
It does not call `basis.vector`, `basis.oracle`, `_terminal_value`, `_t1`, or
`_t1_from_children`.

The retained-state exclusion counts were:

| split | selected | terminal child | root declaration | child declaration | retained |
|---|---:|---:|---:|---:|---:|
| train | 2048 | 53 | 0 | 0 | 1995 |
| dev | 256 | 4 | 0 | 0 | 252 |
| holdout | 256 | 2 | 0 | 0 | 254 |
| total | 2560 | 59 | 0 | 0 | 2501 |

A 64-state deterministic Standard Shogi regression compares the new
eligibility flags with the prior `_teacher_row()` exclusion formulation; the
flags match exactly.

## Direct-control result

The tightened Jacobi-PCG solve used the unchanged F124 objective, tolerance
`1e-12`, and maximum iterations equal to eight times the parameter dimension.
All numerical equivalence checks passed:

- finite PCG parameters: pass
- relative residual: `8.557654090125355e-13`
- objective excess versus matched ridge: `3.1763735522036263e-22`
- holdout PCG-vs-ridge normalized difference: `2.248315387550694e-10`

The scalar gates passed for R2 and Pearson but failed for normalized RMSE in
both PCG and matched ridge.

| model | holdout RMSE | normalized RMSE | R2 | Pearson |
|---|---:|---:|---:|---:|
| PCG | 222.54533878699806 | 0.05158006311678104 | 0.9973394970888689 | 0.9986711427845183 |
| matched ridge | 222.54533883442718 | 0.05158006312777384 | 0.9973394970877348 | 0.9986711427840449 |

The expanded training support improved normalized RMSE from F126's `0.0537423`
to `0.0515801`, but it did not reach the fixed `0.05` gate. Because matched
ridge itself failed, this is a direct-control insufficiency result rather than
a PCG numerical failure.

No T1-label stage, search-compressed fit, scalar search-information diagnostic,
depth-2 transfer, self-play, or Arena run was authorized or executed.

The focused regression suite passes 7 tests, including the new 64-state
eligibility comparison; Python bytecode compilation also passes.
