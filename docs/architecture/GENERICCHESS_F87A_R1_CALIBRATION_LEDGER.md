# F87A-R1 compact calibration ledger

This tracked ledger is the durable summary of the F87A-R1 RESULT. Raw trajectories and generated JSON remain ignored. The run is bound to PREP baseline `1c35c41d817ff0c238db146bc67dee7dc7c0f660`, target `PLAYABILITY`, required layers `A-C`, and the single status reducer. Replay identity is an integrity gate; dynamic playability is a separate qualification gate and remains `DEFER` until calibrated.

| Control | Fingerprint | A / B / C | Key calibration evidence | Terminal counts | Compute |
| --- | --- | --- | --- | --- | --- |
| F86C legacy V4-3 | `7e2ff9e15c2a0d1be5faa8c6697f22e488976a2d2ae9f077b85c6e71f95ff400` | PASS / PASS / DEFER | `LATTICE_RANK_DEFICIT`, `LATTICE_RESIDUE_CONFINEMENT`, `SINK_COMPONENTS`, `ONE_WAY_TRANSPORT`, `FINITE_REACHABILITY_CONFINEMENT` | stalemate 4 | 4 games, 37 plies, 0 search nodes |
| F86I full-reverse V4-3 | `8ca58376a52e539c7c8519e902b8dd9e6991b002586d36d846a7a864fffea05d` | PASS / PASS / DEFER | `HIGH_LOCAL_REVERSIBILITY`, `TERMINAL_TEMPLATE_TRANSPORT_INSUFFICIENT`, plus finite/lattice diagnostics | CENSORED 4 | 4 games, 128 plies, 0 search nodes |
| F86N-R1 boundary V4-3 | `856a810d3a21eec779f9ba8300ce602cd24d3e8850ba895e39579603fd4ff3e2` | PASS / DEFER / DEFER | `STRUCTURAL_BACKBONE_WITNESS`, `BOUNDARY_NOT_ADMISSION` | CENSORED 2, stalemate 2 | 4 games, 111 plies, 0 search nodes |
| F86N-R1 boundary V5-3 | `e8528688a64bce3f39231d9e4f38d5d200ade57c6f517ae33ce9b71b9f75ebe5` | PASS / DEFER / DEFER | `STRUCTURAL_BACKBONE_WITNESS`, `BOUNDARY_NOT_ADMISSION` | CENSORED 4 | 4 games, 128 plies, 0 search nodes |
| Built-in Western Chess | `7bc6cf3179f4eaea30b205576b9032dca47a16803e9cc8b3e29405cb1e820b35` | PASS / DEFER / DEFER | `SEMANTIC_MOVEMENT_NOT_APPLICABLE`; legacy Common-Tape is `UNMEASURED` | not measured | 0 games, 0 search nodes |
| Built-in Standard Shogi | `ac987c3ffe75d8fa885ba787c1aa7cf60e92205465bf056b12b2989674007635` | PASS / DEFER / DEFER | `SEMANTIC_MOVEMENT_NOT_APPLICABLE`; legacy Common-Tape is `UNMEASURED` | not measured | 0 games, 0 search nodes |

Every control has `overall_status=DEFER`. CENSORED trajectories carry null outcome scores and do not enter side-bias denominators. All four legacy/boundary controls use canonical JSON action ordering; opening sensitivity is `UNMEASURED` because the bounded run has one opening identity. Layer D/E, Arena, training, Heavy, C2, F85, and QD/MAP-Elites remain out of scope.
