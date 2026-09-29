# Exact DRAW/LOSS material-control witness in the frozen R5 corpus

**Unknown.** Does a material-only control profile causally change the exact
W/D/L quality of a bounded search choice on an already solved root with a
legal material-changing alternative? The earlier Chess mate and pawn-ablation
roots changed moves but every compared choice still won.

**Smallest direct observation.** Use two existing R5 DEVELOPMENT
capture/recapture roots, selected in sequence. The first has a root capture
labelled DRAW; after it gave no W/D/L separation, the second was selected
because its capture witness is labelled LOSS. Use the frozen R5 exact action
certificate, not a new solver run. On each root compare only two arbitrary
integer profiles, `K=0,R=4,D=1` and `K=0,R=1,D=4`, with the existing Python
material-only evaluator at depths 1 and 2. Disable quiescence, TT, and move
ordering; cap each search at 2,000 nodes and five seconds. These profiles are
controls, not proposed values or a coefficient sweep.

`scripts/audit_r5_capture_loss_material_control.py` checks the frozen R5
fixture SHA, DEVELOPMENT split, completed depth, selected-action membership
in the exact certificate, and the losing action's capture-to-hand transition.

| Root | Profile | Depth 1 exact label | Depth 2 exact label |
| --- | --- | --- | --- |
| `generic-f23n-legacy_capture_recapture-1` | `R=4,D=1` | DRAW | DRAW |
| same | `R=1,D=4` | DRAW | DRAW |
| `generic-f23n-legacy_capture_recapture-2` | `R=4,D=1` | LOSS | DRAW |
| same | `R=1,D=4` | LOSS | LOSS |

On root `-2`, the depth-2 `R=1,D=4` choice is the legal `R` move from
`(1,1)` to `(1,2)`: it captures an opposing `D`, adds one `D` to the mover's
hand, and is still ongoing immediately after the move. The frozen exact
certificate labels that action LOSS. The `R=4,D=1` depth-2 choice is a quiet
king move labelled DRAW. The search selections differ in actual terminal
quality under the same rules, budget, and fixed depth. Depth 1 selects LOSS
under both profiles, so the observation also depends on search horizon.

**One quiescence control.** On root `-2` only, retain both profiles and set
the Python qsearch limit to 4 (hard limit 8 in the shared helper). At depth 1
both still select LOSS, with five qnodes each. At depth 2 both select the
quiet king move labelled DRAW, with 103 and 106 qnodes respectively. Every
run completed its requested depth. Thus this tactical frontier expansion
removes the `D`-high decision error only at depth 2; it does not make either
material profile rule-derived or prove quiescence always prevents bad
captures. The contrast directly shows why validation must name both main
search depth and quiescence semantics.

**Boundary.** This is a targeted, synthetic 5×5 capture-to-hand root, not
Western Chess or Standard Shogi and not a representative context measure.
The R5 builder gives it `max_ply=6`; both selected records report `mixed`
max-ply dependence and use that cap as the authoritative game horizon.
DRAW/LOSS is therefore exact only under this declared finite RuleSet and
terminal contract. It is not a claim about an unbounded continuation.
The second root was inspected after the first control failed to separate
outcomes; it must not be counted as an unbiased success rate. Exact labels
validate the *choice* under each arbitrary profile but do not identify a
correct ratio, a game-independent construction, or a deployment distribution.
The R5 and R10 corpus coverage gates remain failed. Keep this root as a
bounded falsifier for a future frozen prior; do not fit its coefficients or
infer Chess/Shogi material values from it. Xiangqi material values remain
sealed.

**Verification (2026-09-29).** `.venv/Scripts/python.exe
scripts/audit_r5_capture_loss_material_control.py` returned
`R5_MATERIAL_CONTROL_WDL_SPLIT`; the frozen R5 contract tests in
`tests/test_f23n_preference_corpus_r5.py` passed all six cases. No exact
solver, self-play, Arena, or human-value table was used in this probe.
