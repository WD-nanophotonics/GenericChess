# Formal B2 — Bounded Evaluator Control

This is a runtime-suitability replacement for the aborted legacy full-game B protocol; it is not outcome-driven.

- Certified ruleset fingerprint: `5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345`
- Node budgets: LOW `256`, HIGH `512`
- Fixed-position corpus available: `10`; requested LOW 16 / HIGH 12; use all available if short
- Paired rollout horizon: `64` plies; LOW 6 openings / HIGH 4 openings
- Required lockstep: legal set, conversion, submit, normalized SFEN, side, check
- HORIZON_REACHED is not a draw and receives no W/L/D adjudication.
