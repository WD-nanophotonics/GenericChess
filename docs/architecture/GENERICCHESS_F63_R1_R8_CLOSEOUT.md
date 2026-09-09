# GenericChess F63 R1 R8 Resource Calibration Closeout

- Work order: `GENERICCHESS-F63-R1-R8-COMMON4-RESOURCE-CALIBRATION`
- Parent sandbox SHA: `7531f1f250b17cadc0e3643319c296f08453db52`
- Scope: read-only calibration of the existing Standard Shogi Arena evidence.
- New games, Heavy, compute approval, rerun, teacher work, and selected-8/32 work: **not performed**.

## Cohort and provenance

The comparable cohort contains 129 completed games configured with
`nodes_per_move=2000` and no 20k child-search budget:

- F61 preserved Arena progress: 104 games from D0 4/8/32-pair stages and the
  two preserved 4-pair development variants. These pair-v1 records preserve
  game length but do not contain per-search node/time telemetry.
- F62 preserved Arena progress: 24 games, comprising 8 games in
  `arena-4-seed-630301` and 16 games in `arena-8-seed-630302`, with native
  per-search telemetry.
- F63 R6 preserved candidate game: 1 completed game in
  `candidate-59011-common-4-seed-630403`, with native per-search telemetry.

F63 teacher records were excluded from the comparable cohort because their
manifest declares `child_nodes_per_move=20000`; they are diagnostic evidence,
not 2k-node Arena evidence. The F63 R6 game-v1 file was not rewritten. Its
SHA-256 is
`e205dcfab1b4eff012ac496919ae80b4ab93b882e310fcf59c52f42b504c92f2` and its
manifest identity SHA-256 is
`ec802b9492a36d86c9c4be4644e652afb136e7754c0dfc1dc919b6b45a15f1bf`.

The result artifact remains resumable and unresolved:
`COMMON_INCOMPLETE_RESUMABLE`, with one completed game and zero completed
pairs. Its SHA-256 at calibration time is
`8667654423feac2449bc506e35bce7ce338d4f6167b2e5d915cf95e513420d92`.

## Historical distributions

All statistics below are per completed game. Quantiles use linear
interpolation. A cap comparison treats equality with the cap as censored.

| Measure | N | Min | Median | P90 | P95 | Max | Censored by current cap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Plies | 129 | 35 | 167 | 422 | 494 | 498 | 111/129 = 86.05% at 80 |
| Total searched nodes | 25 | — | 290,000 | 886,400 | 975,200 | 990,120 | 20/25 = 80.00% at 200,000 |
| Search elapsed seconds | 25 | — | 1,437.337 | 7,395.544 | 8,415.968 | 9,195.600 | 17/25 = 68.00% at 900 |

The 25-game telemetry subset is the 24 F62 games plus the preserved F63 R6
game. Its effective per-game NPS, computed as total nodes divided by total
native elapsed seconds, is median 182.282, P90 315.481, and max 402.217.
The elapsed values are a trustworthy search-time proxy for occupied lane time;
they are not presented as a host-wide CPU profiler measurement.

For the directly comparable F62 4-pair Arena, the 8 games sum to 19,459.827
native elapsed seconds. With four effective lanes, the ideal balanced lower
bound is 4,864.957 seconds (81.1 minutes) for one candidate stage, already
above the current 3,600-second common-4 stage cap. The 8-pair reference sums
to 55,726.143 seconds over 16 games; it is supporting long-tail evidence, not
a proposed F63 rerun.

## Unchanged common-4 cost estimate

The requested design is three candidates × four color-swapped pairs × two
games, at 2k nodes per move, with four effective lanes (24 games total).
Historical evidence gives a broad, explicitly non-precise range:

- Median-game load model: about 9.6 occupied-lane hours and 2.4 ideal wall
  hours.
- F62 4-pair stage load model: about 16.2 occupied-lane hours and 4.1 ideal
  wall hours for the three serial candidate stages.
- If every game were P90-like, the arithmetic envelope would be about 49.3
  occupied-lane hours and 12.3 ideal wall hours; this is a tail warning, not a
  forecast.

The central historical models therefore do not fit the old 180-minute wall or
12 CPU-hour checkpoint simultaneously. Lane-hours are used as the CPU-hours
proxy because the available evidence is per-search native elapsed telemetry;
the report does not claim more precision than that evidence supports.

## Cap conclusion

The observed maxima suggest finite per-game calibration values of 512 plies,
1,000,000 searched nodes, and 10,000 seconds. These are evidence-derived
candidate values: they clear the observed maxima with small operational
headroom, while 80/200,000/900 demonstrably censor the cohort. They were **not
implemented** in R8 because raising the caps without changing the cost
checkpoint would silently expand the approved computation. The current common-4
stage wall cap is also below the directly observed four-lane F62 4-pair stage
lower bound.

## Decision required before rerun

- **A — retain 3×4 pairs×2k:** preserve the statistical design, but obtain a
  fresh exact-SHA scientific and Supervisor approval with an expanded wall/CPU
  checkpoint and calibrated caps.
- **B — reduce common triage pairs:** use two pairs per candidate (12 games),
  preserving 2k equal parent/child search. This is the smallest design change
  that can plausibly fit the old checkpoint; Chat must decide whether the
  reduced common-stage evidence is acceptable.
- **C — reduce common-stage search:** preserve equal parent/child budgets while
  reducing the common-stage search budget. No numeric reduction is proposed or
  implemented without Chat scientific direction.

R8 is therefore a calibration-only closeout. No cap correction or new compute
approval is issued by this report. The next action is a fresh current-SHA plan
for A, B, or C after the tradeoff decision.
