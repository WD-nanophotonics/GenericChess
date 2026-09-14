# F85B v14 Teacher Acquisition Closeout

The approved minimal teacher acquisition completed successfully for all 36
frozen F83 training roots.  The phase-resumable path sealed the canonical
`artifacts/f85_c2_train_teacher_evidence/training_evidence.json` artifact with
status `COMPLETE_TRAIN_TEACHER_EVIDENCE_SEALED` and `root_count=36`.

The published canonical artifact is byte-for-byte assembled from the 36
COMPLETE phase checkpoints without recomputing or changing any teacher row.
Its raw file SHA-256 is
`3160e3935f8b862209d5be802ee9739a0d7d4e590730fa423099603cfe827aad`.
It contains 36 unique root IDs and position keys, all `train` roles, strata
`12/12/12` for reachable_random/c1_on_policy/c1_pv_corridor, non-empty teacher
rows for every root, and no selected-action count above 8.

Execution was bound to the exact published implementation and approvals:

- implementation SHA: `878b35009eb5dedcc88042fc876000d36a2ca433`
- plan: `f85b-c2-minimal-teacher-rows-v14`
- plan SHA: `e53740b7e2fd7a113e0743f3b8549bb7317695a7d35e547a4518b9e3a265a997`
- envelope SHA: `4330440ebc2515d968b3bc9ceaa526153199e28858fbac85332182a776d8bf7f`
- canonical minimal-manifest digest: `585550922d28ca7c17dd5431c98409b8750653933722661f2cc9cdf7a7e5d37b`
- resource envelope: two lanes, 900-second per-root bound, 9,954,000 maximum nodes

The execution used no automatic retries or limit changes.  No C2 fit and no
Arena were run in this order; those remain the next separately authorized
mainline decisions.
