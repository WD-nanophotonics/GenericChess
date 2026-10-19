# Exact duplicate legacy movement atom: profile, cache, and search probe

## Question

Does adding one exact duplicate legacy `RayAtom` change rule-derived prices,
public legal actions, or bounded AlphaBeta results enough to justify normalizing
the ruleset/compiler representation?

## Bounded comparison

`duplicate_atom_search_probe_20261020.py` constructs one 5x5 legacy ruleset
with two anchors and one north-ray R, then compares it with an otherwise
identical ruleset whose R declares that exact ray twice. The ruleset fingerprints
differ, so source identity is retained. The R movement signature is identical;
raw capability is `1.5710626627604165`, board value is 1000 and hand value 900
in both. Both roots have the same five unique visible legal actions.

One public AlphaBeta player per ruleset uses TT/order/root-tactical disabled,
qdepth0 and node caps 12, 16, 20, 24, 32 and 48. Across every cap the returned
action, score, completed depth, node count, stop reason and retained PV match
exactly. The comparison is deterministic and contains no timing measurement.

The public `EvaluationProfileCache` misses the first lookup for each distinct
fingerprint and hits on each exact repeat. The lower-level capability cache
already keys by canonical movement signature, while the full profile cache
keys by complete ruleset fingerprint. This preserves cache isolation by rule
identity; this probe does not justify changing that contract or deduplicating
serialized rule definitions. Instrumenting the reused capability cache showed
two total geometry builds (K and R) after both profiles, so the duplicate R
geometry did not trigger a second capability build even though the complete
profile was rebuilt under the distinct fingerprint.

## Decision and limits

No price, legal-action, or bounded-search difference was observed for this one
exact duplicated legacy ray, so no normalization/compiler change follows. The
existing profile tests also cover duplicate overlapping mobility targets, and
the standard generator explicitly deduplicates atoms in both symmetry modes
(`piece_generator._mirror_atoms`). A fixed audit of 128 generator configurations
(board sizes4/8, both symmetry modes, hybrid on/off, seeds0–15) found zero
duplicate atom tuples across640 generated piece types. The two focused existing
tests for overlapping-target mobility and cross-ruleset capability reuse also
pass.

This does not cover duplicate leaps, different atoms with overlapping targets,
semantic bindings/guards/effects, larger generated distributions, cache pressure,
or runtime overhead. It makes no utility, broad-domain equivalence, or
performance claim. Revisit only for a real caller or material duplicate-heavy
input whose measured cost can change a specific implementation choice.

Exact output: `data/duplicate_atom_search_probe_20261020.json`.
Reproduce with:

```powershell
.\.venv\Scripts\python.exe docs/research/duplicate_atom_search_probe_20261020.py
```
