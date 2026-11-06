# UI Test branch policy

This branch is the user-authorized UI-only development lane. It is NOT the
sandbox local research agent. Read README.md and docs/ui/UI_TEST.md first.
Do not require ignored .local_agent files, Slack credentials, research sessions,
a heartbeat, native build tools or any additional worker to develop this UI.

The user explicitly requested another established production AI sync on
2026-11-06. The current source is ff073a3b57b46873ccb23078fa7d950a40133891.
The earlier production engine sync is recorded in
docs/ui/ADR-WEB-002-engine-sync.md. Future updates require explicit user direction.

The complete Python Core AI, rules, generation, session, clocks and evaluation
are frozen from ff073a3b57b46873ccb23078fa7d950a40133891. Source hashes are in
docs/ui/AI_BASELINE.json. Use generic_chess/ui/ai_backend.py as the player factory.
UI Test is authoritative for the browser and desktop frontend. When the user
authorizes a sandbox backend update, import only the reviewed production engine
sources and required backend dependencies. Do not import sandbox frontend changes
or merge the whole branch. Make any required interface adaptation on ui-test and
verify that the frontend and save compatibility are preserved.

No completion-search prototypes, training, price experiments or research files
are runtime dependencies. Research history in this Git checkout is reference,
not a task backlog or permission to change the engine.

Develop generic_chess/ui/**, UI assets, launchers, presentation/interface
adapters and UI tests. Keep mutation through UIController/GameSession public
operations and retain cancellation, stale-result protection, terminal handling,
promotion/drop choice and record roundtrips. A browser UI may add a thin service
adapter in a separate UI module; do not duplicate legality/search in frontend.

Do not change generic_chess/{ai,core,rules,generation,session,native,_native},
clock/history semantics, or the baseline manifest to make UI tests pass. If a
backend problem blocks UI work, save exact rules/record/actions and report it
for sandbox handling; do not start parallel AI development here. Interface
changes are permitted, but must preserve the frozen engine contracts.

Work and push to ui-test only, never sandbox/master; no force push or automatic
merge of ongoing sandbox research. Test real PVE and UI lifecycle before delivery.
Final UI integration is a separately reviewed merge into sandbox, selecting UI
changes and resolving the branch-specific policy against the then-current engine.
Do not access other projects or publish user/private input, credentials or raw
account/Slack data. User instructions take precedence.
