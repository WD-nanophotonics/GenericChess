@classmethod
def try_create(cls, compiled, *, strict: bool=False):
    """Create an active provider or return ``None`` for normal fallback."""
    if not isinstance(compiled, CompiledSemanticRuleset):
        return None
    engine = semantic_engine_for(compiled)
    if engine is None:
        return None
    if any((effect.kind in ('move', 'shift', 'remove') and effect.piece_type_ref is not None and (effect.piece_type_ref.kind in ('action_base', 'action_current')) for pattern in engine._patterns for effect in pattern.effects)):
        return None
    started = time.perf_counter()
    try:
        from ...native.compiler import compile_native_semantic_rules
        native_rules = compile_native_semantic_rules(compiled)
        if not native_rules.native_executable:
            return None
    except Exception:
        return None
    provider = cls(compiled, engine, native_rules, strict=strict)
    provider.compile_seconds = time.perf_counter() - started
    return provider
