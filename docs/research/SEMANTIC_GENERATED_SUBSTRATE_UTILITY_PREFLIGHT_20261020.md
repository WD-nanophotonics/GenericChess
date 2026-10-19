# Generated compound-profile utility preflight — 2026-10-20

## Question

Does recombining a compound `move_and_shift_adjacent_friendly` action onto `P`
produce an exposed profile contrast on a reachable generated-rule root, with a
finite-search difference that would justify a utility panel?

## Fixed protocol and evidence

The original pinned seed-21 substrate (`a3807253…`) contains types K/P/X/A but
starts with no P. Its compiled synthetic recombination changes P board/hand
profile values (135/122 to 404/364), yet the fixed 32-prefix-seed block has 20
eligible ongoing 12-ply roots and none contains P on board or in hand; none has
a legal semantic action and candidate/control root evaluation is identical.
The proposed 16-game panel on that substrate has no exposure to its profile
contrast and was not run.

A separate fresh fixed generator block 202610301–202610320 produced 20 rules,
15 with P in the initial setup. The first four eligible P-start seeds (301–304)
were selected by seed order, not by profile or search results. Each received a
fixed legal 12-ply prefix with prefix RNG seed `generator_seed + 900000`. All
four roots remained ongoing with P on board/hand, but had zero legal compound
semantic actions. Public AlphaBeta D2 was run under equal 4096-node ceilings,
TT/order/root-tactical/qsearch disabled, changing only candidate versus legacy
profile reconstruction. All eight calls completed D2 with paired node counts
126, 35, 46, and 27; each pair selected the same action and PV. Three score
pairs shifted, while seed 304 was identical. No games or training were run.

The default profile projects eligible direct movement geometry into atoms and
does not model a compound companion shift. The result therefore confirms only
a scoped geometry-only input sensitivity. It does not show that the price change
improves utility, that compound actions are mispriced generally, or that the
current profile bridge is incorrect.

## Decision

Close this proposed utility panel without games. The original seed21 setup is
unexposed; the fresh four-root check shows score sensitivity but no action/PV
change and no legal compound action. Do not expand seeds or substitute roots
post hoc. No code/default change follows. Retain the existing semantic geometry
profile as a correctness-oriented candidate and preserve the legacy profile as
a control.

Reproducers and machine-readable records:

- `semantic_generated_substrate_exposure_audit_20261020.py`
- `data/semantic_generated_substrate_exposure_audit_20261020.json`
- `semantic_generated_substrate_utility_preflight_20261020.py`
- `data/semantic_generated_substrate_utility_preflight_20261020.json`

The broader semantic search gap map is old and contains historical open labels;
current `LOCAL_MAINLINE.md` closes most of those search-interface checks. Any next
search work must be selected against current callers and current mainline
closures, not by reviving a historical heading.
