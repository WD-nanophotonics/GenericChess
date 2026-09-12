# GenericChess F87A-R8 Western Terminal Witness Closeout

- Baseline: `8fbf24a475b8390b8a4d27a6dd489d4567bb7dd1`
- Scope: one bounded legal terminal witness from the built-in Western initial position.
- Witness: standard seven-ply Scholar's Mate, executed through the production semantic runtime.
- Compute: one seven-ply witness, no search sweep, no Arena, no training, no Heavy job.

## Result

The production semantic runtime accepted all seven canonical legal actions and
reached `checkmate` with winner `0` on ply 7. This is positive evidence that a
natural legal terminal state is reachable from the built-in Western initial
position through semantic actions.

This witness is deliberately not a dynamic viability pass. It does not replace
the R6 control evidence: all three bounded controls still reached their 128-ply
horizons without a terminal result. It therefore does not authorize training,
promotion, or a change to the Western `DEFER` qualification status.

## Evidence

- Manifest SHA-256: `f95ba98008ab690db5dddb4ac1a7b5a3374943ca107d368d805eb0aa2727673c`
- Results SHA-256: `817deec861888dccfbe27be064c16967f8d682a55bb6d7d9bfbce0a0d34f8f1`

R8 narrows the remaining blocker from terminal reachability in the semantic
runtime to reproducible terminal discovery under an authorized dynamic control.
