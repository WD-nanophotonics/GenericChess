# Full technical evidence — structural Leaper portraits

Four gzip JSON packets retain complete RuleSets, profiles, initial and final
histories, actual controller returns, all planned slots, costs and source versions.
Each `*-manifest.json` gives compressed/decoded hashes. Each
`*-qualification.json` verifies its ACTUAL exported games through shared Core.
`qualification-summary.json` independently binds exports to original SHA/values.

| Packet | Planned/retained | Controller returns | Full PV edges | FLOOR choices |
| --- | ---: | ---: | ---: | ---: |
| depth.json.gz | 588 | 15,220 | 35,620 | 0 |
| price.json.gz | 960 | 21,306 | 59,836 | 4,409 |
| material.json.gz | 384 | 10,065 | 29,642 | 0 |
| quantity.json.gz | 192 | 3,267 | 10,851 | 632 |

All 2,124 records complete with zero UNKNOWN; 292 are terminal starts and 1,832
have actual continuation. The 1,015 distinct literal records are not IID samples.
There are 110 current NEW cost returns plus 12 NEW next-design costs = 122.
Sixteen old layout costs remain OLD; eight common-foe costs are exact parent
reuses. `next-design-review.json` links the complete 48 inputs, costs and inert source
in `next-design-data.json.gz`, with exact compressed/decoded hashes;
its 192 prospective fitness games are **NOT RUN**.

Source capsules are inert strings with byte hashes. Never automatically unpack
or execute them. The library basis is sandbox commit
`efac79080ba6eb2b8219e325e9779dcb1a47abbb`; no product/default code is changed.
The reader uses production Core, not an independent solver or WDL oracle:

```
python -m scripts.leaper_portrait --packet docs/research/data/leaper_structural_portrait_20261023/depth.json.gz
```

Repeat the command with the other three packet filenames to inspect them.
Private Chat originals, account information, session ledgers and credentials are
excluded. Producer/preparer failure evidence is technical and explicitly scoped.
The pure-Leap/remove prototype does not redefine the full generated target,
which retains promotions, drops, auxiliary state and relevant history.
