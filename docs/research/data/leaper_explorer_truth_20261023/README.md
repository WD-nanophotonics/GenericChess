# AUX explorer truth handoff

No E0 predictions are included. `pending-e0.json` is a missing-input record,
not a zero-error score. All rule families and old labels are exposed.

## Read and verify

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m scripts.verify_leaper_explorer_truth --output .local_agent/explorer-reader.json
```

This checks file hashes; replays369complete records/35648actions; binds all
34037complete histories,146126legal-action labels and53728reference visits;
checks2650observed mate suffixes; verifies24new cooperative paths and one
negative distance-potential certificate; independently enumerates91712H6
histories, exact policy leaf masses and occupation-law statistics. Imported
31390minimax labels are NOT all independently re-solved by this reader.

The finite3x3 rule and all288setup definitions are inside the packets. Public
readers require no ignored graph pickle or old producer directory. The original
producer scripts used historical local caches; their sources/receipts remain
explicit rather than claiming every raw graph is serialized here.

## Contents and counting units

- `truth.json.gz`: ten4x4canonical rules,369full records,34037unique ongoing
  histories and31390scoped legacy WDL/action labels;2647WDL UNKNOWN.
- `source-context.json.gz`: original PRIMARY policies, seeds, roles, caller
  protocols and costs.540record references are not540independent trajectories.
- `observed-suffixes.json.gz`:2650existential mate witnesses implicit in the old
  complete records, including598histories whose minimax WDL is still UNKNOWN.
- `original-cooperative.json`, `original-executed.py`, `original-verification.json`:
  immutable900s full-graph-preaudit batch,22/25complete,3UNKNOWN.
- `cooperative.json`, `negative-certificates.json.gz`, `cooperative-verification.json`:
  separate certificate-first method on the SAME25inputs,24literal mate paths
  (155edges) and one all-future-DRAW potential. No graph expansion/cap refill.
- `cost-control*.json*`: actual32.09s end-to-end control, original failure and
  method/source qualifications. This is AUX truth validation, not learner speed.
- `mechanisms.json.gz`:10finite observed Position returns with cooperative
  exits;240guarantee-lowering record-actions/229different histories, including
  12closed-structural-DRAW and4actual-terminal-DRAW children.98observed eventual
  results outperform the lowered guarantee. These are correlated diagnostics.
- `finite-outcomes.json.gz`, `finite-occupation.json.gz`, `finite-verification.json`:
  separate old homogeneous3x3/H6/repeat2 control. All288layouts are fully solved;
  exact uniform-legal-action probabilities differ from minimax and from other
  history sampling laws. This is one additional exposed mechanism family.
- `critical.json`: one new independent Session proof attempt stopped at50000
  nodes/UNKNOWN. Its graph label is separate; no successful certificate claimed.
- `rule-targets.json`: conservative property-prevalence bounds under the named
  retrospective within-rule uniform-history mu. Not opening or population truth.
- `freeze.json`: original ten-family6/4exposed partition and original caps.

## Minimal E0 contract

The current scorer accepts binary property probabilities at an exact history:

`format=leaper-explorer-predictions-v1`, `predictions=[...]`. Each row names
`id` (complete-history hash), `fingerprint`, `mu_id`, `property` (one of
`wdl_fork`, `cooperative_decisive`, `universal_draw`), `probability` in[0,1],
full40hex `source_sha`, and actual numeric `cost` (nodes/time).
Declare the frozen feature information set and prediction revision separately.
A claim that a rule has ANY deadzone is not a prevalence prediction under mu.

After actual PRIMARY predictions exist:

```powershell
.\.venv\Scripts\python.exe -m scripts.leaper_explorer_truth score --truth docs/research/data/leaper_explorer_truth_20261023/truth.json.gz --cooperative docs/research/data/leaper_explorer_truth_20261023/cooperative.json --observed docs/research/data/leaper_explorer_truth_20261023/observed-suffixes.json.gz --predictions PATH_TO_REAL_FROZEN_E0.json --output .local_agent/e0-score.json
```

Wrong rule/history/mu joins and duplicate predictions reject. Known-only Brier
is conditional on coverage. Whole-denominator bounds retain missing labels and
abstentions; equal-rule macro bounds accompany pooled-history scores. Fixed
confidence thresholds report descriptive risk/coverage bounds. No IID confidence,
blind generalization, E0 false positive/negative or strength gain follows here.

Rules/Core/history source: committed sandbox8f1f9e5f977e1baba0e5a3cd14d74b7ea0351130
(shared code unchanged from1ac1f97a). Original canonical data source:e8f4abf94.
The H6 rule is from the earlier6ea35571foundation, executed here through current
shared Core. See ../../LEAPER_EXPLORER_TRUTH_CALIBRATION_20261023.md.
