# GenericChess F85A-R5 Three-Lane Authority Correction

F85A-R5 applies the explicit Supervisor correction to the R4 decision. The R3
bounded diagnostic is now accepted as sufficient decision evidence for runtime
geometry: two lanes took 11.226 seconds, three lanes 7.130 seconds, with total
worker CPU effectively unchanged (31.828 versus 31.906 seconds) and only a
35.45 MiB RSS increase. Four lanes improved over three by only 0.35% while
using more RSS, so three lanes is the selected geometry.

No lane experiment is rerun. No teacher acquisition, Heavy run, C2 fit, Arena,
root resampling, or production semantic change is performed in R5.

## Unified three-lane authority

The tracked precompute manifest's execution geometry is updated consistently:

- `execution_contract.max_concurrent_roots = 3`;
- manifest derived SHA `d6b75df2e9d179de958347a7c18bebdee3a0556f83e0001a4fa41c331cd4a489`;
- 36 train roots, 12/12/12 strata, dev/resource roots zero;
- total declared node ceiling `15,426,000`.

The runtime validator and batch scheduler both require exactly three lanes and
use the validated value for batch width. Two- and four-lane plans are rejected
before any teacher runner starts. Atomic per-root progress, terminal
fail-closed behavior, provenance binding, and 36/36 sealing requirements are
unchanged.

## Exact large-plan geometry

The replacement tuple is three lanes on 16 logical CPUs, one stage, 720-second
per-root cap, 70-minute expected wall, 60–80-minute planning range, 180-minute
hard wall, 8.5 expected CPU-hours, 15 hard CPU-hours, and zero effective
games/pairs/plies. This tuple is unapproved and acquisition remains prohibited
until Chat scientific approval and registered Supervisor approval bind the same
plan and envelope digests.

Classification: `C2_TRAIN_TEACHER_ACQUISITION_HARNESS_READY_FOR_LARGE_APPROVAL`.
