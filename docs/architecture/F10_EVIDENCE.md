# GenericChess F10 evidence

## 1. Status

`F10_RESULT = OPTIMIZATION_PASS`; `H10B_CREATED = true`.

## 2. Baseline

The locked baseline is `origin/sandbox=7f83ef8c7c10381cdf712d884d359cacf9bdf0f4`,
`origin/master=4f1d03a308f5fd04a01bbd980c7411888ea1ed9d`, and
`origin/chat=d6b0d5720efe23019a7a2b4cce72e05beee2e6c4`.

## 3. Gmail / inbox provenance

The complete authoritative Gmail body and attachment were saved before execution at
`inbox/2026-08-14_GenericChess-F10_Semantic_Source-Index_Lifetime_Audit.md`.

## 4. Corpus

Profiles A and B used four semantic prefixes, two controls, and five measured repetitions.
The exact corpus is bound by `artifacts/f10_source_index_lifetime/corpus.json`.

## 5. Source call-chain audit

The audited chain is `iter_legal_action_bindings -> _iter_candidates ->
_iter_board_candidates -> _sources_by_owner_type`. The call-chain record is in
`source_call_chain.json`.

## 6. Source-index lifetime diagnosis

Before H10B, the source index was rebuilt per board-move pattern. Profile A recorded
181,170 builds and Profile B 729,010 builds; redundant same-position builds were about
75.0% and 71.6%, respectively.

## 7. Operation breakdown

The audit covered `FULL_LEGAL_BINDINGS`, `HAS_LEGAL_ACTION`, `S3_REPLY_EXISTENCE`,
`ATTACK_QUERY`, and `OTHER`. The complete breakdown is in `operation_breakdown.json`.

## 8. Timing attribution

H10A measured approximately 2.076 s of source-index construction in Profile A and
10.921 s in Profile B across the five-repetition diagnostic corpus. These are inclusive
diagnostic timings; the performance gate uses the independent no-trace formal runs.

## 9. H10A provenance

H10A was implemented in commit `882c061`; the candidate probe was added in `8c49d1d`.
The production-compatible audit wrapper fix is `65dbcfc`.

## 10. Optimization authorization gate

G1 through G6 passed. G1 found major-family median builds/op at least three with at
least 50% redundancy; G2 found material cost; G3 found no exact-index mismatch; and
G4 exceeded the candidate thresholds. The gate record is `optimization_gate.json`.

## 11. Candidate design or rejection

The authorized design is an operation-local optional source-index parameter. It is built
once for a legality operation, passed through board-pattern iteration, and never retained
across operations. Drop-only patterns avoid an unnecessary board index; attack queries
remain isolated.

## 12. Exact index equivalence

All audited before and after rows had zero exact-index-equivalence failures. After H10B,
each observed legality and attack operation built at most one index. See
`exact_index_equivalence.json`.

## 13. Legal-action parity

Formal before/candidate outputs matched on action, score, PV, node counts, completed depth,
termination, terminal status, and search counters for both profiles. `legal_action_parity.json`
records zero stable-field mismatches.

## 14. Attack/check parity

The attack-query path was deliberately left independent. Focused and full regression tests
passed; `attack_check_parity.json` records the result.

## 15. S3/S4 parity

Only source-index plumbing changed; S3 trial and S4 semantics were not altered. The
focused and full suites passed, with the result in `s3_s4_parity.json`.

## 16. Terminal/history/TT parity

Terminal status, history, rollback, and transposition-table/search counters remained stable
in the formal comparison and regression suite. See `terminal_history_tt_parity.json`.

## 17. Search parity

Search parity passed after excluding runtime timing telemetry from the stable semantic
comparison. No action/PV/node/termination/search-counter mismatch was found.

## 18. Interruptibility

Checkpoint arguments are forwarded through the operation-local path, and no index survives
an interrupted operation. `interruptibility.json` records PASS.

## 19. Push/pop/rollback/sibling isolation

The index is a local variable owned by one legality operation; push/pop and sibling isolation
tests passed. See `rollback_sibling_isolation.json`.

## 20. Performance

The no-trace formal candidate improved semantic median wall time by 9.79% in Profile A
and 17.76% in Profile B. All four semantic cases in both profiles improved by at least 3%,
and no stable control regression exceeded 3%. Full data is in `performance_comparison.json`.

## 21. Tests

The focused F8/F9/F10/search/mate-stalemate/repetition suite passed. The complete
`python -m pytest -q -p no:cacheprovider` run passed, and the fresh supported Zig build
passed. Logs are `full_pytest.txt` and `native_build.txt`.

## 22. Evidence / manifest

All new F10 evidence is under `artifacts/f10_source_index_lifetime/`. `manifest.json`
SHA-256 binds the closure files; `old_evidence_before.sha256` and
`old_evidence_after.sha256` are identical.

## 23. Git

H10B production implementation is in `1861b06`; the audit compatibility fix is in
`65dbcfc`. The final evidence/docs closure is committed after this report is generated
and pushed to `origin/sandbox`.

## 24. Deferred

No further F10 optimization is deferred. ATTACK_QUERY remains intentionally isolated and
is not converted into a cross-query cache.

## 25. Final verdict

`OPERATION_LOCAL_SOURCE_INDEX=PASS`, `SOURCE_INDEX_EQUIVALENCE=PASS`,
`LEGAL_ACTION_PARITY=PASS`, `ATTACK_CHECK_PARITY=PASS`, `S3_S4_PARITY=PASS`,
`TERMINAL_HISTORY_TT_PARITY=PASS`, `SEARCH_PARITY=PASS`, `INTERRUPTIBILITY=PASS`,
`ROLLBACK_ISOLATION=PASS`, `PERFORMANCE_GATE=PASS`, `FULL_PYTEST=PASS`, and
`NATIVE_BUILD=PASS`.
