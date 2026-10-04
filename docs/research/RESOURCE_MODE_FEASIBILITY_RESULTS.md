# Resource-mode root feasibility results

2026-10-04. Full-resource construction and exact origin/tag guards pass5 focused
tests. Six root observations qualify feasibility only, not a coefficient law.
The protocol was frozen before observations; old sampled/scored boards unused.

| Game | Refined mode | Corrected admission attempt | Complete choices |
| --- | --- | ---: | ---: |
| Chess | board/P/P |13|44|
| Chess | board/P/Q |9|68|
| Chess | board/Q/Q |1|48|
| Shogi | board/P/P |5|51|
| Shogi | board/P/TP |2|54|
| Shogi | hand/P |5|54|

All32 Chess /40 Shogi physical base resources remain on board or in hands.
Native Q and Pawn-origin Q remain distinct. Every accepted root is synthetic
ply0 with declared reset history/rights, not a reachable-game sample. No full
mode support, conditional population mean or positive service is inferred.

## Invalid first guard and controlled correction

Original raw `data/resource_mode_feasibility_20261004.json` SHA256
d7b18b86386b99fde59fd1da383fdad5a6d3b7b0656997d2d9da7a916438f72f
preserves Chess128/128 rejected by an invalid dead-board predicate. Western
Pawn has no movement atoms; semantic action patterns supply its geometry.
Other Western pieces have atoms. Empty Pawn atom mobility is not inability
to act. Initial legal Chess exposes the old predicate as invalid independently
of any empirical reward or favourable root. Terminal Pawn ranks stay rejected.

`RESOURCE_MODE_FEASIBILITY_CORRECTION.md` freezes that specific guard repair
before corrected replay. The three SAME Chess seed streams/allocations are
replayed, not extended. Original Shogi rows are reused unchanged. New file
`data/resource_mode_correction_20261004.json` pins both original ledger/raw
and correction inputs. The128 old invalid examinations remain visible; they
are not128 additional independent context draws. Corrected Chess first
admissions use23 proposals total, Shogi12. This is not an acceptance-rate study.

Complete choices total319, including original Shogi159 and corrected Chess160.
ZERO public transitions, coefficient samples, goal labels or holdout reads.
Original0.157s + correction0.063s = about0.220s including compilation. Fixed
15s/5000 total enumeration limits,128/root and128 distinct proposals/game remain
unexceeded. Neither truncation nor root resampling after admission occurred.

## Consequences for H2

The reference is feasible on these six observations and preserves resources;
this removes one construction obstacle. It does not prove four-ply trace cost,
complete promoted-type reference support or refreshed-context fidelity. Chess
P/P can transition to P/B,N,R,Q; only Q is represented here. Missing reference
modes cannot be assigned zero future reward. Shogi owned-tag mode transitions
are direction-constrained: an enemy capture ends fixed ownership, even if the
same physical token later appears in enemy hand. Own hand is an initial mode,
not a recurrent destination following enemy capture. Actual continuation must
retain victims, histories and tag probability; reference refresh is explicitly
approximate. Freeze a separate finite path/closure question before observation.

An origin-refined service vector also needs a compatible feature map. Existing
current-type material counts would implicitly mix native/promoted origins;
neither a hidden mixture nor a hand premium is licensed by this feasibility pass.
