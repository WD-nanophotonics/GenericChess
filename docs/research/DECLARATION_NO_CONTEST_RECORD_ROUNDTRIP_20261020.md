# Declaration outcome record round-trip — 2026-10-20

## Question and reproduction

Can every declaration outcome accepted by the generic rule schema survive the
public game-record save/restore boundary? `DECLARATION_OUTCOMES` includes
`WIN`, `RESTART`, `NO_CONTEST` and `LOSS`. `GameSession.declare` stored a valid
`NO_CONTEST` assessment, and `serialize_game_record` emitted it, but
`deserialize_game_record` had a separate three-value allowlist. The exact
production-session reproduction failed on read with:

`[INVALID_OUTCOME] game_record.declaration.outcome: outcome must be WIN, RESTART or LOSS`

The session result was a declaration with winner `None`; the defect was loss of
a valid saved record at deserialization, not the declaration assessment.

## Correction and verification

The record reader now validates against the shared `DECLARATION_OUTCOMES`
constant instead of maintaining a narrower copy. No record schema version,
writer output or past artifact was changed. A product regression serializes,
deserializes and replays one authoritative session record for each of the four
outcomes, then checks the result, winner, unchanged state and record equality.
All four cases pass in
`tests/product/test_no_contest_search.py::test_declaration_outcomes_roundtrip_game_record_and_session`.
A real `play_game` integration regression separately confirms `RESTART` and
`NO_CONTEST` declarations stay unresolved in benchmark accounting; neither is
reclassified as a rule draw or as a failed game.

This restores persistence for an existing supported ruleset outcome; it does
not change search values, game outcomes, WDL classification or price estimates.
The prior failing reproduction and passing test output are preserved privately
under the ignored PRIMARY `.local_agent/research/no-contest-record-contract-20261020/`.
