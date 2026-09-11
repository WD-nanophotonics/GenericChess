# F86K backward-rank targeted partial reversibility

Status: completed static-only work order. The candidate was pre-registered and
published at prep SHA `cf8e5d69e1017e1810a23a569bfea749764efaa9`; the prep
manifest blob is `2fd00b32991533144ba8d790d618227ed718ca5c`. The candidate is
bound to the frozen F86C source rulesets and compared by fingerprint with the
F86I full-closure candidates. No default generator behavior changed.

## Candidate contract

Profile: `ORTHO4_PLUS_FIRST_STRICT_FORWARD_REVERSE_ORDINARY`.

The Anchor is the fixed ORTHO4 family. For each ordinary type, the first
source LEAP with `offset[1] > 0` or RAY with `direction[1] > 0` is selected in
frozen source order. Its exact reverse is appended only when absent. Source
atoms remain the prefix. Types without such an atom record
`NO_STRICT_FORWARD_SOURCE_ATOM` and receive no added family. Full reverse
closure, HOME/FULL8, promotion, drops, material, opening, and defaults are not
changed.

The exact per-type selected atom and reverse are recorded in the manifest. The
observed selections were:

| Samples/types | Selection |
| --- | --- |
| V4-2/P0; V4-3/P0 | no strict-forward source atom; no reverse added |
| V4-3/P1; V5-3/P1; V5-5/P1 | LEAP `(-1,1)` -> `(+1,-1)` |
| V4-3/P2 | LEAP `(+1,2)` -> `(-1,-2)` |
| V4-4/P0 | LEAP `(-1,1)` -> `(+1,-1)` |
| V4-5/P0; V5-2/P0; V5-3/P0; V5-4/P0; V5-5/P0 | LEAP `(+1,1)` -> `(-1,-1)` |

F86K collapses to the F86I full-closure fingerprint for V4-4 and V4-5. Those
rows are comparison evidence only, not new intervention evidence.

## Fingerprint binding

| Sample | Frozen source fingerprint | F86K candidate fingerprint |
| --- | --- | --- |
| V4-2 | `1b8547501a45ebc1344f7134319ed215de09a51dfb001270dc127e77528698ac` | `ac2d9b8bdd3faa183d209e3c2cd69062c61e1bd73dbd59e90e02aa33f9359cde` |
| V4-3 | `7e2ff9e15c2a0d1be5faa8c6697f22e488976a2d2ae9f077b85c6e71f95ff400` | `0374bba8cade19cfffd374139d556586e9dbe9978b4bf5c299d48b1bdf6347ab` |
| V4-4 | `864e9aaf0f36b0a94024454a357e6787b3edd9cfd81898d1bea76dfc591b08d0` | `ed6784e034a0bd625be4d69bace6a459c9d16d590abf93066025115603ed0fde` |
| V4-5 | `9a5f3de7a492fa4fa01ca1b4c2e7a11b24403cde87b79761b26e212d13221f24` | `effc9905d3b3afd3d67d4696ec0c259531f05feb380479f590179fb9fac063b1` |
| V5-2 | `ddacec0f6b6fbffeb9135fbbbb658093d92ce0e5bce28665a87022b702d815d6` | `0c6aa8afa8b571c4cad8bead2962367a73abc4c94c6aef9e227b05fd81a6422e` |
| V5-3 | `d6e47a6fe19ab20538a1ec9539597b5765d0211cb608b15c262613a86e635297` | `74db9dbacc5234524b844062609f5aa4e273a8cef2627bd6d137be07be45ae35` |
| V5-4 | `580475d4c25b8d5bb9d796902d383ac673bd00c3565e4609d07443bcc338ad04` | `9e4c3f8a9bc5279ad5d8464d6bdadaac1e6f138f4e90812dcfc2cb71660dfd07` |
| V5-5 | `c3fa844c61ea944f9fd11560f00878337389f427a59d84958c312e38d5494d31` | `19e70cb043da1f4b04501a565b3ea5c0330dce92f61bf8b09dd73030290e17e5` |

## Static result

The empty-board mechanism census and opening-rank diagnostic were run for all
eight frozen samples. Owner-relative rank is board rank for owner 0 and
`board_size - 1 - board rank` for owner 1; “can reach” is graph reachability
over compiled empty-board mobility, not a game or tactical search.

| Sample | Direct reverse fraction | Nontrivial SCC fraction | Backward-capable type fraction | Opening pieces reaching lower rank |
| --- | ---: | ---: | ---: | ---: |
| V4-2 | 0.000000 | 0.000000 | 0.000000 | 0.00 |
| V4-3 | 0.441176 | 0.541667 | 0.666667 | 0.00 |
| V4-4 | 1.000000 | 0.875000 | 1.000000 | 0.75 |
| V4-5 | 1.000000 | 0.875000 | 1.000000 | 0.60 |
| V5-2 | 0.780488 | 0.920000 | 1.000000 | 0.50 |
| V5-3 | 0.609524 | 0.920000 | 1.000000 | 1.00 |
| V5-4 | 0.390244 | 0.920000 | 1.000000 | 0.75 |
| V5-5 | 0.587156 | 0.960000 | 1.000000 | 0.80 |

Targeted static census used 2,204 checks total (V4-3: 156, complete;
V5-3: 2,048, truncated at cap). Validated positions/templates were V4-3
111/12 and V5-3 1,871/98. Neither cell produced a positive joint kinematic
mate-template witness. Routing is therefore:

- V4-3: `BACKWARD_RANK_RESCUE_INSUFFICIENT_KINEMATICALLY`.
- V5-3: `MATE_CAPACITY_UNRESOLVED_DUE_TO_CENSUS_CAP`.

The route helper gives a positive witness precedence over truncation, but no
such witness was observed. No dynamic smoke run was authorized by this static
gate.

## Compute and verification

New real games: 0. Teacher/search/training compute: 0. F85 compute: 0.
Tactical probes and BFS expansions: 0. Static caps were 2,048 checks per cell
and 4,096 total. The exact compact result is in
`artifacts/f86k_backward_rank_partial_reversibility/results.json`; raw
benchmark output is not tracked, per repository policy.

The F86K contracts pass 4/4. The final bounded checkpoint runs the F86I/F86J/
F86K contract set together and is published with the accepted result commit.
