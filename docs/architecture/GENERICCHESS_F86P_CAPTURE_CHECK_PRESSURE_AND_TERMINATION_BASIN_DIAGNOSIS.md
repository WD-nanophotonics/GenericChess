# GenericChess F86P-R1 capture/check pressure and termination-basin diagnosis

Status: corrected deterministic diagnostic replay complete. F86P-R1 corrects
the child-check side-to-move semantics and the retained geometry arithmetic
from the prior F86P checkpoint. It replays only the 12 frozen F86O
trajectories; it creates zero new games and does not alter any F86O ruleset,
tape, action ordering, or result artifact. The direct successor contract test
proves that the diagnostic helper agrees with both the core check predicate and
the move-history `gave_check` flag.

The implementation baseline for this correction is F86P commit
`d089535fccd67e939b8afa225e8fc3e982c28816`.

## Authority and replay equality

The F86O manifest authority is
`artifacts/f86o_common_tape_triarm_dynamic_smoke/manifest.json`, Git blob
`1d16cf69a7ce5f7347352162dcbd351485e8c5af`. The six frozen ruleset
fingerprints are:

| Arm | V4-3 | V5-3 |
| --- | --- | --- |
| L | `ea993a6147595b1ce740cc91ad426a96395edcb6de479c95c23ecc88800a0e17` | `1a256a4fcc763cb6f4e5ca1037a77b72885d4e85a4d5e46ccf88c69f552b266d` |
| F | `8ca58376a52e539c7c8519e902b8dd9e6991b002586d36d846a7a864fffea05d` | `29390db6050d1ba482a393f7466608a6f19d0df9e6d4f7c3bd3a556f2d194fff` |
| N | `856a810d3a21eec779f9ba8300ce602cd24d3e8850ba895e39579603fd4ff3e2` | `e8528688a64bce3f39231d9e4f38d5d200ade57c6f517ae33ce9b71b9f75ebe5` |

The four frozen tapes remain V4-3 A/B `8624301/8624302` and V5-3 A/B
`8625301/8625302`, algorithm
`python_random_mt19937_random_floor_index_v1`, length 32. Every one of the
following F86O action-sequence hashes was reproduced exactly:

| Arm | Sample | Seats | Action-sequence SHA-256 |
| --- | --- | --- | --- |
| L | V4-3 | A/B | `bf498955a8b5d4ec7ebd7ad31b52ba25f3ca74de8be6e85d836f14d9a6527836` |
| L | V4-3 | B/A | `464e7585eb8c3574248bbcaff08e3540f5eb2152ba8ef432834576882bfb517d` |
| F | V4-3 | A/B | `1e47448a63739fd9faa4e0927fd5ed0304c51dca455e66ee1c114c107cc8e2e3` |
| F | V4-3 | B/A | `542e4a2f829eda20ec6be8147c965f2b4bd10dd8e35a6d0af4a65f2392fab470` |
| N | V4-3 | A/B | `0b91b9ce68e558642feae465689b6b9c04d9673374dc02ebad62e21c2cc63dd3` |
| N | V4-3 | B/A | `ce640e937e1a763ddbfd6db327519c499c4ddf7db36cfbd046cf9881b728d726` |
| L | V5-3 | A/B | `135fd8833a52f98fc4c46ab86aa28b6aa866ac5b8203bae1783140e0fad4204b` |
| L | V5-3 | B/A | `dee88b4b9510338a96ed389e59b2f8ae10b6e02e89bd2adb6ffe1887207e3db5` |
| F | V5-3 | A/B | `fe0b6df18a7605b1f16c885f9fea89d6b8e91462f808dd3f006edb3a568b76dd` |
| F | V5-3 | B/A | `93af93f69aa61619abb2a08b67119e086776082f0dcd3ae65aba0f3cb8d6419a` |
| N | V5-3 | A/B | `37a7266392338d07252b3d0f51a79dd8cd0531c36ae3c99110270aabba8927a8` |
| N | V5-3 | B/A | `10c1dd51ebb3470dae7fae3e07369fcc52a030e17bf9c6fedb5763af54bf82ee` |

