"""Cheap regression contracts for the F94-R5 Western termination audit."""

from generic_chess import build_western_chess_ruleset, compile_ruleset_for_execution


def test_western_termination_contract_is_bounded_and_has_no_extra_adjudications():
    ruleset = build_western_chess_ruleset()
    compiled = compile_ruleset_for_execution(ruleset)

    assert ruleset.repetition_limit == 100_000
    assert ruleset.repetition_policy == "draw"
    assert ruleset.max_ply == 1_000
    assert ruleset.automatic_adjudications == ()
    assert ruleset.repetition_limit > ruleset.max_ply + 1

    assert compiled.repetition_limit == ruleset.repetition_limit
    assert compiled.max_ply == ruleset.max_ply
    assert compiled.automatic_adjudications == ()

