# Fresh-process cost observations

Three isolated processes completed with external elapsed62.63,50.88,46.83ms.
These include interpreter/parent overhead48.73,41.05,35.58ms. Child imports
8.89-12.88ms, qualified record read/direct-pin checks0.72-0.80ms, CDF
validation63-67us, two arithmetic operations152-159us. Whole parent0.156sec,
no retry, game/graph/source event or model. OS caches were NOT flushed, so
these are fresh-interpreter observations, not cold-disk or tail guarantees.

Earlier arithmetic-only field misleadingly named total_import_and_validation
is now supplemented by an honest external process measurement. Original
raw remains unchanged. This confirms the small research interface itself is
cheap once qualified counts exist. It says nothing about deriving counts
from a new ruleset, acquiring author data, full H qualification or production
score/TT integration. Those preprocessing/scope costs remain explicit.
