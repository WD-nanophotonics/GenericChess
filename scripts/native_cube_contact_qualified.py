"""Expose complete closure only after strictly native admission."""
from scripts.native_cube_contact_closure import NativeCubeKernel
class QualifiedNativeCubeKernel(NativeCubeKernel):
    def __init__(self,compiled,profiles,**kwargs):
        super().__init__(compiled,profiles,**kwargs)
        self.closure=set(self.profiles)
