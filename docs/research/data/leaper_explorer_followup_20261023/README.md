# Separate AUX explorer truth layers

Parent input:`../leaper_explorer_truth_20261023`. It remains unchanged.
No E0or baseline forecasts are included. The controls are already exposed.

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m scripts.verify_leaper_explorer_followup --output .local_agent/explorer-followup-reader.json
```

The reader checks manifest bytes,the original portable packet,colour proof and
new exact action bindings,the complete finite suffix root,and all changed local
one-ply rows through actual Core. It reconstructs the same truth layers,initial
view,rule targets and episode UNKNOWN bounds. `--skip-original` skips only the
already checked parent reader;it does not skip new proofs. No local graph pickle,
new game,learner or network is needed.

- `colour-certificate.json`:78escape pairs,global colour invariant,parsed rule
  and full-source binding. Adds372DRAW labels;the rule's original initial
  history has no cooperative decisive continuation.
- `supplement.json.gz`:372invariant rows/2013exact action bindings plus one
  literal cooperative mate path. Source-bound and separate from old UNKNOWNs.
- `local-layer.json.gz`:126changed histories from the complete2275-target
  one-ply pass;46WINs,29[0,1]bounds,51singleton fork-FALSE,4fork-TRUE. Ongoing
  children remain UNKNOWN. Independent changed-row check:741edges/86terminal
  action labels;full producer pass:14454edges/49.325s.
- `summary.json`,`rule-targets.json`:final31808exact WDL/2229nonexact;
  4627cooperative TRUE/24778FALSE/4632UNKNOWN. No source mu is silently changed.
- `initial-view.json.gz`:a PROPOSED evaluation view of the same ten original
  initial histories. Cooperation9TRUE/1FALSE,fork9UNKNOWN/1FALSE. Its new mu IDs
  are required for predictions on that support. PRIMARY still freezes the
  actual prediction target;this is no new layout or blind holdout.
- `episode-exposure.json.gz`:369records have148fork-TRUE/36FALSE/185UNKNOWN;
  positive first-event times remain unknown because of unresolved prefixes.
- `sampling-*.json`:shared-label,finite-support differences between sampling
  laws. Unit-independent-label query counts are interval-width abstractions,
  not solver-time estimates or instructions to launch queries.
- `initial-path-*`,`suffix-*`,`*-entry-failure.json`:failed/capped attempts and
  their actual costs,not refilled slots. The suffix batch remains1complete,
  1partial,22unstarted. The complete root has an8-edge mate exactly at clock128.
- `source-qualification.json`:fixed shared/parent sources,post-execution source
  qualifications,constructed-test scope and absence of new Player/training work.

To obtain the full current truth object in Python:

```python
from pathlib import Path
from scripts.leaper_explorer_truth import load, materialize
from scripts.leaper_explorer_supplement import apply_supplement
from scripts.leaper_local_truth import apply_layer
p = Path('docs/research/data/leaper_explorer_truth_20261023')
q = Path('docs/research/data/leaper_explorer_followup_20261023')
t = materialize(load(p/'truth.json.gz'), load(p/'cooperative.json'),
                load(p/'observed-suffixes.json.gz'))
t = apply_supplement(t, load(q/'supplement.json.gz'))
t = apply_layer(t, load(q/'local-layer.json.gz'))
```

Run the portable reader before trusting incoming layers. These pure application
functions join checked evidence;they are not substitutes for the proof checkers.

Actual frozen PRIMARY forecasts can use the maintained history format described
by the parent README,or `leaper-rule-prevalence-predictions-v1`. The latter rows
name `fingerprint`,`mu_id`,`property`,`probability`,full40hex `source_sha`and
numeric actual `cost`. Both paired comparison inputs also declare a `freeze`
object with `forecast_id`,`information_set`,`frozen_at`,`truth_access`;these are
provenance declarations,not independent proof of blinding. Property names are
`wdl_fork`,`cooperative_decisive`,`universal_draw`. Rule-level prevalence is not
existence over arbitrary legal histories/layouts. No missing forecast becomes.5.

Use `scripts.leaper_explorer_compare.compare` for paired history predictions,
or `scripts.leaper_rule_forecast_score.score_rules` for rule-prevalence forecasts.
The original initial view can be passed to either appropriate scorer,using its
own mu IDs. Known-only Brier/skill is conditional on shared coverage;zero baseline
loss has undefined skill. UNKNOWN completions,unpaired support and equal-rule
weights stay explicit. Small exposed samples do not establish population
calibration or unseen-rule generalization. No actual E0FP/FN has been measured.
