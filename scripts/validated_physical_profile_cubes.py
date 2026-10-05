"""Strict promotion identity boundary; frozen dispatcher remains unchanged."""
from scripts.shared_contact_prefix import Profile
from scripts.physical_profile_event_cubes import PhysicalProfileEventCubes,ContactUnsupported

class ValidatedPhysicalProfileCubes(PhysicalProfileEventCubes):
    def __init__(self,compiled,profiles,**kwargs):
        profiles=tuple(profiles)
        if any(not isinstance(p,Profile) or type(p.promoted) is not bool for p in profiles):
            raise ContactUnsupported('physical promotion flag must be bool')
        super().__init__(compiled,profiles,**kwargs)
