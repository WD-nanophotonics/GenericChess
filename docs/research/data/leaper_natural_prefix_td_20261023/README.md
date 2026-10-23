# Saved natural-prefix learner evidence

`pilot.json.gz`: four TRAIN episodes per rule,16 TRAIN/48 EVAL games.
`budget.json.gz`: NEW64-episode seed streams,256 TRAIN/16 EVAL games.
`extras.json.gz`:16 directional queries,one negative first-action control,
four child-score queries and96 committed5x5 target returns,zero5x5 games.
All337 NEW physical games reach actual rule terminals. Old free/TD4 controls
are exact reuse, never extra games. Complete rules, histories, literal targets,
paid returns, failures/UNKNOWN fields, original fixed slots and limits remain.

The executed infrastructure basis is sandbox1ac1f97a74b26015ffb73dcb612333923a6d61d0;
closing8f1f9e5f977e1baba0e5a3cd14d74b7ea0351130 adds no shared runtime change.
The existing source packet at `../leaper_tie_truth_20261023/strongfoe-source.json.gz`
is required by the full readers for source-world binding, without another copy.
The primary5x5 typed source is bound to its fixed1ac SHA/hash; its complete
consumed worlds are retained in extras for local replay.

From repository root, with the normal project Python environment:

```
python scripts/verify_leaper_prior_td.py docs/research/data/leaper_natural_prefix_td_20261023/pilot.json.gz
python scripts/verify_leaper_prior_td.py docs/research/data/leaper_natural_prefix_td_20261023/budget.json.gz
python scripts/verify_leaper_td_extras.py docs/research/data/leaper_natural_prefix_td_20261023
python scripts/compare_leaper_td_budget.py docs/research/data/leaper_natural_prefix_td_20261023/pilot.json.gz docs/research/data/leaper_natural_prefix_td_20261023/budget.json.gz
```

Readers replay Core paths and backward TD arithmetic; they perform no new
search/training. They are semantic consistency checks, not independent WDL
oracles. Producers are ordinary files under `scripts/`; running them costs
NEW computation and must not overwrite/refill the closed cohorts. The report
states the exposed-rule, fixed-opponent and distinct-TRAIN-stream limitations.
No fitness/default/generator result is claimed by this AUX learner study.
