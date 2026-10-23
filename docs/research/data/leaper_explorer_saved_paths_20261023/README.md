# Saved-history truth packet

Same369records/34037histories,rules and original mu identifiers. Parent packets
leaper_explorer_truth_20261023 and leaper_explorer_followup_20261023 stay intact.
No E0,baseline,Player game,training example,new rule or holdout is supplied.

```powershell
.\.venv\Scripts\python.exe -m scripts.verify_leaper_saved_paths --output .local_agent/saved-path-reader.json
```

The default reader checks both parents,all new complete successor rows,the
recorded-edge diagnostic,all positive literal paths,loop-removal provenance,
actual repetition barriers and final target/episode views. Optional
--skip-parents / --skip-diagnostics explicitly omit those earlier/negative
diagnostic checks;they do not strengthen any scientific claim.

Load current truth with scripts.leaper_saved_child_bounds.current_truth(parent,
followup),then propagate(truth,edges),saved_suffix_transfer.apply with
shortened-proofs,and observed_path_proofs.apply with observed-proofs. Verify
incoming packets first. Each layer binds its exact input digest. The final
digest is d129e9a87929502a19b4758a53ff4eec2084c6bb0e6e11700cc50998d374f333.

- edges/changes/summary:2271complete successor rows,14407edges;81new exact WDL.
- recorded-edges/path-*:bidirectional max-interval diagnostic,zero new bounds.
- identity-feasibility:Core identity measurement;capture-pruned keys are not adopted.
- suffix-proposals/proofs:165original mate-suffix proposals,160literal positives.
- shortened-proofs:separate loop-deletion method,same165inputs,161positives.
- barriers:five raw repetition failures,two terminal-history groups;one rescued
  by shortening,the other four remainUNKNOWN.
- observed-proposals/proofs:shortest paths in the incomplete union of recorded
  transitions;474proposals,311positives,163UNKNOWN. No negative inference.
- final-*:31889exact WDL;fork1932TRUE/29901FALSE/2204UNKNOWN;cooperation5443TRUE/
  24780FALSE/3814UNKNOWN. Initial cooperation9TRUE1FALSE;initial fork9UNKNOWN.
- pending-e0:actual missing-input contract,not synthetic predictions or zero error.
- source-qualification and plans:fixed sources,budgets,execution and scope limits.

Component costs exclude some loading/serialization and all engineering. The
shortened method also reconstructs source suffixes;fewer target actions do not
establish end-to-end or learner speed. All controls are exposed and correlated.
Original100k/1m/900s/50kcap failures remain closed,not continued by these methods.

Report:../../LEAPER_SAVED_HISTORY_PATH_TRUTH_20261023.md.
