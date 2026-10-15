# Historical reference path-key correction

The two actual paths are two passes then a four-king-move return cycle, versus
the king cycle then two passes. Same board, ply6 and repetition counts; different
last-action history. With a real three-pass draw rule, the next pass is ongoing
on the first path and action_class_draw on the second. Before correction the
historical reference's custom TT keys were equal. Core RuntimeSearchKey already
keeps these states distinct; Core is not changed. Full pre-fix source and actual
counterexample are retained here. This demonstrates a key-contract collision,
not a claim that a stored corpus's final WDL was observed corrupted.

Corrected reference retains ordered exact identity, actor, action_signature and
check evidence for continuous-check and compiled consecutive/automatic/repeated-
cycle path rules. Plain board/repetition/maxply reference key path is retained.
Tests bind the actual different successors and actual runtime push/pop restore.
Both known direct F23V/R1 callers' six compiled rule families have no such path
rules and draw repetition policy, so their reference key path remains unchanged.
No frozen labels were read/recomputed, no corpus or oldcap was reopened, and no
claim is made about current PRIMARY code. This is a scoped auxiliary reference
fix, not a new production TT design or proof of complete generic-domain coverage.
