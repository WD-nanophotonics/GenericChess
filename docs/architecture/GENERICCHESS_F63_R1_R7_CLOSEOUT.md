# F63-R1-R7 candidate CLI summary corrective closeout

R7 fixes the resume-only CLI/reporting defect identified after the approved
common-4 run. Stage-scoped candidate results intentionally do not contain the
legacy teacher `classification` field; the terminal summary now treats that
field as optional and reports the frozen teacher decision state separately.
Candidate-only results, including `COMMON_INCOMPLETE_RESUMABLE`, can therefore
serialize successfully without fabricating a teacher conclusion.

The focused regression covers the candidate-only resumable result shape and
keeps the candidate identity test isolated from real runtime state. Validation
completed before closeout:

- `tests/test_f63_champion_loop_causal_triage.py` and
  `tests/test_f63r1_game_atomic_arena.py`: 23 passed;
- `py_compile` passed for `scripts/f63_champion_loop_causal_triage.py`;
- the historical failed run remains
  `f63-r6-common4-03e648359600` with exit code 1;
- no Heavy is running and common-4 was not restarted;
- the retained game-v1 file remains SHA-256
  `e205dcfab1b4eff012ac496919ae80b4ab93b882e310fcf59c52f42b504c92f2`;
- candidate-59011 remains at one completed game and zero complete pairs, with
  no candidate selection.

The corrective implementation checkpoint is
`6670aaf957407cd4b4f801915c3ab7aba2cc388e`, published to `origin/sandbox`.
The previous common-4 compute approval bound to sandbox
`442bea51330ae0225bb28423c61b3dc59d2b5572` is obsolete because the code SHA
changed. A fresh current-SHA common-4 plan and fresh Chat plus Supervisor
approval are required before any resume. This R7 closeout does not authorize
execution, selected-8/32 work, or changes to the 80-ply cap.
