# DEV_AUX task2607 — exact full-history root feasibility

## Frozen question and method

Before any additional evaluation, can a deterministic outcome-blind scan find at least 16 unique valid four-ply Generic-rule start records per rule that are exactly disjoint from all 512 possible four-ply task2606 training-family roots? Identity is the canonical complete `GameSession` record, including ruleset fingerprint and all ordered actions. The frozen scan considered family IDs 991000–992023 in ascending order, selected the first 16 accepted roots per rule, and had a no-expansion shortage rule. No training, model fitting, or outcomes were used.

## Result

The feasibility audit passed for all four rules. Selected roots: 271001 (families 991002, 991006, 991007, 991008, 991011, 991012, 991013, 991020, 991024, 991027, 991028, 991031, 991032, 991034, 991040, 991052); 271002 (991000, 991001, 991002, 991007, 991012, 991015, 991016, 991018, 991019, 991021, 991023, 991024, 991027, 991030, 991033, 991034); 271003 (991000, 991003, 991005, 991006, 991009, 991012, 991015, 991016, 991018, 991020, 991022, 991023, 991024, 991025, 991027, 991028); 271004 (991000, 991001, 991004, 991005, 991008, 991011, 991017, 991019, 991022, 991028, 991032, 991033, 991034, 991037, 991039, 991042).

For each rule, 1,024 candidate IDs were classified. Exact training-root overlaps, terminal/short prefixes, and evaluation duplicates were rejected in frozen precedence order. There were 295, 104, 130, and 150 duplicate training records in rules 271001–271004 respectively; the number of unique valid training records was 196, 372, 381, and 311. All four rules returned the required 16 roots without changing the scan range or criteria.

## Scope

This proves finite sampler feasibility and exact start-record disjointness for the selected panel only. It is not an outcome estimate, trained result, descendant-state disjointness claim, or population/generalization guarantee. Task2609 subsequently used these outcome-blind roots for a fixed-model evaluation; its limitations and outcomes are reported separately.
