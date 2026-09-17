# F104 cheap linear ordering distillation

F104 evaluated the one permitted `A_CANONICAL_WESTERN_CHESS` cheap-ordering
profile against the frozen F61R4 full nonlinear teacher. The parent was
`55249ef226ce60e51da8b6172881ea331757de0c72dbf918e48d84779dea1d5e`, the
teacher ordering checkpoint was
`68136a6ea36fc9ab764bc7164e1fdb58c7cfbead718500dc9f51c0feedf0649f`, and the
reconstructed teacher model SHA was
`855537bd5f473c557e22eba7b2fccd51142d5572599e4075d93dd127c2942950`.

The fit consumed exactly the cached 24 roots and 161 action rows from
F61R4. It used board-type counts, hand-type counts, the three dynamic
features, and owner/type 3x3 spatial occupancy with zero-sum spatial rows;
root-centered ridge fitting used alpha `1e-3`, no bias, and seed `59012`.
The resulting ephemeral candidate checkpoint was
`9eb5e8e4184bea73125de1079995338ee063fcbf5e08bd95bc5b7b1634735488`.

All correctness gates passed: compact nonlinear and localized control were
empty, the parent-leaf fixed-node search was identical with ordering enabled,
and parent/candidate Python-to-Native quantized score parity was exact across
all 161 rows. The cost comparison also passed: cheap/full ordering-score wall
ratio was `0.0728116784` (0.1224948 s vs 1.6823510 s across 1,000 repetitions
of the same 161 states).

The offline strength gates failed. Cheap-vs-teacher top-action agreement was
`9/24 = 0.375`, below parent-vs-teacher `14/24 = 0.5833333`; cheap-vs-q20
agreement was `9/24 = 0.375`, below parent-vs-q20 `11/24 = 0.4583333`.
Therefore the required classification is
`CHEAP_LINEAR_ORDERING_DISTILLATION_INSUFFICIENT`. The work order requires
stopping before Arena2, so no new self-play, teacher search, or Arena Heavy
run was started and no candidate is eligible for promotion.
