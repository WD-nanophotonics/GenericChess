# Prospective richer-root external reference preflight

Choose ONE new synthetic initial root, without consulting outcome labels:
7k/8/8/8/3p4/8/2P5/K7 w - - 0 1. The purpose is a small complete Pawn-risk
decision with distant Kings and no castling/EP at the initial state. This is
not a new natural-game sample or an extension of the exposed Lichess puzzle.
It is chosen structurally, not from service best-move order or previous labels.

Freeze geometric_half, linear_mixture and unit at scale100000, the existing
complete q1-root operator B and empty-hand V3 capture hint. Retain static
full ties as a control. All root actions and replies are required; no root
filtering. Whole128 public/runtime events,5000 returned/member entries,
128 author pushes/5000 author entries,128 aggregate qnodes,15sec local CPU.
Preflight author legality/check/terminal status and conservative source/runtime
event bound before Core materialization or external outcome acquisition.
Any failure closes the trial, without replacement/deepening/budget increase.

Independent outcome contract: after local policies and complete tree have been
persisted and hashed, make at most ONE unauthenticated HTTPS GET to the public
Lichess standard tablebase endpoint, submitting only this synthetic FEN.
30sec transport timeout,256KiB response cap,no automatic retry. Preserve exact
response bytes, requested URL,FEN,clock,complete legal move set and metadata.
Require all moves present with unambiguous win/draw/loss categories. Interpret
move categories from the CHILD side-to-move, reverse to root owner, and retain
all best category ties. Unknown/maybe/cursed/blessed/syzygy-only categories
remain unsupported here, never silently map to draw. DTZ is not mate distance.

This is compatibility with the service's independent50-move outcome contract,
NOT the local F24F max-ply/repetition goal. No FEN encodes local complete
history; record the true synthetic local history separately. No WDL bridge or
scientific completion follows. Report ALL policy ties, minimum/maximum source
outcome over each tie set and canonical outcome; successful intersection alone
is weaker than all-tie preservation. Source source-code metadata and author
legal equivalence qualify orientation, not independent proof of every label.

Primary source inspected before acquisition:
https://github.com/lichess-org/lila-tablebase/blob/main/README.md
documents standard endpoint, complete legal move metadata, nullable distances,
and50-rule mainline. Its response example's winning parent has a losing child.
Further category orientation must be checked in source before trusting labels.
No worker, heavy table download, original-trial rerun or human holdout access.
