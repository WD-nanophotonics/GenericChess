# Exact action history in consecutive-action search caches

Two complete legal histories can reach the same board/side, ply, repetition
counts, actors and check responsibility by passing or taking a semantic board
no-op. Under two-consecutive-pass adjudication, the next pass draws on one path
and continues on the other. The previous runtime TT key omitted that distinction.

An actual public D1/q0 query with a controlled constant7 leaf reproduces the
wrong reuse: pinned0ad6647e returns0 on a warm second history versus-7 cold.
The repaired query returns-7 in both cases. This is a cache correctness witness,
not a playing-strength/evaluation-quality result.

For consecutive-action rules, the existing persistent history context now
retains the already computed action signature, hashes it and compares exact
bytes after digest equality. Import, push and pop retain it. The owned public
SearchStateIdentity also includes the full action-history tuple for these rules.
The search applies its verified-history TT eligibility guard to this policy.
Plain rules retain empty action signatures and the previous digest/key behavior.
No public position/repetition SHA, Native ABI, engine default or UI policy changes.
Existing unsupported no-progress-search rejection is preserved.

Five regressions cover complete legal histories/future draws, actual public
warm/cold decisions, forced digest collisions and plain-rule reuse. Related100
checks pass; final2,319 active tests pass with zero failure/error/skip. The first
full validation had2,195 passes and124 setup errors scanning pytest's default
temporary root (WinError5). A fresh project-owned basetemp passes the same failed
fixture and the full rerun; original raw failure/XML is retained privately.
No system permission/security change or user intervention was needed.

Private transport/algorithm resource producers imported0ad before this repair;
their frozen timings are not measurements of this later Python fix. Detailed
source/failure/old-current probes will be bound in CORE_CHECK_TRANSPORT.md and its
Agent-only archive once the remaining declared research producer closes.

Later fixed-source Dot review confirms the conditional signature retains the
information read by consecutive-action adjudication; it does not independently
execute our tests. The supported provenance is trusted Core/session witnesses
or successful public-history replay, not arbitrary forged supplied witnesses.
The same pair without supplied witnesses reconstructs with0 misses/2 key calls
per history, keeps distinct keys and prevents cross-history table hits. Detailed
closed resource and source evidence: CORE_CHECK_TRANSPORT.md.
