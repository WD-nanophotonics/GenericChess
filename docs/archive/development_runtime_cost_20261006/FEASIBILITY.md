# Mature material testbed, decision record

Pinned official Fairy-Stockfish revision9f778da667f6e07dae1e85d3e2ea204fc6dee94d;
acquisition.json binds official codeload URL, zip SHA256 and byte count.
Existing Zig0.16 provides a compiler; no package/model/settings installation.
The build and probe are not yet executed. Do not build concurrently with the
declared operational timing batch. Source/build failure is retained evidence.

One standard-Chess material leaf is the smallest next decision-changing test.
It reuses the24 exposed development positions and legality/UCI transport,
not a translation of all GenericChess rules. Full arbitrary-rule reuse remains
unestablished. YaneuraOu MATERIAL_LEVEL1 is another genuine material-evaluation
mode, but switching to Shogi first would add interface work and lose this exact
Chess comparison entry. Defer that alternative, not its entire research route.

Eval::evaluate receives a pure material override behind a dedicated build macro,
before classical/NNUE/shuffling terms. It omits King material and clamps outside
the tablebase range. Only the five normal Chess nonroyal types are supported by
this experimental hook; do not expose its binary as a generic variant player.
Upstream GPL license/AUTHORS and original source zip remain local alongside patch.

Corrected coupling audit: ordinary SEE in position.cpp2502/2506/2607,
capture ordering movepick.cpp136/152 and q-futility search.cpp1663 use PieceValue.
Variant pieceValueMg/Eg overrides produce EvalPieceValue/CapturePieceValue in
psqt.cpp290-303. CapturePieceValue is used for atomic/blast exchanges, not normal
Chess SEE. Ordinary search thresholds, nonPawnMaterial and original PieceValue
remain unchanged in this first experiment, common to all three leaf candidates.
That is a declared fixed-search development test, not a pure theory ranking or
evidence that mismatched SEE is optimal. No all-heuristics retuning prerequisite.

Verified shared-account advisor followup1791289384.758129 identifies internal
PawnEg208 versus UCI displayed100cp. Pinned uci.cpp/types.h/search.cpp independently
confirm it. Adopt one common internal scale208 per Pawn before any probe outcome,
round other model ratios consistently. Trace output expresses Pawn units, hence
static one-Pawn difference must give1.00 (100cp), for both side orientations.
This convention does not eliminate MG/EG126/208 or fixed-threshold mismatches.
Earlier proposed internal100 and local draft126 are superseded before execution,
not result-dependent tuning. No deep search is used to verify a static gauge.

Once build/static controls pass, three fixed models ×24positions at0.25sec,
Threads1/Hash16/clear hash, record every move/depth/node/time/finite answer match.
Same wall-time compares these configurations, not cross-engine node quality.
This tiny probe decides runnable feasibility and whether mature search can
produce useful differences; actual playing and robustness need later evidence.
No new protocol, advisor approval, worker or publication action.

Primary source: https://github.com/fairy-stockfish/Fairy-Stockfish/tree/9f778da667f6e07dae1e85d3e2ea204fc6dee94d/src
