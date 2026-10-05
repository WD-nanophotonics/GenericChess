from types import SimpleNamespace as NS
from time import monotonic
import pytest
from scripts.shared_contact_prefix import Profile,SharedContactPrefix
from scripts.validated_physical_profile_cubes import ValidatedPhysicalProfileCubes,ContactUnsupported
from scripts.audit_physical_profile_dispatch import build,profiles
from generic_chess.rules.compiler import compile_ruleset_for_execution

def test_nonboolean_identity_is_rejected_before_any_geometry():
    c=compile_ruleset_for_execution(build())
    original=profiles()
    for i,flag in ((0,0),(1,1)):
        p=Profile(original[i].base,original[i].current,flag)
        # Observed old truthiness gate accepts integer aliases of booleans.
        SharedContactPrefix._profile(NS(c=c),p)
        with pytest.raises(ContactUnsupported,match='must be bool'):
            ValidatedPhysicalProfileCubes(c,(p,))
    with pytest.raises(ContactUnsupported,match='must be bool'):
        ValidatedPhysicalProfileCubes(c,(NS(base='A',current='A',promoted=False),))

def test_valid_bool_profiles_keep_exact_physical_dispatch():
    start=monotonic();p=profiles()
    def check():assert monotonic()-start<15
    k=ValidatedPhysicalProfileCubes(compile_ruleset_for_execution(build()),p,checkpoint=check)
    assert k.stats['canonical_candidates']<=128 and k.closure==set(p)
    assert {(d,q) for d,q in k.quiet[p[1],3] if d==6}=={(6,p[1])}
    assert {(d,q) for d,q in k.quiet[p[2],3] if d==6}=={(6,p[3])}
