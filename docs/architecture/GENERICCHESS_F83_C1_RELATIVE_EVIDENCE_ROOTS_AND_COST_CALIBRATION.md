# GenericChess F83: C1-relative evidence roots and teacher-cost calibration

Status: `C1_RELATIVE_EVIDENCE_ROOTS_FROZEN_TEACHER_COST_LOWER_BOUND_ONLY`.

F83 performed no C2 fitting or training, optimizer execution, candidate
checkpoint generation, Arena, self-play strength evaluation, external-engine
work, sealed-corpus reuse as training data, or production semantics change.

The frozen root corpus is
`artifacts/f83_c1_relative_evidence/root_corpus.json` with corpus ID
`37a323abe5935720463a8e544a23f0d5d4ce58ee14f6a75b4cece178dc8c0b0a` and
content SHA
`9d38241387478465650629a47caf2279af10ebef5847af75fdd3285c7dc09e69`. It
contains 54 globally unique C1-relative roots:

- 16 `reachable_random`, 16 `c1_on_policy`, and 16 `c1_pv_corridor`
  acquisition roots;
- 12 train and 4 dev roots in each acquisition stratum;
- 2 resource-only roots in each stratum.

All recorded overlaps with F62, F75, F77, F78/F80, and F81 sealed histories
are zero. The corpus binds C1
`f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4` and model
SHA `b4372d087d0e7760857efefd69413c97c8cf10b5b188dd704f5d1e308a4d32b6`.

The resource-only teacher probe is
`artifacts/f83_c1_relative_evidence/teacher_cost_probe.json` with content SHA
`3b05ff6d999928f97906b4eedae611b5c15b50ae06786cbb674cfaef3063e2ab`. It
used the tracked F62 spectrum contract and six probes at most two concurrently,
with a 180-second per-root cap. All six probes reached the cap; none was
accepted as a teacher label, and no probe failed its harness. The conservative
48-root estimate is approximately 144 minutes at one lane, 72 minutes at two
lanes, and 36 minutes at four lanes, with a 2.40 CPU-hour upper proxy. Wall
time therefore crosses the repository's large-work threshold despite CPU
remaining below five hours.

F83 stops here. The next step must be a separately approved F84 decision about
full acquisition, using this lower bound and a versioned compute plan if the
work proceeds. No C2 candidate or champion change is produced by F83.
