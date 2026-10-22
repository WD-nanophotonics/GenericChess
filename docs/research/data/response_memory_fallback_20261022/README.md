# Response memory and fallback evidence — 2026-10-22

Read [the report](../../SEARCH_RESPONSE_MEMORY_AND_FALLBACK_20261022.md) and
[summary.json](summary.json) first. [measurements.zip](measurements.zip) contains
full technical inputs, query returns, histories, outcomes, all masks, failed
instrumentation, actual thin producers and next inputs. [manifest.json](manifest.json)
records every member and private-original/public-copy hash. JSON formatting is
compact and private absolute workspace paths are replaced in publication copies;
exact originals remain private. No original research outcome was redacted.

Reproduce measurements on sandbox parent `60e1b23c87002f81f19994bd68f9ffa20437a57b`
with the separately committed countermove CLI switch. Sources use the existing
Core/search/runner; execute only fresh output paths under their declared caps.
MTD and aux-frontier changes are isolated process prototypes, not product features.
The old no-scan canonical fallback assertion and product source stay unchanged.
`sources/attempted-product.patch` is evidence of a REJECTED migration, not a
patch to deploy. Partial-policy ordinary runner masks remain alongside the
separately preregistered intentional-fallback task masks; do not interchange them.
The next evaluator C/D games are NOT RUN. Their full inputs/profiles are present.

Sources are stored once, normalized UTF-8/LF with original-byte hashes retained.
The measured CLI used CRLF; `counter-20261022/line-endings.json` records both
measured and canonical hashes. No source change was concealed by an old hash.
