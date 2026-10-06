# Prospective source-adjudicated first-quiet exchange

Frozen before this new population is sampled, 2026-10-06. Development task,
not natural-game performance or a repair of the closed128-proposal pilot.
Question: can complete actual recapture information beyond a fixed depth1
controller be retained together with independent automatic draws affordably?

Native board K/R(owner0), K/N/B(owner1), actor0, empty hands, no promoted
origins/castling/EP, fresh history. SHA256 string seed
`GenericChess/adjudicated-exchange/v1/proposal/{i}/{label}` determines each
choice modulo ordered options. King0 uniformly indexed among central c3-f6
squares, N then B among its eight adjacent squares without replacement;
King1 among corners without replacement; R among remaining squares. This is
a conditional construction, NOT uniform over positions or reachable games.
Indices0..119, new seed, no more proposals after failure. Previous actor
must not be checked; current actor may or may not be checked. Complete local
root table must include captures of both N/B and at least one quiet action.

Before compiling candidate root actions, a candidate-blind geometric filter
asks whether either remaining minor could nominally attack R after the own
King captures the other adjacent minor. This is raw occupancy/attack geometry,
NOT a legal capture, successor materialization, source probe or outcome label.
Knight uses its eight offsets; Bishop requires diagonal line with intermediate
squares empty after that nominal occupancy change. No price/selection/gain
filter. Reserve at most240 nominal checks and1680 scanned intermediate
squares; count actual work. First eligible local root is irrevocable; author
invalidity/disagreement or information failure closes the run, not substitution.

Compile once. Public transitions128, returned action entries plus complete
membership-list charge5000,120 proposals,30sec cooperative WHOLE clock
including pinned-author replay, no tables/downloads. Root K/R actions<=22;
at most4 ordinary captures; each defender K+minor has<=21 actions. Thus
106 selected transitions, with total enumeration bound4972 if120 proposal
lists each<=22. Source separately reserves128 pushes/5000 legal entries under
the same30sec clock. All counters include failures; no private successors.
Full states and actual native terminal cache retained, never patched.

Pinned python-chess1.11.2/manifest from ADJUDICATED_FIRST_QUIET_ADMISSION.md
checks root/ALL children actor, board, rights, stack length, legal action
multiplicity and automatic outcome. Its true terminal wins over first-quiet
stopping. Local ongoing versus author INSUFFICIENT_MATERIAL is recorded as
an explicit contract difference, accepted only for King versus King+minor
after sole R removal. CHECKMATE/STALEMATE/winner must otherwise agree. No
draw suppression; claim_draw=False still retains automatic insufficient draw.

Materialize ALL root children, score them before defender successors. Existing
exact geometric_half/linear_mixture Chess contact formulas; unit1/zero0
baselines, depth1/q0, owner0, King excluded, divide inventory by31, terminal
goal scored separately, canonical smallest string tie plus COMPLETE tie set.
Write immutable `.selections.json` BEFORE ANY enemy successor/label. Independent
root-child terminal checks happen before scoring because they define its goal
contract; they cannot be used to replace the root. Record source qualification
and chronology explicitly. No later controller after a recapture: automatic
insufficient draw ends it. Every nonterminal quiet ends the task, ordinary
capture continues to ALL enemy actions. Noncapture after root ends at ply1;
defender quiet ends at ply2, recapture source draw at ply2. No deeper events.

Each leaf retains actual local state, source outcome, path and class: true
source Win/Draw/Loss or ongoing first-quiet five-mode P/N/B/R/Q signed inventory
vector, with full path incidence. Quiet is NOT a true goal draw. Compare only
complete sets of same classes with existing sufficient unweighted set order;
mixed true terminals/quiet default UNKNOWN. Report all policies/canonical/full
ties and actual future information, even zero gain/incomparability. No WDL
strength, automatic calibration, unique context law or human-value inference.

No retries or output overwrite; preserve failed old pilot and new failure.
