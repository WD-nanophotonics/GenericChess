# Semantic capability input diagnostic

2026-10-08. This is an exposed development check of rule-only valuation inputs,
not a selected price formula or player-strength result.

## Observed interface gap

`build_ruleset_profile` derives generic-v1 static capability from movement atoms.
The execution adapter exposes retained legacy metadata; it does not reconstruct
semantic movement. Canonical Western P has no atoms, raw capability0 and the
clamped board value1. Its executable quiet/capture rules do exist. A longer
semantic capture and a capture-only variant retain exactly those old values.
Nonempty atoms can also differ from replaced/augmented semantic movement.
Correct legality therefore does not establish correct capability inputs.

This concerns the static component, not the whole default evaluator score.
Its promotion-zone construction also reads legacy empty-forward metadata:
canonical semantic P currently gets all64 squares classified as its zone.
The isolated input witness below zeros dynamic terms; it does not validate or
repair that separate dynamic approximation. Input-source repair should precede
piece-specific positional patches.

The existing unfamiliar-search report now states this input scope and lists
semantic moving types without atoms. That list detects a concrete omission;
an empty list does not certify complete semantic valuation. Frozen outputs,
evaluator defaults and earlier comparisons retain their original status.

## A bounded approximation that can see the change

The pilot projects simple actor moves, target removal and optional clear paths
from compiled IR, separating empty and enemy targets. Guards, auxiliary effects,
compound movement, drops, zones and postconditions are explicitly excluded;
own-anchor safety and future promotion/custody are ignored. Under the declared
independent occupancy law, empty probability is1-d and each ownership probability
is d/2. Path-clear unions are computed without double counting endpoints.
Promotion alternatives to the same endpoint are not extra current mobility.

| Predeclared variant | Quiet endpoints | Capture endpoints | Weighted projected mobility |
|---|---:|---:|---:|
| Canonical P |56|98|0.8501171875|
| Longer semantic capture |56|84|0.825234375|
| Capture-only |0|98|0.1741796875|
| Type-ID rename |56|98|0.8501171875|

Weights/densities are the existing generic-v1 configuration, retained as an
explicit development law, not asserted to be uniquely implied by the rules.
Capture-only mobility is zero at density0 and positive when enemies can occur.
Treating the union capture graph as empty-board quiet movement would fail this
basic distinction. Longer range need not increase this context-average measure:
finite-board boundaries reduce the number of its valid endpoints.

Independent Core checks cover both owner orientations,512 quiet contexts and
32256 single-enemy contexts. Another10240 fixed occupancy samples inspect the
density law and rename invariance. These synthetic pseudo contexts have no
anchors; they do not validate full-game legal mobility or material prices.
Reuse of the same samples exposes the omitted double-step, exclusively on rank1:
paired missing means are0.123046875 at density0 and0.03125 at0.5. Guards are thus
a measurable approximation issue, not a reason to keep semantic movement absent.

In these particular all-N-background contexts, the omitted double-step mean is
analytically (1-d)^2/8: one eligible source rank and two empty squares. This
explains the paired sample effect without a new sweep or a universal guard law.
The simple weighted proxy's pawn-normalized ratios are N5.473, B7.146, R10.493,
Q17.638, with Q/R1.681. These are opportunity ratios under this law, not selected
material coefficients. Seeing previously omitted movement is necessary input
repair; it does not establish that this mobility normalization is useful prices.

## Decision

Prioritize a scoped semantic capability input for a rule-only candidate, retaining
empty/enemy availability and explicit unsupported mechanics. Do not silently
replace generic-v1, normalize signed service into positive prices, or select
parameters for human-reference agreement. One next implementation check should
use the existing comparison entry with a semantic-only unfamiliar movement;
its purpose is sensitivity and cost, not universal optimality or Elo.

That first interface witness now runs on a predeclared six-piece recombination:
the otherwise atomless type has semantic rook movement. Its complete compiled
quiet/capture/path geometry matches the canonical rook in both orientations.
Only this type's board lookup is changed from1 to1435, using the projected
opportunity and unchanged legacy median scale; all other table entries, search
and dynamic-term switches stay fixed. This is a scoped input intervention,
not a new selected pricing formula. Both owners use the same corrected lookup.

Eight cold public calls atdepth1/2 agree with independent plain Core material
minimax and repeat exactly. Atdepth1 both controls choose the same capture.
Atdepth2 the baseline retains that zero-valued capture, whereas the input
candidate avoids it: the capture's own Core two-ply value changes from0 to-660.
The opponent can also capture a different knight, so the baseline observation
is a tie, not a certified strategic blunder. Both chosen root values remain0.
This demonstrates input sensitivity only, not improved playing strength, an
independent material reference or permission to adopt the candidate by outcome.

[Pell's original Metagamer paper](https://cdn.aaai.org/AAAI/1994/AAAI94-212.pdf)
constructs game-specific evaluation from rules and static analyses, separating
material mobility/reachability features from dynamic advisors. Its reported
static promotion advisor was not implemented. This is precedent for an explicit
approximation, not evidence for our formula or modern playing strength.
[Clune's general-game heuristic paper](https://cdn.aaai.org/AAAI/2007/AAAI07-180.pdf)
uses payoff, control, termination and feature stability; its sampling assumptions
do not identify universal material prices. Our projected density law is a local
construction, not a result of either paper.

Compact observations: data/semantic_capability_20261008.json. Exact producers,
failed initial rename comparison and complete records:
../archive/semantic_geometry_probe_20261008/. Archived code is on-demand evidence.
