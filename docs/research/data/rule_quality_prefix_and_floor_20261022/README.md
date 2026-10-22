# Rule-quality prefix and competence evidence

This compact technical capsule accompanies
[the report](../../RULE_QUALITY_FLOOR_AND_PRICE_CONTROLS_20261022.md).
It contains 2,270 selected technical members plus `PROVENANCE.json`, including
complete rules, canonical full histories, observed child/terminal witnesses,
176 actual new match games, 2,064 Player returns, 2,008 FLOOR turns, qualifications,
and the 12 prepared next inputs. It includes four exact public prerequisite
copies from the preceding fixed capsule; it does not repeat that whole archive.

`summary.json` is directly readable. `manifest.json` gives the archive hash and
size. Per-member original/public SHA256 identities and transformations are inside
`PROVENANCE.json`. Large aggregate copies of repeated full states are replaced
with exact receipt indexes; unique full records remain. File-byte references
are translated to public copies; rule/action/state identities remain intact.
Private exact originals and failures remain in ignored `.local_agent`.
No raw Chat/account outputs, credentials, test logs or source-tree dump is included.

Run from the repository root with its supported Python environment:

```
python docs/research/data/rule_quality_prefix_and_floor_20261022/verify.py
```

The reader accesses the ZIP directly, checks every member hash, strictly parses
canonical records and replays the public technical copies using maintained Core.
It checks all old dense parent frames, new match histories/PVs, counterfactual
records, early resource witnesses and next inputs. It writes only an ignored
local qualification receipt. This is shared-Core replay, not a second rules
engine, a new search-strength test or a clean-checkout execution claim.

Analysis harnesses are included for inspection. Indexed counterfactual aggregates
must be regenerated from their primitive inputs before running a driver that
expects duplicate embedded full states; the verifier resolves the indexes
without regenerating or extending any fitness panel. The common-tail policy
summary is explicitly conditional; `policy-distinct-bounds.json` is the corrected
continuing-policy sensitivity. Raw UNKNOWN is never replaced by a draw.