The final-position digests also matched all 12 F86O records. The replay uses
one-ply `legal_successors` only; it does not search deeper or enumerate a
state-space tree.

## One-ply interaction metrics

The total was 1,620 one-ply child probes against the fail-closed cap of 4,096;
truncation was false. The table reports opportunity plies / total plies,
chosen captures, chosen checks, mate-in-one opportunities, material reduction
for the two seat-swapped games, and first capture plies.

| Arm | Sample | Capture opportunity fraction | Chosen captures | Check opportunity fraction | Chosen checks | Mate-one opportunities | Material reduction | First capture plies |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| L | V4-3 | 12/38 | 6 | 0/38 | 0 | 0 | 4, 2 | 4, 3 |
| L | V5-3 | 9/60 | 3 | 7/60 | 1 | 0 | 1, 2 | 5, 7 |
| F | V4-3 | 21/64 | 8 | 7/64 | 1 | 0 | 5, 3 | 1, 7 |
| F | V5-3 | 43/64 | 5 | 25/64 | 4 | 0 | 2, 3 | 7, 16 |
| N | V4-3 | 26/64 | 6 | 1/64 | 0 | 0 | 2, 4 | 6, 1 |
| N | V5-3 | 23/64 | 7 | 12/64 | 2 | 0 | 4, 3 | 7, 9 |

ARM-N therefore had frequent legal capture opportunities (49/128 plies),
selected 13 captures, and reduced material in all four trajectories. Corrected
child semantics find 13 checking-opportunity plies and 2 chosen checks, but no
mate-in-one opportunities. Per-ply legal action counts, start-in-check flags,
capture and check availability, cumulative captures, ordinary material
counts, and opponent-anchor pressure trajectories are retained in
`summary.json` for all three arms. A mate-in-one child is asserted to be a
checking child during instrumentation.

## Static-witness distance surrogate

F86N-R1’s compact accepted result retained joint-witness counts and the
backbone witness, but not the target-square rows. Because re-enumerating its
mate census is forbidden, F86P-R1 retains the already persisted F86H
`ORTHO4_CURRENT` witness geometry only as a clearly labeled, non-authority
cross-ruleset reference. It does not participate in scientific routing, does
not claim those rows were revalidated under ARM-N, and does not call the
metric a legal mate distance. The metric is the empty-board minimum assignment
distance for same-type ordinary pieces plus the two empty-board Anchor
distances, ignoring occupancy, check, and capture. Equal piece counts carry no
implicit penalty, and a zero Anchor distance remains zero.

| ARM-N sample / seats | Start | Minimum | Ply of minimum | Final |
| --- | ---: | ---: | ---: | ---: |
| V4-3 A/B | 4 | 2 | 3 | 21 |
| V4-3 B/A | 4 | 4 | 1 | 53 |
| V5-3 A/B | 1 | 0 | 4 | 55 |
| V5-3 B/A | 1 | 0 | 10 | 54 |

The trajectories move closer to the persisted target geometry at some points,
but no trajectory supplies a mate-in-one opportunity and none terminates. The
corrected route is therefore
`CHECK_PRESSURE_PRESENT_BUT_MATE_BASIN_UNREACHED`: material/capture
interaction and legal checking pressure exist, with two checking moves chosen,
but the frozen trajectories never reach a mate basin. This is a diagnostic
route, not a generator threshold.

## Scope and verification

Replayed trajectories: 12. New real games: 0. Search depth greater than one:
0. BFS: 0. AlphaBeta: 0. Training: 0. Teacher: 0. F85: 0. Heavy: 0.
Static census rerun: 0. Rulesets, movement samplers, seeds, tapes, and the
default generator were not changed. The workflow policy files were not
changed.

Exact verification:

```text
.venv\Scripts\python.exe -m pytest tests/test_f86p_capture_check_pressure_diagnosis.py
6 passed
```

The durable compact result is
`artifacts/f86p_capture_check_pressure_diagnosis/summary.json`. Full action
dumps are not tracked.
