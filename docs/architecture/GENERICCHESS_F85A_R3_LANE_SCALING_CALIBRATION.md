# GenericChess F85A-R3 Lane Scaling Calibration

F85A-R3 is a bounded decision experiment requested after the two-lane F85 v3
tuple was withheld. It uses only the three already frozen F84 resource roots:
`reachable_random-r-00`, `c1_on_policy-r-00`, and `c1_pv_corridor-r-00`.
It performs no 36-root acquisition, no training-evidence sealing, no C2 fit, no
Arena/self-play, and no root resampling.

## Experimental contract

The single Heavy-protected diagnostic used the explicit envelope
`f85-lane-scaling-calibration-v1` (SHA-256
`36fda3b81fc0ddedcc664c9be805f5bb9936063b12e2fe76d2f955710817699e`). It
ran the same three roots sequentially at lane counts 2, 3, and 4, using F59
smoke budgets of 50/100/200 root nodes and three initial selected actions. It
recorded stage wall time, summed worker process CPU, aggregate worker RSS peak,
and a canonical result signature per root.

The run was executed from published sandbox checkpoint
`1fbc4183a0fae8c0804f23f41a7f271ff9042841`. Raw ignored evidence is retained
at `.generic_chess_flow/f85-lane-scaling-calibration/raw.json` with SHA-256
`da2994c71d4705885c4bfe910ce07ddcdea90e43bf94b2eaf0e8c5dde13c3619`.

## Results

| Root lanes | Stage wall (s) | Total worker CPU (s) | Peak worker RSS (MiB) | Relative wall | Deterministic signatures |
| ---: | ---: | ---: | ---: | ---: | :---: |
| 2 | 11.226 | 31.828 | 205.84 | 1.000x | yes |
| 3 | 7.130 | 31.906 | 241.29 | 1.574x | yes |
| 4 | 7.105 | 31.859 | 256.96 | 1.580x | yes |

All three lane counts produced identical per-root result signatures. Three lanes
reduced wall time by 36.5% versus two while leaving total CPU unchanged within
measurement noise. Four lanes added 6.5% RSS over three lanes while improving
wall time by only 0.35%, which is not a meaningful scaling gain in this probe.

## Decision and limits

The smoke observation favored three lanes on this narrow workload, but it does
not establish full teacher-acquisition memory scaling or authorize production
geometry. The F85 harness therefore remains at the previously calibrated
two-lane authority: the frozen manifest's original precompute contract bytes
and runtime validator both require two lanes, while three- and four-lane plans
are rejected before any teacher runner starts.

The resulting classification is
`C2_TRAIN_TEACHER_ACQUISITION_HARNESS_READY_FOR_LARGE_APPROVAL` remains bound
to the calibrated two-lane geometry. The smoke result is diagnostic history
only; teacher acquisition remains prohibited until the exact two-lane tuple
has separate Chat scientific and registered Supervisor approval.
