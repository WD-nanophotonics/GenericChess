"""Explicit semantic backend ownership and protocol are compilation inputs."""
import pytest
from generic_chess.native import native_available
from generic_chess.native import compiler as nc
from test_native_terminal_declaration_priority import position

pytestmark=pytest.mark.skipif(not native_available(),reason='Native unavailable')

def test_explicit_existing_backend_survives_poisoned_global_default(monkeypatch):
    s=position();backend=nc._module();expected=nc.build_semantic_compile_payload(s.compiled)
    monkeypatch.setattr(nc,'_module',lambda:object())
    nr=nc.compile_native_semantic_rules(s.compiled,backend_module=backend)
    assert nr.backend_module is backend
    assert nr.report==expected[1]
    assert backend.semantic_rules_info(nr.capsule)==expected[0]

def test_unknown_explicit_backend_contract_is_not_silently_narrowed():
    class Unknown:
        def native_capabilities(self):
            return {'semantic_payload_version':5,'semantic_max_squares':1024,
                    'semantic_action_encoding_version':2}
        def compile_semantic_rules(self,payload):
            raise AssertionError('unknown public action dictionary reached C')
    with pytest.raises(nc.NativeUnsupportedRuleError,match='contract'):
        nc.compile_native_semantic_rules(position().compiled,backend_module=Unknown())
    with pytest.raises(nc.NativeUnsupportedRuleError,match='capabilities'):
        nc.compile_native_semantic_rules(position().compiled,backend_module=object())
