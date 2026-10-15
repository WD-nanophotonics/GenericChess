"""Explicit opt-in transport of a complete no-WIN census across setup-only changes.

This is not a generic dead-position rule. It requires exact equality of every
compiled execution field of the already covered legacy rules. Only declared
starting placements, their fingerprint, and their descriptive entity count may
vary. Full current record replay still occurs in the base filter. UNKNOWN only.
"""
from dataclasses import fields
from pathlib import Path
import json
from generic_chess.rules.compiled import CompiledRuleSet
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from scripts.generic_inventory_proof_filter import InventoryNoWinFilter

_SETUP_FIELDS=frozenset(('ruleset_fingerprint','initial_position','initial_entity_count','initial_setup_positions'))

def execution_differences(reference,target):
    if type(reference) is not CompiledRuleSet or type(target) is not CompiledRuleSet:
        raise ValueError('legacy compiled rules required; semantic support is not qualified')
    # Unknown future compiled fields are compared automatically, never ignored.
    return tuple(f.name for f in fields(reference) if f.name not in _SETUP_FIELDS and getattr(reference,f.name)!=getattr(target,f.name))

class SetupTransportedNoWinFilter(InventoryNoWinFilter):
    def __init__(self,census_folder,coverage_file,target_compiled,**kwargs):
        super().__init__(census_folder,coverage_file,**kwargs)
        plan=json.loads((Path(census_folder)/'plan.json').read_text(encoding='utf-8'))
        reference=compile_ruleset_for_execution(deserialize_ruleset(Path(plan['rules']).read_text(encoding='utf-8')))
        if reference.ruleset_fingerprint!=self.fingerprint:raise ValueError('reference census fingerprint mismatch')
        differences=execution_differences(reference,target_compiled)
        if differences:raise ValueError('execution fields differ: '+','.join(differences))
        # The census source already enforces no declarations/drop/promotion/pass,
        # capture removal, draw-only history and complete KK/KKN edge closure.
        # Compilation's initial_entity_count is descriptive, not a Core bound.
        self.reference_fingerprint=self.fingerprint
        self.fingerprint=target_compiled.ruleset_fingerprint
        self.target_compiled=target_compiled

    def eligible(self,session):
        # Do not accept a forged dataclass merely reusing a qualified fingerprint.
        return session.compiled is self.target_compiled and super().eligible(session)
