# Task034 declaration
Reuse Task033580exact query traces; zero new attack queries. Reconstruct same compiled states to count selected rows, active groups, all source scans and original consumed binding prefix.
Question: how much row materialization could lazy rank merging avoid, separately from source scans and heap priming? Done when all falsequeries consume all rows and selected/consumed totals reconcile.
No intrinsic time, comparisons, memory totals or speed predictions from these work counts. Do not rerun caller/search cost.
