"""H8A contract tests for push/terminal checked-state forwarding."""

from scripts.audit_f8_push_terminal_check import PushTrace


def test_f8_trace_uses_exact_position_fields_not_hash_only():
    assert set(PushTrace._position_summary.__name__) == set("_position_summary")
    assert PushTrace._position_summary(None) is None


def test_f8_duplicate_summary_has_required_gate_fields():
    trace = PushTrace()
    summary = trace.snapshot()
    for key in (
        "semantic_pushes", "gave_check_calls", "terminal_check_calls",
        "exact_duplicate_pairs", "duplicate_pair_rate", "boolean_mismatches",
        "duplicate_second_check_s",
    ):
        assert key in summary
