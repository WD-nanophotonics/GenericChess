# Partial mode-equivalence evidence and targeted interface correction

2026-10-04. Frozen first program SHA256
51495b04e3367a29d3a3db8f3e2663b20caf3b854bf33df78108f1da217b392f
completed BOTH Chess paired-control loops, then failed before ANY Shogi control
because SemanticTypeMetadata exposes no movement_atoms attribute. Exception
at line149 occurs after the Chess equality/reward/trace/capture assertions.
Shell tool wall time0.476s, exit1. No final numerical rows were persisted;
overall first run is INCOMPLETE. Preserve source and explicit failure evidence,
do not pretend it returned a successful raw report or rerun completed Chess.

Pure root enumeration recovery (no child transitions) gives27 choices per
owner. Completed first-program loops therefore performed2*(27+27)+4=112 public
transitions. All matched Chess child/current-state/short-history observations,
unit scores, tagged rewards and enemy-capture loss checks succeeded before
the reported interface error. Its exact numerical rows remain unavailable;
we do not fabricate them. Current geometry permits only QxRd6 as tagged
capture, giving1/27 analytically for either origin under uniform choices.

Targeted correction uses source RuleSet.piece_types to compare G/TP atoms BEFORE
transitions; compiled semantic metadata remains authoritative for execution.
Run only the four previously UNEXECUTED sparse Shogi captures, no Chess replay,
new seed or coefficient. Remaining16 of original128 transitions suffice;4 are
planned. Root recovery plus original public/binding passes and new4 roots are
bounded above by54+216+1024+1024=2318 enumerations<5000, using original root/reply
128 caps. Corrected clock cap8s, original/recovery shell time<0.73s, preserves
the original10-second overall budget conservatively. No material budget reset.

Save targeted Shogi raw report and link this prefix certificate/failure log.
Its completion does not turn missing original numerical rows into persisted
evidence or prove unrestricted Chess provenance equivalence. No retries after
this correction. It qualifies source-versus-compiled metadata handling and
the previously frozen custody question; no project rules changed.
