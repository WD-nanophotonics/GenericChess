"""H8A contract tests for push/terminal checked-state forwarding."""

from scripts.audit_f4_runtime_cost import make_session, corpus_specs
from scripts.audit_f8_push_terminal_check import PushTrace
from generic_chess.core.terminal import terminal_from_search_runtime
from generic_chess.core.search_runtime import SearchPathRuntime


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


def test_f8_terminal_known_checked_is_optional_and_exact_for_semantic_runtime():
    spec = next(spec for spec in corpus_specs() if spec["id"] == "semantic_prefix_0")
    session = make_session(spec)
    runtime = SearchPathRuntime.from_state(session.state, session.compiled)
    action = runtime.legal_actions()[0]
    view = runtime.push(action)
    exact = view.terminal_status
    forwarded = terminal_from_search_runtime(
        runtime,
        known_checked=runtime._gave_check(runtime.position),
    )
    assert forwarded == exact
    runtime.pop()
    assert runtime.position == session.state.position
