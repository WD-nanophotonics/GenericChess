# Search backend attribution recovery

Only Agent-generated experiment sources/results and builtin rule manifests.
No Slack/account, credential, user input or external engine binary is included.

Extract `evidence.zip` to a project-local scratch directory first; member hashes
are in the data index. The archive keeps exact experiment bytes.

`d6-45s.json`, `aligned-d2.json` and `pilot.json` belong to the OLD Shogi
ac987c3f rule definition. `d6-source.py` also uses the old cshogi repetition
adapter. Never relabel them as the repaired Standard Shogi comparison.
`recover_old.py --verify-only` loads `frozen-rules.json` and audits the eight
old frontiers against the preserved adapter. Original bounded CLI arguments
otherwise run the old assay. The backend base is Git0175a769303f1feccd73fece15f7613dffe22391;
old runtime is also retained in `utility-runtime-source.py` for accounting scope.

`utility.json` uses `repaired-rules.json` and `utility-used-source.py`, with
runtime accounting from the base Git version. Its source hashes are exact.
The active bridge and later profile/primitive results use repaired Native
provider owner accounting. Different source/rule versions are explicit;
no cross-version delta is labelled a search speed gain.

One-off profile/primitive/mature scripts were run under
`.local_agent/search-attribution-20261010/`. To repeat them, copy the selected
script there (or adjust its declared ROOT), using the published active bridge.
External engine probes require the separately present binaries with hashes
recorded in their result; unavailable binaries are not silently substituted.
Do not rerun broad historical cohorts merely to update a current result.
All positions are exposed development controls, not renewed holdouts.

Data index: ../../research/data/search_attribution_20261010.json.
