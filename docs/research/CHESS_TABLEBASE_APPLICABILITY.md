# Independent Chess tablebase applicability, 2026-10-04

Status: primary-source/local-code audit only. No tablebase files, packages or
services were installed, no positions were submitted to an external endpoint,
and no deployment labels were read. This is a new label-source investigation,
not a retry of the old bounded mate/service experiments. Shogi and Xiangqi
labels are outside the coverage of these Chess libraries.

## The present executable goal

build_western_chess_ruleset in generic_chess/rules/western_chess.py creates
the F24F movement-certification fixture, not all FIDE adjudication. Its explicit
repetition_limit is100000, max_ply1000, stalemate is draw; no_progress_draw is
unset and no declarations/custom automatic/consecutive adjudications are added.
Full legal moves include promotion, castling and en passant. Movement/perft
certification does not justify importing a different history/terminal rule.

Both generic_chess/core/terminal.py:_terminal_from_parts and
generic_chess/core/semantic_executor.py:terminal_result check lack of legal
actions/checkmate or stalemate before max_ply. A mate reached exactly at the
1000th ply wins rather than being truncated to a draw. History is not reset
when probing a child. A synthetic high repetition count could still trigger
the100000 threshold; normal short histories do not make that threshold reachable
before the max-ply draw. For a precise adapter require max current repetition
count + remaining horizon < repetition_limit, rather than assuming history empty.

## Candidate sources and mismatches

| Source | Published label meaning | Present use decision |
| --- | --- | --- |
| Syzygy through python-chess | WDL under50-move rule and rounded distance-to-zeroing; positions with castling rights excluded | No unconditional import into F24F goal |
| Lichess tablebase service | Category family includes uncertain/cursed/blessed results; nullable DTM and precise DTZ | Metadata alone is not a compatible certificate |
| Gaviota through python-chess | WDL and signed half-move DTM, up to5pieces; no castling rights | Conditional low-inventory lead, not yet an adapter |

Syzygy WDL probing assumes a capture or pawn move just occurred. Its +/-1
cursed/blessed cases distinguish mate potential from50-rule draws; DTZ is a
zeroing distance, sometimes rounded by one ply, not a minimax mate distance.
Required capture/promotion successor material tables must also be present.
These facts rule out treating any returned numeric score as our owner-zero
goal value. [Maintainer Syzygy documentation](https://python-chess.readthedocs.io/en/latest/syzygy.html)

The Lichess API describes dtm/precise_dtz as nullable and an expanded category
set, including unknown/maybe results. Its documented mainline claims50-move
draws. A principal variation is one line, not all defensive branches or proof
of a horizon value; best-first move ordering must not select our roots or acts.
[Service maintainer API](https://github.com/lichess-org/lila-tablebase/blob/main/README.md)

Gaviota's adapter documents DTM in half-moves, positive for a winning side to
move, negative for losing, with zero meaning either draw or already checkmated.
It therefore requires a separate authoritative terminal/WDL distinction at zero.
Pure Python access is available; native access has shared global state/cache.
Neither path was opened here. [Maintainer Gaviota documentation](https://python-chess.readthedocs.io/en/latest/gaviota.html)
The Texel author's integration analysis explicitly identifies Gaviota as
ignoring the50-move draw rule, and uses additional conditions to apply its mate
information to FIDE play. We would need the reverse audit against F24F plus
its finite total-ply horizon. [Texel tablebase integration](https://github.com/peterosterlund2/texel/blob/master/doc/tbprobe.md)

## Conditional finite-horizon bridge, not an implemented certificate

Suppose an independently trusted tablebase proves unlimited-game WDL and exact
minimax mate distance D under precisely the same move/mate/stalemate semantics
as the local executable game. Assume no other history/claim draw can occur
before its remaining total-ply horizon H, and mate has priority at H.
For an ongoing root, define owner-zero goal values, converting side-to-move
orientation explicitly. Then unlimited draw remains finite draw; a nonzero
WDL with |D|<=H retains its sign; a nonzero WDL with |D|>H becomes finite draw.

Reason: in the winning case, the winner minimizes and defender maximizes time
to forced mate while preserving their WDL objectives. Within D the winner can
force mate. Below D the defender can avoid that mate through the horizon, and
the unlimited winner has a strategy avoiding loss, so neither can force the
opposite signed outcome; truncation is draw. In an unlimited draw each side
can avoid losing forever, hence through H. This is our conditional inference,
not a claim that a current API already supplies all premises or that DTZ is D.
Terminal roots must use fresh local terminal status before any conversion.

Unverified move equivalence, castling/en-passant support, unknown/missing tables,
ambiguous DTM zero or extra adjudication must instead yield unknown. File hashes,
source/library version, board orientation, side-to-move and absolute ply/history
belong in any future frozen certificate record. A FEN alone does not encode the
full local history or remaining total-ply budget. No rules were changed to make
an external label appear applicable.

## What this enables and what remains

Reject direct Syzygy50/service-category substitution. Keep a Gaviota DTM adapter
as a concrete alternative for <=5-piece, no-castling roots after an independent
move/state conversion and terminal-priority qualification. Its actual file
availability/size, verified checksums and probe cost have not been audited;
no blanket download/generation or enlarged experiment budget is admitted.
It cannot certify full-inventory Chess pilot roots or provide Shogi control.

Next construction work can proceed independently of this label gap. Before
any new decision-use corpus, either qualify a compatible low-inventory law and
certificate source or choose a bounded validation question whose expected label
coverage is demonstrated. Do not generate more all-unknown roots first and
then increase depth, reset history or replace unknown with draw.
