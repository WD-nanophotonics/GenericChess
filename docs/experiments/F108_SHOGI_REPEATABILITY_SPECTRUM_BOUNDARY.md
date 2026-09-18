# F108 Shogi repeatability spectrum boundary

F108 was superseded as the mainline by a newer Policy-v0 direction while its exact F59 action-spectrum stage was already running. Per Supervisor instruction, the stage was allowed to reach its nearest natural resumable boundary and was stopped immediately after all 48 roots were persisted. No candidate training, candidate checkpoint, or Arena2 was run.

## Frozen input and persisted surface

- Sandbox baseline: `d572847986f148fa316b37fb2897dffa261ae306`
- Ruleset: `B_CANONICAL_STANDARD_SHOGI`
- Parent/teacher checkpoint: `f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4`
- Parent compact model SHA256: `b4372d087d0e7760857efefd69413c97c8cf10b5b188dd704f5d1e308a4d32b6`
- Source opening seed: `1080101`; diagnostic seed: `1080102`
- Source openings: 16; diagnostic roots: 48; three roots per source opening; continuation plies 8–40
- Persisted source surface SHA256: `3ac7f52d6b2fbb7847d66798922ba7a2cabdb1760cb80d60c99d0af3a7e51006`
- Persisted spectrum roots: 48 files, 13,323,540 bytes

The persisted surface passed its uniqueness and historical disjointness checks against F62 roots and the F78/F81/F107R1 Arena opening identities before spectrum generation. The exact F59/F62 production spectrum routine produced 40 stable 10k/20k consensus roots. Applying the F74/F78 trusted-root predicate yielded 30 trusted roots and 212 retained action rows:

`root_40k == root_80k == spectrum_top_10k == spectrum_top_20k`, no root-80k mate band, and no retained-q20 mate band.

## Boundary and interpretation

The F108 process was interrupted after root 47 completed and before `_adam_fit`, alpha backtracking, candidate persistence, parity checks, or Arena2. Therefore F108 has no candidate identity, safety decision, or strength classification. The spectrum is retained as bounded control evidence only and does not establish repeatable next-generation learning.

The next mainline is the separately authorized Policy-v0 work order: a dedicated policy learner with one state inference and batched logits over legal actions, semantically derived action features, separately trained Chess and Shogi weights, equal-budget searched-spectrum targets, held-out ranking/regret, and equal-wallclock AlphaBeta Arena validation. TreeStrap remains secondary and bounded; Gumbel MCTS waits for Policy-v0.
