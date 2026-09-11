# GenericChess F85A Chat Authority Reconciliation

This report requests same-Chat reconciliation of a current authority conflict.
It is not an acquisition authorization, lane experiment, C2 fit, Arena run, or
production change.

## Conflict to resolve

The signed R6 Chat response accepted checkpoint
`49b4abcf6240dbef3ab15281e0328b9132ee6b1f` and froze the two-lane tuple. The
latest registered-Supervisor directive explicitly rejects that two-lane tuple,
requires the measured three-lane option to be reconsidered, and instructs the
worker to bring the conflict back to the same Chat rather than request two-lane
approval.

The worker has preserved the R6 repository authority and has not started
acquisition. Chat should decide the conflict directly: either accept a new
three-lane exact tuple under a new work order, or provide concrete independent
scientific/resource evidence that overturns the R3 observation. The manifest
and validator must not be treated as independent evidence when they are the
constraints under dispute.

## Evidence already available

The bounded R3 diagnostic used only the three frozen F84 resource roots and
smoke budgets, with deterministic signatures:

| Lanes | Wall | Worker CPU | Peak worker RSS |
| ---: | ---: | ---: | ---: |
| 2 | 11.226 s | 31.828 s | 205.84 MiB |
| 3 | 7.130 s | 31.906 s | 241.29 MiB |
| 4 | 7.105 s | 31.859 s | 256.96 MiB |

Three lanes improved wall time by 36.5% over two with essentially unchanged
CPU; four lanes added only 0.35% over three while using more RSS. The limits
are explicit: this was smoke-sized and did not establish full F59 teacher
workload scaling. No additional lane experiment is being run here.

## Roadmap note

The user also asked that a possible future shift toward smaller, randomly
generated game variants for benchmarking be considered in the roadmap when
Chat judges the timing appropriate. This report records that direction only;
it does not start or expand any benchmark work in the current F85 order.

Until Chat resolves the lane conflict in a new signed work order, acquisition
remains prohibited and the published R6 checkpoint remains unchanged.
