# GenericChess F11 evidence

## 1. Status

`F11_RESULT = AUDIT_ONLY_PASS` and `H11B_CREATED = false`.

## 2. Baseline

H11A locked sandbox `83b921a07277ca7186f66a65ecc95fb040838a34`, master
`4f1d03a308f5fd04a01bbd980c7411888ea1ed9d`, and chat
`d6b0d5720efe23019a7a2b4cce72e05beee2e6c4`.

## 3. Gmail / inbox provenance

The complete authoritative Gmail body was persisted at
`inbox/2026-08-14_GenericChess-F11_Post-F10_Semantic_Search_Re-Baseline_Single-Winner_Optimization.md`.

## 4. Corpus / tuning

The certified six-case corpus, Standard Shogi fingerprint, Profile A/B tuning, warm-up,
and five repetitions are bound in `corpus.json` and `tuning.json`.

## 5. Post-F10 whole-search attribution

The opt-in H11A probe measured semantic generation, S3 transition/trial, attack/check,
terminal, runtime push/pop/hash, evaluation, geometry, path/guard, source-index, and
search recorder categories. Inclusive timings are not summed as a wall decomposition.

## 6. Deep profile

Bounded cProfile completed for representative Semantic Shogi Profile A and B cases. Both
were within the 60-second cap. Cumulative and self-time top-50 reports are retained.

## 7. Structural counts

The whole-search rows include patterns, geometry candidates, S0/S1 candidates, S3 trials,
accepted trials, attack/check calls, pushes/pops, terminal probes, source-index builds,
history/hash counters, legal actions, successors, evaluation, qnodes, and TT counters.

## 8. Hotspot ranking

The dominant current family is exact semantic attack/check work, followed by checkpoint
dispatch and runtime push/terminal/hash work. Geometry enumeration is measurable but
subdominant. The machine-readable ranking is `hotspot_ranking.json`.

## 9. H11A provenance

H11A audit script and evidence were committed and pushed in `f2caf31`. No production
module was modified by H11A.

## 10. Candidate matrix

Attack memoization/target-directed geometry, general caches, and runtime identity redesign
are forbidden by F11. Geometry allocation reduction and evaluator optimization are allowed
examples but did not establish dominance or a safe material end-to-end probe.

## 11. Single-winner decision

`NO_CLEAR_SINGLE_WINNER`. No family simultaneously met the dominance, locality, and safe
probe requirements. Therefore H11B was not created.

## 12. Optimization authorization gate

G2 (root cause explained) passed. G1/G3 did not support authorization; G4–G6 were not
run because no candidate was authorized. This is a frozen `NO_CLEAR_SINGLE_WINNER`
audit-only outcome, not a lowered-threshold decision.

## 13. Candidate design or rejection

No candidate design was retained. Explicit `NOT_RUN_NOT_AUTHORIZED` records are used for
candidate formal files; no fabricated before/after performance is reported.

## 14. Legal-action parity

No H11B production candidate existed; therefore candidate parity was not run. F10 and all
focused regressions remained unchanged and passed.

## 15. Attack/check parity

No attack/check candidate was authorized. The dominant attack/check family is rejected for
F11 because it would revive F6/F7-style geometry or memoization architecture.

## 16. S3/S4 parity

No H11B candidate existed. Existing S3/S4 regressions passed; production semantics were
unchanged.

## 17. Terminal/history/TT parity

No H11B candidate existed. Existing terminal, history, repetition, continuous-check, and
TT regressions passed; production state was unchanged.

## 18. Search parity

No candidate differential was authorized. The H11A whole-search outputs are deterministic
for logical fields within each run and preserve the frozen search policy.

## 19. Interruptibility

No candidate was retained. Focused interruptibility/runtime tests passed, and no production
checkpoint behavior was changed.

## 20. Rollback/sibling isolation

No candidate state was retained. Focused push/pop, rollback, sibling-isolation, F9, F10,
and search-runtime tests passed.

## 21. Performance

F11 is audit-only; no candidate performance gate applies. H11A is the post-F10 authority:
Profile A semantic cases were approximately 0.536–0.737 s, and Profile B approximately
2.461–3.146 s under the instrumented whole-search attribution run. These are not claimed
as an optimization delta.

## 22. Python-local runtime headroom

`PYTHON_LOCAL_RUNTIME_HEADROOM = LIMITED`. The evidence recommends exactly one next
boundary: `NATIVE_SEMANTIC_EXECUTION_AUDIT`. It was not started in F11.

## 23. Tests

The focused F11/F10–F3 semantic, runtime, history/TT, and native-stress suite passed.
The complete `python -m pytest -q -p no:cacheprovider` suite passed 100%.

## 24. Evidence / manifest

All new evidence is under `artifacts/f11_post_f10_rebaseline/`. `manifest.json` binds the
closure. `old_evidence_before.sha256` and `old_evidence_after.sha256` are identical and
cover F4–F10 artifacts, evidence docs, and ADRs 022–027.

## 25. Git

H11A is `f2caf31`. E11 closure is committed after this report and pushed to `origin/sandbox`.
Master and chat remain unchanged; no force-push or reset was used.

## 26. Deferred

Do not begin F12. Defer exactly one boundary: `NATIVE_SEMANTIC_EXECUTION_AUDIT`.
Search-strength/evaluator work is outside this F11 recommendation.

## 27. Final verdict

`F11_RESULT=AUDIT_ONLY_PASS`  
`H11B_CREATED=false`  
`reason=NO_CLEAR_SINGLE_WINNER`  
`FULL_PYTEST=PASS`  
`NATIVE_BUILD=PASS`  
`PYTHON_LOCAL_RUNTIME_HEADROOM=LIMITED`
