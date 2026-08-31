# ADR-097: Semantic Qsearch Check-Discovery Fastpath Audit

## Status

F33 H33A audit-only PASS; no Candidate A or B is retained in production.

## Decision

F33 evaluated two additive prototypes against the frozen ten-root Standard
Shogi corpus. Candidate A reused the authoritative `gave_check` value already
stored in the runtime history frame after a committed push. Candidate B used
the cached semantic binding to preview the exact child Position, checked the
resulting position (including discovered checks), conservatively fell back for
history-sensitive adjudication, and otherwise probed legal-action existence.
Both candidates retained the production noisy action sequence and exact fixed
node search result. The audit never changed `generic_chess/`.

The H33A manifest SHA is
`14de91028470b9bf4d3a8933a73912fa1e0b2567fb70ca106e0a284d778378bf`.
The result fixture is
`tests/fixtures/f33_check_discovery_audit.json` with SHA-256
`e65300346bb7be48bcf933a163d25f5700fe7c2b93efc5b577b491eee973f25c`.
F32 R1 and first-pass identities remain frozen in the fixture.

## Findings

Candidate A passed classifier and fixed-node result parity but retained all
28,307 / 87,780 committed classification pushes at 512 / 2048 nodes. Candidate
B passed classifier parity and fixed-node result parity, and reduced committed
classification pushes from 28,307 to 0 at 512 and from 87,780 to 0 at 2048.
The fixed-node median timing gains were 16.11% and 13.42%, below the required
20% performance gate; no root accessibility gate passed. Therefore neither
candidate is retained, despite the structural reduction.

The exact classifier recorded 0 mismatches for all three variants. It
preserved direct and discovered checking behavior, and the audit executed
terminal, repetition/continuous-check, max-ply, automatic-adjudication, and
opaque-history conservative fallback paths. `qnode-cap` semantics remain
unchanged and are not redesigned here.

The derived next boundary is
`F34_QUIESCENCE_BUDGET_ARCHITECTURE`. A reduced noisy set, `_action_delivers_check`
substitution, qdepth change, evaluator change, Native repair, rule change, or
promotion is not authorized.

## Regression and scope

H33A target tests passed. Full regression retains only the historical 12
F13/F14/F21 Native failures and the F24F Kiwipete depth-1 mismatch (45 vs 48).
No new failure was introduced and production diff is ZERO.
