# F86S closeout

- Work order: `GENERICCHESS-F86S-F86N_R1-JOINT-WITNESS-CONFINEMENT-AUTHORITY-RECOVERY`
- PREP checkpoint: `7d90b3e9cfb327dae291c1bb54b9b2399fe04b39`
- Original RESULT checkpoint: `3c8a8c95b37bd300e863a45057fbeb70e02b54b5`
- PREP manifest: `artifacts/f86s_f86n_r1_joint_witness_confinement/manifest.json`
- Witness evidence: `artifacts/f86s_f86n_r1_joint_witness_confinement/witnesses.json`
- RESULT summary: `artifacts/f86s_f86n_r1_joint_witness_confinement/summary.json`
- Architecture report: `docs/architecture/GENERICCHESS_F86S_F86N_R1_JOINT_WITNESS_CONFINEMENT_AUTHORITY_RECOVERY.md`

The PREP→RESULT runner was unchanged and the PREP manifest remained byte-identical (`SHA256 E7766FCE6D0DD236C434342531185CC1749C1676A8ED47D69A4694F5FED239D8` before and after RESULT). The targeted census reproduced V4-3 as 1296 candidate checks, 1166 validated positions, 108 templates, no truncation, and 2 ordinary/joint reachable witnesses. V5-3 reproduced 2048 checks, 1592 validated positions, 90 templates, truncation true, and 21 ordinary/joint reachable witnesses. Total checks were 3344 under the 4096 cap.

Exactly 2 V4-3 complete-census witness rows and 21 V5-3 `OBSERVED_UNDER_TRUNCATED_CENSUS` rows were persisted. Every row passed exact F86R checker geometry and has zero legal defender, Anchor-flight, checker-capture, and interposition/screen replies.

F86S-R1 correction baseline: `c1825764891a96e3b744659ce18c40c326d9d374`. Because F86R did not serialize dynamic occupancy, V4-3 is safely routed to `STATIC_VS_DYNAMIC_CONFINEMENT_DIFFERENCE_IS_MULTI_FACTOR`; V5-3 remains `STATIC_MATE_WITNESSES_HAVE_STRICTLY_STRONGER_NEIGHBOR_ATTACK_COVERAGE`; overall remains `CONFINEMENT_GAP_IS_SAMPLE_DEPENDENT`. F86R dynamic control facts were preserved: V4-3 one single-checker action with coverage 2 and two Anchor-flight breaks; V5-3 thirteen single-checker actions with coverage 0×8 and 1×5, with 24 Anchor-flight and 3 checker-capture breaking replies.

Focused F86S test result: `6 passed`; Courier recovery regression: `2 passed`. This correction used zero census checks, games, movement candidates, dynamic work beyond F86R, AlphaBeta, BFS, training, teacher search, C2, F85, and Heavy. Default generator: unchanged.
