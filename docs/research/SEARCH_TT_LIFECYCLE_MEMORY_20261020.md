# AlphaBeta transposition-table lifecycle and history memory probes — 2026-10-20

## Decision question

Does the current persistent `AlphaBetaPlayer` table show enough entry or memory
pressure on bounded generated-rule matches to justify changing the default
250,000-entry capacity?

## Evidence

At the reviewed source base `b94526790449937b840142259ae94339715852b8`, the UI
owns one `AlphaBetaPlayer` for a match. A new root search advances the TT
generation; loading a different ruleset or changing q-depth semantics clears it.
When full, the table evicts half of older-generation entries, or one quarter of
current-generation entries if all are current. Existing capacity coverage uses
a five-entry table and checks the entry bound.

A single 8x8 bilateral-random hybrid generated rule (seed 21,
fingerprint `64e773602de8f5eeb10c1f26e311a7018578cfded4345d44a24ed65a38749b7e`,
`max_ply=512`) was played with one reused player and the Balanced fixed-node
configuration (50,000 total nodes, q-depth 4). The durable log contains 14
completed, legal plies: TT occupancy 8,712/250,000 (3.48%), current traced
memory 14,823,691 bytes above baseline (traced current 14,884,266 bytes), and
50,000 nodes on each call. It
includes generated promotion and drop actions. The registered 20-ply/45-minute
run has no terminal footer; the process is no longer present, and the reason it
stopped is unknown. This is a partial prefix, not a completed 20-ply result.

A separate completed run adds `RuleNoProgressDraw(100, reset_on_capture=True)`
to the same generated seed and uses 256 nodes per search, q-depth 0. One player
submitted 100 legal plies; the game remained ongoing with 101 history records.
At ply 100 the TT held 2,539/250,000 entries (1.02%); traced current memory was
7,120,405 bytes above the pre-search baseline and peak was 7,528,504 bytes.
The run took 63.686 seconds. This exercises the full ActionRecord-history key
path, but is a low-node probe, not the Balanced configuration.

The source identity audit confirms that rules with `no_progress_draw` or
consecutive-action adjudication include the full ActionRecord-derived history
in each `SearchStateIdentity`; other rules use their applicable repetition and
adjudication context. A synthetic TT layout probe (4,356 entries) measured 377,
2,529, and 14,912.5 traced bytes per entry for 0, 14, and 100 repeated history
records. This is representation sensitivity from constructed keys, not actual
search memory or a basis for linear extrapolation to 250,000 entries.

Private per-ply source records are retained under `.local_agent` and are not
part of this public report.

## Decision and limits

Neither real sample approached the entry cap, and neither demonstrates a
production defect. Keep the default capacity and eviction policy unchanged.
The Balanced run is incomplete and lacks no-progress history; the long-history
run uses a much smaller search budget and only one generated rule. Do not infer
full-match or worst-case memory safety, cap lifetime, playing strength, or
cross-rule behavior. Revisit only if a representative long-history run at a
required production budget shows material memory pressure or a concrete caller
requires a byte-budget guarantee.
