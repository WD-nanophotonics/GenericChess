# ADR-WEB-002: User-authorized production engine synchronization

Date: 2026-10-12. Mode: local. Delivery branch: ui-test only.

## Decision and source

The user explicitly requested the latest Sandbox search improvements in the
browser game and a more capable opponent. This supersedes the prior prohibition
on updating the pinned backend for this one reviewed synchronization. It does
not authorize changes to sandbox/master or automatic recurring merges.

Previous production source: b236c79ab7d11b2f234af4e099eb8b4208149f26.
Reviewed remote sandbox HEAD: 7b988c9f247fd3eb96ca17daedf28e5c4d93b3cd.
All 195 manifest sources equal that exact remote commit after LF normalization.
23 production files changed; their contents are copied verbatim, with no UI-side
engine edits. The manifest records both source revisions and update authority.
Frontend, launchers, UI-specific policy, human material values and save data are
retained. No research files, training models, experiment scripts or binaries are
runtime dependencies. The copied independent production regressions exercise
the updated paths; historical parity tests may need NumPy in the test environment.
One historical certification test is guarded with importorskip for its optional
cshogi helper; no runtime dependency or engine behavior is changed.

## Included improvements and boundary

Compiled incoming-attack and actor/drop/transition dispatch indices avoid repeated
semantic work. Runtime history/auxiliary identity and occurrence rollback fixes
preserve legal and repetition semantics. Semantic cancellation and deadline
checkpoint handling is repaired/streamlined, and root budget starts before history
import. PlayerDecision adds retained-result provenance without changing default
q policy. Latest production Shogi correctly treats no legal action as a loss.

Keep Python Core AlphaBeta, ordinary q4/hard8, default ordering and fixed-time
0.5/1/3-second settings. The UI material profile remains the same Chess/Shogi
human teaching table; generated/custom rules keep rule-derived prices.
Native source/adapters are synchronized coherently but UI explicitly disables
Native legality. Web runtime remains Qt-free and needs no compiler.

Sandbox Q0_THRESHOLD_CONFIRMATION and LOCAL_UI_SEARCH_TEST describe experimental
Native q0/material-only search and limited compatibility. Their reports explicitly
retain default/UI policies and do not demonstrate general one-second playing
strength. Do not silently adopt that research route, root ordering, terminal
shortcut, q4 refresh, or unsupported declaration fallback.

## Save compatibility and visible identity

Old bundles embed their rules, record and fingerprint. Never rewrite them to the
new Shogi rule/fingerprint. The human table matches both exact old/new production
Shogi fingerprints, so old saves do not accidentally revert to generic prices.
New Shogi games use the corrected no-move-loss policy. UI/API roundtrip regression
checks original rules and positions. The API health and each state expose source
SHA; the AI bar shows the dated Core q4 label, from service metadata.

## Local delivery measurement

Four fixed positions (four deterministic legal plies from Chess, Shogi and
seed42 generated/hybrid), three fresh-player calls each, one second per call,
q4/hard8 and unchanged evaluation. Exported rules/record are reused verbatim for
the after arm, including old Shogi rule identity. Node totals, elapsed time and
legal result are recorded in ignored artifacts/engine-sync. They are smoke
measurements, not a playing-strength benchmark or a portable speed guarantee.
Initial paired runs and the idle-machine after-arm repeat completed Chess D1 before versus D2 after, and Shogi D1
versus D2 after; generated and hybrid stayed D1. All moves were legal.
One-second deadlines are cooperative, with small indivisible-work overshoot.
No Elo, win-rate or uniform strength claim follows. Prefer meaningful complete
PVE testing over treating a deeper horizon as proof of stronger play.

## Validation

UI/PVE/lifecycle, material policy, HTTP/WebSocket and launcher regression;
compiled dispatch, runtime history/identity/rollback, semantic checkpoint,
Shogi, evaluator and search accounting regressions; full frontend build and
real Edge desktop/mobile PVE, promotion/drop, import/export and reconnect.
195-source frozen check is now against the explicitly reviewed new source.
Optional Native tests may skip when no extension is installed; Native is not the
selected UI backend. Test outputs and screenshots stay ignored.

Future synchronization must repeat source review, compatibility testing and
source SHA verification, then publish only ui-test. Engine research remains
owned by sandbox. The next integration merge is still separately authorized.

Final verification: 473 passed / 32 optional-dependency skips (the complete
combined UI/product synchronization suite), 16/16 real Edge desktop/mobile
browser tests, production Vite build, 195 LF-normalized source hashes, and
Qt/NumPy-free Web player creation. The skipped cases exercise optional Native
extensions and the optional historical cshogi certification helper, not the
selected Core UI backend. Original saves were not used for browser test fixtures.
On this host 8765 is occupied by another service, so the delivered game runs on
127.0.0.1:8770 with the normal .web_state directory; --port retains configurability.
