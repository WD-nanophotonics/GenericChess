from scripts.audit_f9_terminal_legal_probe_reuse import corpus_specs, run_search


def test_f9_h9a_trace_proves_low_reuse_rate_without_production_forwarding():
    spec = next(item for item in corpus_specs() if item["id"] == "semantic_prefix_0")
    result, _rows = run_search(spec, "A")
    trace = result["f9_trace"]
    assert trace["semantic_pushes"] > 0
    assert trace["terminal_probe_calls"] == trace["semantic_pushes"]
    assert trace["reuse_eligible_rate"] < 0.85
    assert trace["repeated_prefix_s3_trial_count"] > 0
